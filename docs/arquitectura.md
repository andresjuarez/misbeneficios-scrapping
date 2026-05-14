# Arquitectura técnica

## Flujo de datos end-to-end

```
Sitios bancarios
      │
      ▼
┌─────────────────────────────────────────────┐
│               SCRAPERS (por banco)           │
│                                             │
│  Playwright (SPA)  │  httpx (API interna)   │
│  BCI, Falabella,   │  Santander, BancoChile │
│  BancoEstado...    │  (si se descubre API)  │
└──────────┬──────────────────────────────────┘
           │  Lista de BeneficioRaw (Pydantic)
           ▼
┌─────────────────────────────────────────────┐
│               PIPELINE                      │
│                                             │
│  1. Normalizer   → categoría, región,       │
│                    tipo tarjeta canónicos   │
│  2. Deduplicator → compara contra BD,       │
│                    filtra ya existentes     │
│  3. Uploader     → POST /api/beneficios     │
│                    (o INSERT directo)       │
└──────────┬──────────────────────────────────┘
           │
           ▼
    PostgreSQL (misBeneficios BD)
```

---

## Stack técnico

| Componente | Librería | Motivo |
|------------|----------|--------|
| Browser headless | `playwright` | Mejor soporte para SPAs modernas que Selenium; más rápido que Puppeteer |
| HTTP client | `httpx` | Async nativo, mejor que `requests` para llamadas paralelas |
| HTML parsing | `beautifulsoup4` + `lxml` | Robusto y rápido |
| Validación | `pydantic` v2 | Tipado estricto, validación automática, serialización a JSON |
| BD (opción A) | `psycopg2-binary` | Insert directo sin pasar por la API REST |
| BD (opción B) | `httpx` | POST a `/api/beneficios` de misBeneficios (requiere auth) |
| Scheduling | `APScheduler` o cron | Ejecución periódica (diaria/semanal) |
| Config | `python-dotenv` | Variables de entorno |
| Logging | `loguru` | Logs estructurados con nivel y contexto |

### Por qué Python y no Node.js/TypeScript

- Playwright tiene soporte en ambos, pero el ecosistema de scraping Python (BeautifulSoup, Scrapy, httpx) es más maduro.
- Pydantic ofrece normalización de datos más expresiva que Zod para este caso.
- El scrapper es un servicio independiente; no necesita compartir código con el backend NestJS.

---

## Modelo de datos interno (BeneficioRaw)

Lo que extrae el scraper antes de normalizar:

```python
class BeneficioRaw(BaseModel):
    banco: str              # "Banco de Chile", "BCI", etc. (tal como aparece en el sitio)
    comercio: str           # "Starbucks", "LATAM", etc.
    descuento: str          # Texto completo del beneficio
    categoria_raw: str      # Categoría tal como la usa el banco ("Food & Drink", "Gastronomía", etc.)
    tarjeta_raw: str        # "Visa", "Mastercard", "AMEX", etc. (puede ser vacío)
    regiones_raw: list[str] # Regiones tal como las nombra el banco
    url_fuente: str         # URL exacta del beneficio
    fecha_scraping: datetime
```

Lo que sale del pipeline (normalizado, listo para insertar):

```python
class BeneficioNormalizado(BaseModel):
    banco: str              # Nombre canónico (debe existir en tabla bancos)
    comercio: str
    descuento: str
    categoria: str          # Nombre canónico (debe existir en tabla categorias)
    tarjeta: str            # "Visa" | "Mastercard" | "American Express"
    regiones: list[str]     # Nombres canónicos (deben existir en tabla regiones)
```

---

## Estrategias de extracción

### Tipo A — API interna (preferida)

Algunos bancos cargan los beneficios desde un endpoint REST interno que su frontend SPA consume. Si se puede identificar esta API (usando DevTools → Network → XHR/Fetch), el scraping se reduce a:

```python
async def scrape() -> list[BeneficioRaw]:
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.banco.cl/beneficios", headers={...})
        data = resp.json()
        return [parse_item(item) for item in data["beneficios"]]
```

Ventajas: rápido, estable, no depende del HTML, menos probable de romperse.

### Tipo B — SPA con Playwright

Para bancos donde no se encuentra API interna o está protegida:

```python
async def scrape() -> list[BeneficioRaw]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://banco.cl/beneficios", wait_until="networkidle")
        # Paginación
        while True:
            items = await page.query_selector_all(".benefit-card")
            for item in items:
                raw = await extract_item(item)
                yield raw
            next_btn = await page.query_selector("[data-next]")
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_load_state("networkidle")
        await browser.close()
```

### Tipo C — HTML estático

Para sitios que renderizan server-side (poco probable en bancos modernos):

```python
async def scrape() -> list[BeneficioRaw]:
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://banco.cl/beneficios")
        soup = BeautifulSoup(resp.text, "lxml")
        return [parse_card(card) for card in soup.select(".benefit-card")]
```

---

## Resiliencia y buenas prácticas

| Aspecto | Implementación |
|---------|---------------|
| Rate limiting | `asyncio.sleep(1-3s)` entre requests; no saturar los servidores |
| Reintentos | `httpx` con `max_retries=3`, backoff exponencial |
| Timeout | 30s por página, 10s por request HTTP |
| User-Agent | Rotar entre 3-4 UAs legítimos de Chrome/Firefox |
| Detección de cambios | Comparar hash del HTML antes de re-parsear |
| Logging | Loguru con nivel INFO en ejecución normal, DEBUG en desarrollo |
| Fallo parcial | Si un banco falla, continuar con los demás y reportar el error |
| Legalidad | Revisar `robots.txt` y TOS de cada banco antes de ejecutar |

---

## Integración con misBeneficios backend

**Opción A — Via API REST (recomendada para empezar)**

El uploader hace POST a los endpoints existentes del backend. No requiere acceso directo a la BD.

```python
async def upload(beneficio: BeneficioNormalizado):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:3001/api/beneficios",
            json=beneficio.model_dump(),
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
```

Requiere agregar un endpoint de escritura al backend (actualmente solo hay GET).

**Opción B — Insert directo en PostgreSQL**

Más simple para comenzar, sin modificar el backend. Usa las mismas credenciales de BD.

```python
import psycopg2

def upload(beneficios: list[BeneficioNormalizado]):
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre FROM bancos")
            bancos_map = {row[1]: row[0] for row in cur.fetchall()}
            # ... INSERT INTO beneficios ...
```

---

## Scheduling

Para ejecución automática periódica, dos alternativas:

**Cron del sistema (más simple):**
```bash
# Ejecutar todos los lunes a las 3am
0 3 * * 1 cd /path/to/scrapping && python main.py >> logs/scraping.log 2>&1
```

**APScheduler en Python (más control):**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(run_all_scrapers, "cron", day_of_week="mon", hour=3)
scheduler.start()
```

Para el MVP se recomienda cron del sistema. APScheduler cuando se necesite lógica más compleja (distintas frecuencias por banco, notificaciones, etc.).
