# Análisis por banco

Para cada banco se documenta: URL de beneficios, tipo de sitio detectado, estrategia recomendada y lo que hay que investigar antes de implementar.

> **Cómo investigar un banco antes de implementar:**
> 1. Abrir la URL en Chrome con DevTools → Network → filtrar por `Fetch/XHR`
> 2. Navegar por los beneficios y observar qué requests se hacen
> 3. Si hay una llamada a `/api/...` o similar → Tipo A (API interna)
> 4. Si solo hay carga de JS bundles → Tipo B (Playwright)
> 5. Ver `robots.txt` y revisar TOS del banco

---

## BCI

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.bci.cl/beneficios/beneficios-bci` |
| URL detalle | `https://www.bci.cl/beneficios/beneficios-bci/detalle/{slug}` |
| Tipo probable | **B — SPA (React)** |
| Prioridad | Alta (banco grande, muchos beneficios) |

**Lo que hay que investigar:**
- Paginación: ¿scroll infinito o páginas numeradas?
- Filtros disponibles en el sitio (categoría, tarjeta, región)
- Si existe endpoint interno tipo `/api/v1/beneficios`
- Selectores CSS/data-attributes de las cards

**Datos esperados por card:**
- Nombre del comercio
- Descripción del beneficio
- Categoría (BCI usa sus propias)
- Vigencia (fecha de inicio/fin)
- Tipo de tarjeta

---

## Santander ✅ Implementado

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://banco.santander.cl/beneficios/` |
| URL detalle | `https://banco.santander.cl/beneficios/?slug={slug}` |
| Tipo confirmado | **A' — Playwright + intercepción de API** |
| Estado | Scraper en producción |
| Resultados | ~275 beneficios extraídos |

### Por qué no es Tipo A puro

La API existe (`promociones.json`) pero devuelve 403 si se llama directo con httpx. El servidor verifica que el request venga de un navegador real (Referer, cookies de sesión, headers). Solución: Playwright en modo stealth lanza el navegador real, y en lugar de parsear el DOM, interceptamos la respuesta de red de la API.

Adicionalmente, la URL tiene un hash dinámico que cambia en cada sesión:
```
https://banco.santander.cl/beneficios/promociones.json?_=a3f9c2...
```

Por eso se intercepta por prefijo de URL, no por URL exacta.

### Estrategia implementada

```python
# Playwright stealth → esperar respuesta de API
async with page.expect_response(
    lambda r: r.url.startswith("https://banco.santander.cl/beneficios/promociones.json")
              and r.status == 200,
    timeout=45_000,
) as response_info:
    await page.goto(BANCO_URL, wait_until="domcontentloaded")

data = await (await response_info.value).json()
```

Flags anti-detección:
```python
args=["--disable-blink-features=AutomationControlled", ...]
await context.add_init_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)
```

### Estructura del JSON

```json
{
  "promociones": [
    {
      "title": "Starbucks",
      "tags": ["cat-sabores", "wm-limited"],
      "custom_fields": {
        "Bajada externa":      { "value": "20% de descuento" },
        "Región cobertura":    { "value": "Metropolitana, Valparaíso" }
      },
      "conditions": "Válido lunes y martes. Tope $5.000 por transacción.",
      "url": "https://banco.santander.cl/beneficios/?slug=starbucks"
    }
  ]
}
```

### Mapeo de categorías (tags `cat-*`)

| Tag Santander | Categoría canónica |
|---------------|-------------------|
| `cat-sabores` | Gastronomía |
| `cat-viajes` | Viajes |
| `cat-compras` | Compras |
| `cat-bencina` | Bencina |
| `cat-salud` | Salud |
| `cat-entretenimiento` | Entretenimiento |
| `cat-supermercados` | Supermercados |
| `cat-tecnologia` / `cat-tecnología` | Tecnología |
| `cat-descuentos` | Compras |
| `cat-cuotas-sin-interes` | Compras |
| `cat-multiplica-millas` | Viajes |
| `cat-verdes` | Compras |
| `cat-otros` | *(pendiente — `categoria_pendiente=True`)* |

### Mapeo de tarjetas (tags)

| Tag Santander | Tarjeta canónica |
|---------------|-----------------|
| `wm-limited` | Mastercard |
| `exclusivo-limited` | Mastercard |
| *(cualquier otro o ninguno)* | Visa |

### Mapeo de regiones

El campo `custom_fields["Región cobertura"]["value"]` es una cadena separada por comas:
- `"Metropolitana, Valparaíso"` → split → normalizar cada una
- Vacío → `["Todas las regiones"]`

---

## Banco Falabella

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.bancofalabella.cl/descuentos` |
| URL detalle | `https://www.bancofalabella.cl/descuentos/detalle/{slug}` |
| Tipo probable | **B — SPA** |
| Prioridad | Alta (muchos usuarios CMR) |

