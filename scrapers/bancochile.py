"""
Banco de Chile — Tipo A (API pública REST)

Endpoint descubierto inspeccionando la carga de la página de beneficios:
https://sitiospublicos.bancochile.cl/personas/beneficios

La API devuelve páginas de 100 entradas. Se itera hasta agotar total_pages.
No requiere autenticación ni Playwright.
"""
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from models.beneficio import BeneficioRaw
from scrapers.base import BaseScraper

API_BASE = "https://sitiospublicos.bancochile.cl"
API_URL = (
    f"{API_BASE}/api/content/spaces/personas/types/beneficios/entries"
    "?meta.category[in][]=beneficios&sort_by=meta.updated_at&order=desc&per_page=100"
)
DETALLE_URL = f"{API_BASE}/personas/beneficios/detalle"

# meta.category_slug → categoría canónica
_CAT_SLUG_MAP: dict[str, str] = {
    "restaurantes-y-bares":         "Gastronomía",
    "gastronomia":                  "Gastronomía",
    "gastronomía":                  "Gastronomía",
    "food-drink":                   "Gastronomía",
    "sabores-gourmet":              "Gastronomía",
    "comida-rapida":                "Gastronomía",
    "supermercados":                "Supermercados",
    "supermercado":                 "Supermercados",
    "viajes":                       "Viajes",
    "travel":                       "Viajes",
    "turismo":                      "Viajes",
    "entretenimiento":              "Entretenimiento",
    "entretencion":                 "Entretenimiento",
    "entertainment":                "Entretenimiento",
    "cine-y-teatro":                "Entretenimiento",
    "deportes":                     "Entretenimiento",
    "compras":                      "Compras",
    "retail":                       "Compras",
    "moda":                         "Compras",
    "hogar":                        "Compras",
    "beneficios-y-descuentos":      "Compras",
    "tecnologia":                   "Tecnología",
    "tecnología":                   "Tecnología",
    "tech":                         "Tecnología",
    "bencina":                      "Bencina",
    "combustible":                  "Bencina",
    "salud":                        "Salud",
    "farmacias":                    "Salud",
    "salud-y-bienestar":            "Salud",
    "belleza":                      "Salud",
    "mascotas":                     "Compras",
    "catalogo-productos":           "Compras",
    "dolares-premio":               "Compras",
    "sustentable":                  "Compras",
    # Slugs de campañas puntuales → categoría por contexto
    "40-de-descuento-visa":         "Compras",
    "50-de-descuento-visa-infinite":"Compras",
}

# Prefijos de tags que indican región — se normalizan luego en el normalizer
_REGION_TAGS = {
    "todo-chile",
    "todas-las-regiones",
    "nacional",
    "metropolitana-de-santiago",
    "region-metropolitana",
    "valparaíso",
    "valparaiso",
    "biobío",
    "biobio",
    "la-araucanía",
    "la-araucania",
    "maule",
    "o-higgins",
    "ohiggins",
    "los-lagos",
    "antofagasta",
    "coquimbo",
    "los-ríos",
    "los-rios",
    "atacama",
    "tarapacá",
    "tarapaca",
    "aysén",
    "aysen",
    "magallanes",
    "arica-y-parinacota",
    "ñuble",
    "nuble",
}

# Tags de ciudades → mapear a su región (el normalizer también lo hace, pero los slugs son distintos)
_CIUDAD_TAG_REGION: dict[str, str] = {
    "santiago":     "Región Metropolitana",
    "las-condes":   "Región Metropolitana",
    "providencia":  "Región Metropolitana",
    "vitacura":     "Región Metropolitana",
    "viña-del-mar": "Valparaíso",
    "vina-del-mar": "Valparaíso",
    "concepción":   "Biobío",
    "concepcion":   "Biobío",
    "temuco":       "La Araucanía",
    "puerto-montt": "Los Lagos",
    "iquique":      "Tarapacá",
    "antofagasta":  "Antofagasta",
    "la-serena":    "Coquimbo",
    "rancagua":     "O'Higgins",
    "talca":        "Maule",
    "valdivia":     "Los Ríos",
    "punta-arenas": "Magallanes",
    "arica":        "Arica y Parinacota",
    "chillán":      "Ñuble",
    "chillan":      "Ñuble",
    "copiapó":      "Atacama",
    "copiapo":      "Atacama",
}

