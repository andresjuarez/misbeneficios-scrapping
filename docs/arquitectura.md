# Arquitectura técnica

## Flujo de datos end-to-end

```
Sitios bancarios
      │
      ▼
┌──────────────────────────────────────────────────┐
│               SCRAPERS (por banco)                │
│                                                  │
│  Tipo A' — Playwright+intercept  │  Tipo A — httpx│
│  Santander                       │  Banco de Chile│
│                                  │                │
│  Tipo B — Playwright DOM parse                    │
│  BCI, Falabella, BancoEstado... (pendiente)       │
└──────────┬───────────────────────────────────────┘
           │  Lista de BeneficioRaw (Pydantic)
           ▼
┌──────────────────────────────────────────────────┐
│               PIPELINE                            │
│                                                  │
│  1. Normalizer   → categoría, región,            │
│                    tipo tarjeta canónicos        │
│  2. Deduplicator → compara fingerprints en BD,   │
│                    filtra ya existentes          │
│  3. Uploader     → INSERT directo a PostgreSQL   │
│                    con UPSERT por fingerprint    │
└──────────┬───────────────────────────────────────┘
           │
           ▼
    PostgreSQL 5433 (misBeneficios BD)
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
    banco: str              # "Santander", "BancoChile", etc. (nombre canónico del banco)
    comercio: str           # "Starbucks", "LATAM", etc.
    descuento: str          # Texto del beneficio (corto y limpio)
    categoria_raw: str      # Categoría tal como la usa el banco o su slug
    tarjeta_raw: str        # "Visa", "Mastercard", "American Express" (puede ser vacío)
    regiones_raw: list[str] # Regiones — pueden ser crudas (BancoChile ya las pre-normaliza)
    condiciones: str = ""   # Texto legal / condiciones de uso
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
    condiciones: str = ""   # Texto legal (puede ser vacío)
    url_fuente: str
    fecha_scraping: datetime
    categoria_pendiente: bool = False  # True si no se encontró mapeo canónico
```

---

## Estrategias de extracción

### Tipo A — API pública REST (preferida)

Algunos bancos exponen sus beneficios vía una API REST que no requiere autenticación. Se llama directamente con httpx:

```python
async def scrape() -> list[BeneficioRaw]:
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.banco.cl/beneficios?page=1&per_page=100")
        data = resp.json()
        return [parse_item(item) for item in data["entries"]]
```

Ventajas: rápido, estable, no depende del HTML, menos probable de romperse.

**Ejemplo implementado:** Banco de Chile (`scrapers/bancochile.py`)

### Tipo A' — Playwright + intercepción de API (semi-headless)

La API existe pero el servidor bloquea llamadas directas (verifica Referer, cookies de sesión, headers de navegador). Playwright lanza un browser real en modo stealth y en lugar de parsear el DOM, intercepta la respuesta de red de la API:

```python
async with page.expect_response(
    lambda r: r.url.startswith(API_URL_BASE) and r.status == 200,
    timeout=45_000,
) as response_info:
    await page.goto(BANCO_URL, wait_until="domcontentloaded")

data = await (await response_info.value).json()
```

Más lento que Tipo A (~10-15s extra por el browser), pero más estable que parsear DOM.

**Ejemplo implementado:** Santander (`scrapers/santander.py`)

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

**Implementado: Insert directo en PostgreSQL (Opción B)**

Se usa psycopg2 con un patrón UPSERT por `fingerprint`. Si el beneficio ya existe, actualiza `descuento`, `condiciones` y `url_fuente`; si es nuevo, inserta.

```python
cur.execute("""
    INSERT INTO beneficios
        (comercio, descuento, condiciones, banco_id, categoria_id,
         tipo_tarjeta_id, url_fuente, activo, fingerprint)
    VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s)
    ON CONFLICT (fingerprint) DO UPDATE SET
        descuento   = EXCLUDED.descuento,
        condiciones = EXCLUDED.condiciones,
        url_fuente  = EXCLUDED.url_fuente,
        updated_at  = now()
    RETURNING id
""", (...))
```

El uploader también inserta en `beneficio_regiones` (tabla de unión N:M) con `ON CONFLICT DO NOTHING`.

**Nota de infraestructura:** el PostgreSQL de Docker corre en puerto 5433 (no 5432) para evitar conflicto con el PostgreSQL local de macOS. La variable `DATABASE_URL` en `.env` debe especificar el puerto: `postgresql://user:pass@localhost:5433/misbeneficios`.

**Opción A — Via API REST (no implementada)**

Requeriría agregar endpoints de escritura al backend NestJS. Queda pendiente si se necesita desacoplar el scraper de acceso directo a BD.

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