**Lo que hay que investigar:**
- Diferencia entre `/descuentos` y `/beneficios` (si existe)
- Estructura de categorías de Falabella (gastronomía, compras, etc.)
- Si los beneficios son solo para tarjeta CMR Visa o hay distinción

---

## BancoEstado

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.bancoestado.cl/content/bancoestado/cl/personas/inicio/beneficios.html` |
| Tipo probable | **C — HTML parcialmente estático** o B |
| Prioridad | Alta (banco más grande de Chile) |

**Lo que hay que investigar:**
- BancoEstado históricamente ha tenido sitios menos modernos; puede tener HTML server-rendered
- Verificar si usa Adobe Experience Manager (AEM) — común en bancos tradicionales
- Beneficios de CuentaRut vs tarjetas de crédito (diferenciar)

---

## Banco de Chile ✅ Implementado

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://sitiospublicos.bancochile.cl/personas/beneficios` |
| URL detalle | `https://sitiospublicos.bancochile.cl/personas/beneficios/detalle/{slug}` |
| Tipo confirmado | **A — API pública REST (httpx directo)** |
| Estado | Scraper en producción |
| Resultados | ~1446 registros raw (un registro por red de tarjeta por beneficio) |

### Endpoint

```
GET https://sitiospublicos.bancochile.cl/api/content/spaces/personas/types/beneficios/entries
    ?meta.category[in][]=beneficios
    &sort_by=meta.updated_at
    &order=desc
    &per_page=100
    &page={n}
```

No requiere autenticación. Responde en JSON sin restricciones de Referer/cookies.

### Paginación

```json
{
  "meta": {
    "total_pages": 8,
    "current_page": 1,
    "total_count": 756
  },
  "entries": [ ... ]
}
```

Se itera `page` de 1 a `meta.total_pages`. Con `per_page=100` son 8 páginas (~756 beneficios base; el total de registros raw es mayor porque se genera uno por red de tarjeta).

### Estructura de un entry

```json
{
  "meta": {
    "slug": "descuento-starbucks-visa",
    "category_slug": "restaurantes-y-bares",
    "tags": ["todo-chile", "restaurantes-y-bares"]
  },
  "fields": {
    "Titulo": "Starbucks",
    "Tipo Beneficio": "20% dto.",
    "Descripcion": "<p>Disfruta 20% de descuento...</p>",
    "Condiciones Comerciales": "<p>Tope $3.000. Lunes a viernes.</p>",
    "Tarjetas Permitidas": ["visa-credito", "visa-debito"]
  }
}
```

### Campos utilizados

| Campo fuente | Campo destino | Notas |
|-------------|---------------|-------|
| `fields.Titulo` | `comercio` | Texto limpio |
| `fields["Tipo Beneficio"]` | `descuento` | Texto corto ya limpio |
| `fields.Descripcion` | `descuento` (fallback) | HTML → BeautifulSoup para limpiar |
| `fields["Condiciones Comerciales"]` | `condiciones` | HTML → BeautifulSoup |
| `meta.category_slug` | `categoria_raw` | Ver mapeo abajo |
| `fields["Tarjetas Permitidas"]` | `tarjeta_raw` | Un BeneficioRaw por red presente |
| `meta.tags` | `regiones_raw` | Slugs → región canónica |
| `meta.slug` | `url_fuente` | Construida como `/personas/beneficios/detalle/{slug}` |

### Mapeo de categorías (`meta.category_slug`)

| Slug BancoChile | Categoría canónica |
|-----------------|-------------------|
| `restaurantes-y-bares` | Gastronomía |
| `sabores-gourmet` | Gastronomía |
| `comida-rapida` | Gastronomía |
| `supermercados` | Supermercados |
| `viajes` / `turismo` | Viajes |
| `entretenimiento` / `entretencion` | Entretenimiento |
| `cine-y-teatro` / `deportes` | Entretenimiento |
| `compras` / `retail` / `moda` / `hogar` | Compras |
| `beneficios-y-descuentos` | Compras |
| `catalogo-productos` / `dolares-premio` | Compras |
| `mascotas` / `sustentable` | Compras |
| `40-de-descuento-visa` / `50-de-descuento-visa-infinite` | Compras *(slugs de campaña)* |
| `tecnologia` / `tech` | Tecnología |
| `bencina` / `combustible` | Bencina |
| `salud` / `farmacias` / `salud-y-bienestar` / `belleza` | Salud |

### Mapeo de tarjetas (`fields["Tarjetas Permitidas"]`)

