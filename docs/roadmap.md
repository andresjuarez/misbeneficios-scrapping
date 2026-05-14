# Roadmap de implementación

## Fase 0 — Setup del proyecto (1-2 días)

**Objetivo:** Estructura base lista para implementar scrapers.

### Tareas
- [x] Documentar arquitectura técnica
- [x] Analizar bancos y definir estrategias
- [x] Definir tablas de normalización
- [ ] Crear `requirements.txt` con dependencias
- [ ] Crear `config.py` con variables de entorno
- [ ] Crear modelos Pydantic (`models/beneficio.py`)
- [ ] Crear clase base abstracta (`scrapers/base.py`)
- [ ] Crear pipeline base (`pipeline/normalizer.py`, `pipeline/deduplicator.py`, `pipeline/uploader.py`)
- [ ] Crear orquestador principal (`main.py`)
- [ ] Crear `.env.example`

**Criterio de éxito:** `python main.py --dry-run` corre sin errores con lista vacía.

---

## Fase 1 — Primer scraper (3-5 días)

**Objetivo:** Datos reales de un banco en BD.

### Banco objetivo: Santander (Tipo A — API interna)

Santander fue elegido como primer banco porque:
- Probablemente tiene API interna (más simple de implementar)
- Alta prioridad (banco grande)
- El patrón API sirve de template para otros bancos similares

### Tareas
- [ ] Investigar API interna de Santander con DevTools
- [ ] Implementar `scrapers/santander.py`
- [ ] Probar extracción en modo dry-run
- [ ] Correr pipeline completo (normalizar → deduplicar → insertar)
- [ ] Verificar datos en BD de misBeneficios

**Criterio de éxito:** Al menos 20 beneficios de Santander en BD, categorías y regiones normalizadas correctamente.

---

## Fase 2 — Scrapers prioritarios (2-3 semanas)

**Objetivo:** Cubrir los 5 bancos de mayor volumen.

### Orden de implementación

| # | Banco | Tipo | Complejidad | Estado |
|---|-------|------|-------------|--------|
| 1 | Santander | A — API | Baja | Fase 1 |
| 2 | Banco de Chile | A o B | Baja-Media | Pendiente |
| 3 | BCI | B — SPA | Media | Pendiente |
| 4 | Falabella | B — SPA | Media | Pendiente |
| 5 | BancoEstado | B o C | Media | Pendiente |

### Tareas por banco
- [ ] Investigar sitio (Network tab, robots.txt)
- [ ] Implementar scraper
- [ ] Adaptar tabla de normalización si aparecen categorías nuevas
- [ ] Test en dry-run
- [ ] Inserción en BD de staging

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
