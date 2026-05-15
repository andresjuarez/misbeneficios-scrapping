# Roadmap de implementación

## Fase 0 — Setup del proyecto ✅ Completa

**Objetivo:** Estructura base lista para implementar scrapers.

### Tareas
- [x] Documentar arquitectura técnica
- [x] Analizar bancos y definir estrategias
- [x] Definir tablas de normalización
- [x] Crear `requirements.txt` con dependencias
- [x] Crear `config.py` con variables de entorno
- [x] Crear modelos Pydantic (`models/beneficio.py`)
- [x] Crear clase base abstracta (`scrapers/base.py`)
- [x] Crear pipeline base (`pipeline/normalizer.py`, `pipeline/deduplicator.py`, `pipeline/uploader.py`)
- [x] Crear orquestador principal (`main.py`)
- [x] Crear `.env.example`

**Notas de implementación:**
- Python 3.13 requirió versiones sin pin (`psycopg2-binary>=2.9.10`, `pydantic>=2.9.0`, `greenlet>=3.0.0`)
- Docker PostgreSQL movido a puerto 5433 para evitar conflicto con PostgreSQL local en 5432
- Uploader usa INSERT directo con psycopg2 (no via API REST) + patrón UPSERT por fingerprint

**Criterio de éxito:** `python main.py --dry-run` corre sin errores con lista vacía.

---

## Fase 1 — Primer scraper ✅ Completa

**Objetivo:** Datos reales de un banco en BD.

### Banco objetivo: Santander

### Tareas
- [x] Investigar API interna de Santander con DevTools
- [x] Implementar `scrapers/santander.py`
- [x] Probar extracción en modo dry-run
- [x] Correr pipeline completo (normalizar → deduplicar → insertar)
- [x] Verificar datos en BD de misBeneficios

**Notas de implementación:**
- La API devuelve 403 a llamadas directas de httpx → se usa Playwright en modo stealth para interceptar la respuesta (`page.expect_response()`)
- URL con hash dinámico por sesión → se intercepta por prefijo `promociones.json`, no por URL exacta
- ~275 beneficios insertados en BD; `cat-otros` marcados como `categoria_pendiente=True`
- Se agregó campo `condiciones` al modelo, migración de BD y frontend (drawer lateral)

**Criterio de éxito:** ✅ 275 beneficios de Santander en BD, categorías y regiones normalizadas.

---

## Fase 2 — Scrapers prioritarios (en curso)

**Objetivo:** Cubrir los 5 bancos de mayor volumen.

### Orden de implementación

| # | Banco | Tipo | Estado |
|---|-------|------|--------|
| 1 | Santander | A' — Playwright + intercepción API | ✅ Completo |
| 2 | Banco de Chile | A — API pública REST | ✅ Completo |
| 3 | BCI | B — SPA | Pendiente |
| 4 | Falabella | B — SPA | Pendiente |
| 5 | BancoEstado | B o C | Pendiente |

### Banco de Chile — notas de implementación
- [x] API pública descubierta en subdominio `sitiospublicos.bancochile.cl`
- [x] Implementar `scrapers/bancochile.py` (httpx, sin Playwright)
- [x] Paginación por query param `&page={n}`, `meta.total_pages=8`, `per_page=100`
- [x] Un BeneficioRaw por red de tarjeta (Visa / Mastercard) — beneficios con ambas redes generan 2 registros
- [x] Categorías desde `meta.category_slug`, incluyendo slugs de campaña mapeados a canónicas
- [x] Regiones desde `meta.tags` — mix de slugs de región y ciudad
- [x] Test en dry-run: 1446 raw, 1446 normalizados, 746 nuevos a insertar

### Tareas pendientes (BCI, Falabella, BancoEstado)
- [ ] Investigar sitio (Network tab, robots.txt)
- [ ] Implementar scraper
- [ ] Adaptar tabla de normalización si aparecen categorías nuevas
- [ ] Test en dry-run
- [ ] Inserción en BD

**Criterio de éxito:** +100 beneficios de 5 bancos diferentes en BD, sin duplicados, con categorías y regiones válidas.

---

## Fase 3 — Scrapers secundarios (1-2 semanas)

**Objetivo:** Completar cobertura de bancos medianos.

| # | Banco | Tipo | Estado |
|---|-------|------|--------|
| 6 | Scotiabank | B — SPA | Pendiente |
| 7 | Itaú | B — SPA | Pendiente |
| 8 | Ripley | B — SPA | Pendiente |
| 9 | BICE | B o C | Pendiente |
| 10 | Security | B — SPA | Pendiente |

**Criterio de éxito:** Todos los bancos del catálogo cubiertos. +200 beneficios totales en BD.

---

## Fase 4 — Automatización y monitoreo (1 semana)

**Objetivo:** El sistema corre solo y reporta fallas.

### Tareas
- [ ] Configurar cron job (ejecución semanal, lunes 3am)
- [ ] Alertas por email/Slack cuando un scraper falla
- [ ] Dashboard de últimas ejecuciones (fecha, banco, cantidad scrapeada, errores)
- [ ] Rotación de logs (`loguru` con compresión)
- [ ] Healthcheck: comparar cantidad scrapeada vs semana anterior (alerta si cae >30%)

**Criterio de éxito:** Sistema corre una semana completa sin intervención manual. Fallas se detectan y alertan automáticamente.

---

## Fase 5 — Calidad de datos (ongoing)

**Objetivo:** Mantener datos precisos y actualizados.

### Tareas
- [ ] Revisar beneficios con `categoria_pendiente=True` semanalmente
- [ ] Agregar variantes de categorías/regiones a las tablas de mapeo
- [ ] Depurar beneficios expirados (comparar fecha_vigencia_fin)
- [ ] Detectar cambios de estructura en sitios bancarios (alerta si tasa de extracción cae)

---

## Métricas de éxito del proyecto

| Métrica | Meta MVP | Meta Final |
|---------|----------|------------|
| Bancos cubiertos | 5 | 10 |
| Beneficios en BD | 100+ | 500+ |
| Frecuencia actualización | Manual | Semanal automático |
| Tasa de éxito scraping | >80% | >95% |
| Beneficios sin categoría | <10% | <2% |
| Tiempo de ejecución total | <10 min | <5 min |

---

## Dependencias externas

| Dependencia | Riesgo | Mitigación |
|-------------|--------|-----------|
| Cambios de estructura HTML/API en bancos | Alto | Alertas por caída de tasa de extracción |
| Bloqueo por IP | Medio | Rate limiting conservador, User-Agent rotation |
| Cambios en TOS de bancos | Bajo | Revisar robots.txt antes de cada Fase |
| Downtime de BD misBeneficios | Bajo | Retry con backoff, guardar datos localmente en JSON |
