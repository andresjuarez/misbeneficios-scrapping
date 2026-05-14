# misBeneficios — Scraping

Sistema automatizado para extraer beneficios de tarjetas de crédito desde los sitios oficiales de bancos en Chile y poblar la base de datos de misBeneficios.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [Arquitectura](docs/arquitectura.md) | Stack técnico, estructura de carpetas, flujo de datos |
| [Bancos](docs/bancos.md) | Análisis por banco: URL, tipo de sitio, estrategia de extracción |
| [Normalización](docs/normalizacion.md) | Mapeo de datos scrapeados al modelo de BD |
| [Roadmap](docs/roadmap.md) | Fases de implementación y criterios de éxito |

## Resumen ejecutivo

El scraping de beneficios bancarios en Chile enfrenta tres retos principales:

1. **Sitios SPA** — La mayoría de los bancos usan React/Angular. El HTML que devuelve el servidor está vacío; el contenido lo renderiza JavaScript. Requiere un browser headless (Playwright).

2. **APIs internas** — Algunos bancos cargan los beneficios desde una API REST propia (generalmente un endpoint `/api/beneficios` o similar). Si se puede identificar esta API, el scraping es mucho más simple y robusto.

3. **Normalización** — Cada banco usa sus propias categorías, nombres de regiones y formatos de descuento. Hay que mapear todo al modelo canónico de misBeneficios.

## Stack recomendado

- **Python 3.11+** — ecosistema de scraping más maduro
- **Playwright** — browser headless para SPAs con JS
- **httpx** — cliente HTTP async para APIs internas
- **BeautifulSoup4** — parsing de HTML cuando es necesario
- **Pydantic v2** — validación y normalización de datos
- **psycopg2 / httpx** — inserción directa en BD o vía API REST de misBeneficios

## Estructura de carpetas (target)

```
misBeneficios-scrapping/
├── scrapers/
│   ├── base.py              # Clase base abstracta
│   ├── bci.py
│   ├── santander.py
│   ├── falabella.py
│   ├── bancoestado.py
│   ├── ripley.py
│   ├── scotiabank.py
│   ├── itau.py
│   ├── bice.py
│   ├── security.py
│   └── bancochile.py
├── pipeline/
│   ├── normalizer.py        # Normalización de categorías, regiones y tarjetas
│   ├── deduplicator.py      # Evitar beneficios duplicados en BD
│   └── uploader.py          # POST a la API REST o inserción directa
├── models/
│   └── beneficio.py         # Pydantic model del beneficio scrapeado
├── config.py                # Variables de entorno y configuración
├── main.py                  # Orquestador: corre todos los scrapers
├── requirements.txt
└── .env.example
```
