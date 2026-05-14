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

## Santander

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://banco.santander.cl/beneficios/` |
| URL detalle | `https://banco.santander.cl/beneficios/?slug={slug}` |
| Tipo probable | **A — API interna** (el slug en query param es indicio) |
| Prioridad | Alta |

**Lo que hay que investigar:**
- El parámetro `?slug=` sugiere que hay una API que devuelve el beneficio por slug
- Buscar en Network tab llamadas a `api.santander.cl` o similar
- Endpoint de listado: buscar request al cargar `/beneficios/` sin slug
- Headers de autenticación requeridos (si los hay)

**Estrategia probable:**
```
GET https://[api-interna].santander.cl/beneficios?page=1&size=50
→ JSON con lista de beneficios
```

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

## Banco de Chile

| Campo | Valor |
|-------|-------|
| URL beneficios | `https://sitiospublicos.bancochile.cl/personas/beneficios` |
| URL detalle | `https://sitiospublicos.bancochile.cl/personas/beneficios/detalle/{slug}` |
| Tipo probable | **A o B** |
| Prioridad | Alta |

**Lo que hay que investigar:**
- El subdominio `sitiospublicos` sugiere que hay una API detrás
- Buscar calls a `api.bancochile.cl` o similar en Network tab
- Banco de Chile tiene tarjetas Visa y Mastercard — verificar distinción en los beneficios

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

| Banco | Tipo estimado | Prioridad | Complejidad |
|-------|--------------|-----------|-------------|
| BCI | B — SPA | Alta | Media |
| Santander | A — API | Alta | Baja |
| Banco de Chile | A o B | Alta | Baja-Media |
| Falabella | B — SPA | Alta | Media |
| BancoEstado | B o C | Alta | Media |
| Scotiabank | B — SPA | Media | Media |
| Itaú | B — SPA | Media | Media |
| Ripley | B — SPA | Media | Media |
| BICE | B o C | Baja | Alta |
| Security | B — SPA | Baja | Media |

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