El campo es un array de slugs con prefijo de red:
- `visa-credito`, `visa-debito`, `visa-infinite` → **Visa**
- `mastercard-*`, `mastercard-black` → **Mastercard**
- `amex-*` → **American Express**

Si un entry tiene ambas redes, se generan **dos `BeneficioRaw`** (uno por red), resultando en dos registros independientes en BD.

### Mapeo de regiones (`meta.tags`)

Los tags mezclan regiones y ciudades. El scraper resuelve slugs directamente a nombre canónico antes de pasar al normalizer:

| Tag slug | Región canónica |
|----------|----------------|
| `todo-chile` / `nacional` | Todas las regiones |
| `metropolitana-de-santiago` | Región Metropolitana |
| `las-condes` / `providencia` / `vitacura` / `santiago` | Región Metropolitana |
| `valparaíso` / `viña-del-mar` | Valparaíso |
| `biobío` / `concepción` | Biobío |
| `la-araucanía` / `temuco` | La Araucanía |
| `maule` / `talca` | Maule |
| `o-higgins` / `rancagua` | O'Higgins |
| `los-lagos` / `puerto-montt` | Los Lagos |
| *(y resto de regiones)* | Mapeado en `_SLUG_REGION_MAP` |

Si no se detecta ninguna región en los tags, el normalizer asigna `["Todas las regiones"]`.

---

## Scotiabank

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.scotiabank.cl/personas/tarjetas-de-credito/beneficios.html` |
| Tipo probable | **B — SPA** |
| Prioridad | Media |

**Lo que hay que investigar:**
- Scotiabank Chile fue absorbido desde BBVA — la plataforma puede ser más moderna
- Verificar si los beneficios están bajo `/tarjetas-de-credito/` o sección dedicada

---

## Itaú

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.itau.cl/personas/tarjetas/beneficios` |
| Tipo probable | **B — SPA** |
| Prioridad | Media |

**Lo que hay que investigar:**
- Itaú Brasil tiene buena API documentada; la filial chilena puede exponer algo similar
- Verificar distinción entre tarjetas (débito vs crédito) en la sección de beneficios

---

## Ripley

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://banco.ripley.cl/beneficios` |
| Tipo probable | **B — SPA** |
| Prioridad | Media |

**Lo que hay que investigar:**
- Banco Ripley y Tiendas Ripley pueden tener beneficios cruzados — solo nos interesan los de tarjeta de crédito
- Verificar categorías: Ripley usa "Mundo Ripley" para puntos, filtrar solo descuentos directos

---

## BICE

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.bice.cl/personas/tarjetas/beneficios` |
| Tipo probable | **B o C** |
| Prioridad | Baja-Media |

**Lo que hay que investigar:**
- BICE es banco boutique con foco en clientes de alto patrimonio — puede tener pocos beneficios listados públicamente
- Algunos beneficios pueden requerir login

---

## Security

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://www.security.cl/personas/tarjetas-de-credito/beneficios` |
| Tipo probable | **B** |
| Prioridad | Baja |

**Lo que hay que investigar:**
- Banco Security fue adquirido por grupo BTG — verificar si el sitio cambió
- Beneficios públicos vs exclusivos para clientes

---

## Resumen de prioridades

| Banco | Tipo confirmado | Prioridad | Estado |
|-------|----------------|-----------|--------|
| Santander | A' — Playwright + intercepción API | Alta | ✅ En producción |
| Banco de Chile | A — API pública REST | Alta | ✅ En producción |
| BCI | B — SPA | Alta | Pendiente |
| Falabella | B — SPA | Alta | Pendiente |
| BancoEstado | B o C | Alta | Pendiente |
| Scotiabank | B — SPA | Media | Pendiente |
| Itaú | B — SPA | Media | Pendiente |
| Ripley | B — SPA | Media | Pendiente |
| BICE | B o C | Baja | Pendiente |
| Security | B — SPA | Baja | Pendiente |

---

## Mapa de categorías por banco (pendiente completar)

Cada banco usa nombres distintos para sus categorías. Hay que mapearlas a las canónicas de misBeneficios.

| Categoría canónica | Posibles nombres en bancos |
|--------------------|---------------------------|
| Gastronomía | "Restaurantes", "Food & Drink", "Comida y bebida", "Gastronomía" |
| Viajes | "Turismo", "Travel", "Vuelos y hoteles", "Viajes" |
| Compras | "Retail", "Shopping", "Tiendas", "Moda" |
| Bencina | "Combustible", "Bencina", "Estaciones de servicio" |
| Salud | "Salud y bienestar", "Farmacias", "Health" |
| Entretenimiento | "Ocio", "Entertainment", "Cine y teatro" |
| Supermercados | "Supermercado", "Grocery", "Alimentación" |
| Tecnología | "Electrónica", "Tech", "Tecnología" |