# Normalización de slugs de región a nombre canónico
_SLUG_REGION_MAP: dict[str, str] = {
    "todo-chile":               "Todas las regiones",
    "todas-las-regiones":       "Todas las regiones",
    "nacional":                 "Todas las regiones",
    "metropolitana-de-santiago":"Región Metropolitana",
    "region-metropolitana":     "Región Metropolitana",
    "valparaíso":               "Valparaíso",
    "valparaiso":               "Valparaíso",
    "biobío":                   "Biobío",
    "biobio":                   "Biobío",
    "la-araucanía":             "La Araucanía",
    "la-araucania":             "La Araucanía",
    "maule":                    "Maule",
    "o-higgins":                "O'Higgins",
    "ohiggins":                 "O'Higgins",
    "los-lagos":                "Los Lagos",
    "antofagasta":              "Antofagasta",
    "coquimbo":                 "Coquimbo",
    "los-ríos":                 "Los Ríos",
    "los-rios":                 "Los Ríos",
    "atacama":                  "Atacama",
    "tarapacá":                 "Tarapacá",
    "tarapaca":                 "Tarapacá",
    "aysén":                    "Aysén",
    "aysen":                    "Aysén",
    "magallanes":               "Magallanes",
    "arica-y-parinacota":       "Arica y Parinacota",
    "ñuble":                    "Ñuble",
    "nuble":                    "Ñuble",
}


def _html_a_texto(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(separator=" ").strip()


def _tarjeta_desde_permitidas(permitidas: list[str]) -> list[str]:
    """Retorna lista de redes presentes: ['Visa'], ['Mastercard'] o ['Visa', 'Mastercard']."""
    redes: set[str] = set()
    for t in permitidas:
        slug = t.lower()
        if "mastercard" in slug:
            redes.add("Mastercard")
        elif "visa" in slug:
            redes.add("Visa")
        elif "amex" in slug or "american" in slug:
            redes.add("American Express")
    return list(redes) if redes else ["Visa"]


def _regiones_desde_tags(tags: list[str]) -> list[str]:
    regiones: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        slug = tag.lower().strip()

        # Mapeo directo slug → región canónica
        if slug in _SLUG_REGION_MAP:
            region = _SLUG_REGION_MAP[slug]
            if region not in seen:
                seen.add(region)
                regiones.append(region)
            continue

        # Ciudad → región
        if slug in _CIUDAD_TAG_REGION:
            region = _CIUDAD_TAG_REGION[slug]
            if region not in seen:
                seen.add(region)
                regiones.append(region)

    return regiones


class BancoChileScraper(BaseScraper):
    banco_nombre = "BancoChile"

    async def _extraer(self) -> list[BeneficioRaw]:
        resultados: list[BeneficioRaw] = []
        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent(),
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            page = 1
            total_pages = 1

            while page <= total_pages:
                url = f"{API_URL}&page={page}"
                logger.info(f"[BancoChile] Página {page}/{total_pages} — {url}")

                try:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error(f"[BancoChile] Error en página {page}: {e}")
                    break

                meta = data.get("meta", {})
                total_pages = meta.get("total_pages", 1)
                entries = data.get("entries", [])

                for entry in entries:
                    parsed = self._parsear_entry(entry)
                    resultados.extend(parsed)

                page += 1
                if page <= total_pages:
                    await self._delay()

        logger.info(f"[BancoChile] Total extraídos: {len(resultados)}")
        return resultados

    def _categoria_desde_entry(self, entry: dict) -> str:
        meta = entry.get("meta", {})

        # Intentar category_slug directo
        slug = meta.get("category_slug", "").lower().strip()
        if slug in _CAT_SLUG_MAP:
            return _CAT_SLUG_MAP[slug]

        # Buscar en tags
        for tag in meta.get("tags", []):
            t = tag.lower().strip()
            if t in _CAT_SLUG_MAP:
                return _CAT_SLUG_MAP[t]

        return slug  # devolver raw para que normalizer lo marque pendiente

    def _parsear_entry(self, entry: dict) -> list[BeneficioRaw]:
        """
        Retorna una lista porque un entry puede tener Visa Y Mastercard,
        generando un BeneficioRaw por red de tarjeta.
        """
        fields = entry.get("fields", {})
        meta = entry.get("meta", {})

        comercio = (fields.get("Titulo") or "").strip()
        if not comercio:
            return []

        # Descuento: campo corto limpio
        descuento = (fields.get("Tipo Beneficio") or "").strip()
        if not descuento:
            # Fallback: texto plano de Descripcion HTML
            descuento = _html_a_texto(fields.get("Descripcion") or "")
        if not descuento:
            return []

        condiciones = _html_a_texto(fields.get("Condiciones Comerciales") or "")

        categoria_raw = self._categoria_desde_entry(entry)

        permitidas: list[str] = fields.get("Tarjetas Permitidas") or []
        redes = _tarjeta_desde_permitidas(permitidas)

        regiones_raw = _regiones_desde_tags(meta.get("tags") or [])

        slug = meta.get("slug") or ""
        url_fuente = f"{DETALLE_URL}/{slug}" if slug else API_BASE

        fecha = datetime.now()

        beneficios = []
        for red in redes:
            beneficios.append(BeneficioRaw(
                banco="BancoChile",
                comercio=comercio,
                descuento=descuento,
                categoria_raw=categoria_raw,
                tarjeta_raw=red,
                regiones_raw=regiones_raw,
                condiciones=condiciones,
                url_fuente=url_fuente,
                fecha_scraping=fecha,
            ))

        return beneficios
