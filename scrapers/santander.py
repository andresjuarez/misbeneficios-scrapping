"""
Santander Chile — Tipo A (API interna)

La página https://banco.santander.cl/beneficios/ carga los beneficios
desde una API REST. Detectada inspeccionando Network tab → XHR/Fetch.

Para descubrir el endpoint exacto:
  1. Abrir https://banco.santander.cl/beneficios/ en Chrome DevTools
  2. Filtrar por Fetch/XHR
  3. Buscar request con payload JSON de lista de beneficios
  4. Actualizar API_URL abajo con el endpoint encontrado

Mientras el endpoint no se confirme, este scraper usa Playwright para
interceptar la primera llamada a la API y capturar la URL real.
"""
import asyncio
from datetime import datetime

import httpx
from loguru import logger
from playwright.async_api import async_playwright

import config
from models.beneficio import BeneficioRaw
from scrapers.base import BaseScraper

BANCO_URL = "https://banco.santander.cl/beneficios/"

# Parte estable de la URL (sin el hash dinámico que cambia en cada sesión).
# Playwright intercepta cualquier respuesta cuya URL empiece con este prefijo.
API_URL_BASE: str | None = "https://banco.santander.cl/beneficios/promociones.json"


class SantanderScraper(BaseScraper):
    banco_nombre = "Santander"

    async def _extraer(self) -> list[BeneficioRaw]:
        # Siempre usamos Playwright: garantiza cookies de sesión y headers de navegador.
        # Llamar la API directo con httpx resulta en 403 porque el servidor verifica Referer/cookies.
        if API_URL_BASE:
            return await self._interceptar_api_conocida()
        return await self._descubrir_y_extraer()

    def _browser_context_opts(self) -> dict:
        return dict(
            user_agent=self._user_agent(),
            viewport={"width": 1280, "height": 800},
            locale="es-CL",
            timezone_id="America/Santiago",
            extra_http_headers={
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            },
        )

    async def _launch_stealth(self, p):
        """Lanza Chromium con flags que evitan detección de headless."""
        browser = await p.chromium.launch(
            headless=config.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1280,800",
            ],
        )
        context = await browser.new_context(**self._browser_context_opts())
        # Ocultar navigator.webdriver que delata Playwright/Selenium
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return browser, context

    async def _interceptar_api_conocida(self) -> list[BeneficioRaw]:
        """
        Carga la página con Playwright en modo stealth y espera la respuesta de API_URL_BASE.
        wait_for_response() es más confiable que on("response"): registra el listener ANTES
        de navegar, evitando perder respuestas que llegan muy rápido.
        """
        logger.info(f"[Santander] Esperando respuesta de {API_URL_BASE}")

        async with async_playwright() as p:
            browser, context = await self._launch_stealth(p)
            page = await context.new_page()

            try:
                async with page.expect_response(
                    lambda r: r.url.startswith(API_URL_BASE) and r.status == 200,
                    timeout=45_000,
                ) as response_info:
                    await page.goto(BANCO_URL, wait_until="domcontentloaded", timeout=60_000)

                response = await response_info.value
                logger.info(f"[Santander] Respuesta capturada: {response.url}")
                data = await response.json()

            except Exception as e:
                logger.warning(f"[Santander] No se capturó respuesta de {API_URL_BASE}: {e}")
                await browser.close()
                return []

            await browser.close()

        return self._extraer_items(data)

    async def _descubrir_y_extraer(self) -> list[BeneficioRaw]:
        """
        Modo descubrimiento: navega la página en modo stealth y loguea todas las
        respuestas JSON con URLs que parezcan contener beneficios/promociones.
        Útil para encontrar el endpoint correcto cuando API_URL_BASE es None.
        """
        logger.info("[Santander] Modo descubrimiento — registrando todas las respuestas JSON")
        api_responses: list[dict] = []

        async with async_playwright() as p:
            browser, context = await self._launch_stealth(p)
            page = await context.new_page()

            async def capturar_respuesta(response):
                content_type = response.headers.get("content-type", "")
                url = response.url
                if "json" in content_type:
                    logger.debug(f"[Santander] JSON detectado: {url}")
                    if any(k in url.lower() for k in ("promo", "beneficio", "descuento", "oferta", "promocion")):
                        try:
                            body = await response.json()
                            api_responses.append({"url": url, "data": body})
                            logger.info(f"[Santander] Candidato: {url}")
                        except Exception:
                            pass

            page.on("response", capturar_respuesta)
            await page.goto(BANCO_URL, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(6)
            await browser.close()

        if not api_responses:
            logger.warning(
                "[Santander] Sin candidatos JSON. "
                "Probar con HEADLESS=false en .env para ver la página manualmente."
            )
            return []

        logger.info(f"[Santander] URLs candidatas: {[r['url'] for r in api_responses]}")
        logger.info("[Santander] Establecer el prefijo correcto en API_URL_BASE (sin el hash final)")

        resultados = []
        for captured in api_responses:
            resultados.extend(self._extraer_items(captured["data"]))
        return resultados

    def _extraer_items(self, data: dict | list) -> list[BeneficioRaw]:
        """
        Parsea la respuesta JSON de la API de Santander.
        Adaptar según la estructura real del endpoint.
        """
        items_raw: list[dict] = []

        if isinstance(data, list):
            items_raw = data
        elif isinstance(data, dict):
            # Probar claves comunes de paginación
            for key in ("promociones", "beneficios", "items", "data", "content", "results"):
                if key in data and isinstance(data[key], list):
                    items_raw = data[key]
                    break

        if not items_raw:
            logger.warning(f"[Santander] Estructura inesperada: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return []

        resultados = []
        for item in items_raw:
            try:
                raw = self._parsear_item(item)
                if raw:
                    resultados.append(raw)
            except Exception as e:
                logger.error(f"[Santander] Error parseando item: {e} — {item}")

        return resultados

    # Mapeo de tags internos de Santander a categorías canónicas
    _CAT_TAG_MAP: dict[str, str] = {
        "cat-sabores":              "Gastronomía",
        "cat-viajes":               "Viajes",
        "cat-compras":              "Compras",
        "cat-bencina":              "Bencina",
        "cat-salud":                "Salud",
        "cat-entretenimiento":      "Entretenimiento",
        "cat-supermercados":        "Supermercados",
        "cat-tecnologia":           "Tecnología",
        "cat-tecnología":           "Tecnología",
        # Categorías adicionales descubiertas en datos reales
        "cat-descuentos":           "Compras",       # descuentos generales en comercios
        "cat-cuotas-sin-interes":   "Compras",       # cuotas 0% en retail
        "cat-multiplica-millas":    "Viajes",         # acumulación de millas LATAM Pass
        "cat-verdes":               "Compras",       # beneficios eco/sustentables
        # cat-otros → no se mapea → categoria_pendiente=True para revisión manual
    }

    # Mapeo de tags de tarjeta a tipo canónico
    _TARJETA_TAG_MAP: dict[str, str] = {
        "wm-limited":       "Mastercard",  # WorldMember Limited → Mastercard
        "exclusivo-limited": "Mastercard",
    }

    def _categoria_desde_tags(self, tags: list[str]) -> str:
        for tag in tags:
            if tag in self._CAT_TAG_MAP:
                return self._CAT_TAG_MAP[tag]
        # Si no hay cat-* reconocido, devolver el tag raw para que el normalizer lo marque pendiente
        cat_tags = [t for t in tags if t.startswith("cat-")]
        return cat_tags[0] if cat_tags else ""

    def _tarjeta_desde_tags(self, tags: list[str]) -> str:
        for tag in tags:
            if tag in self._TARJETA_TAG_MAP:
                return self._TARJETA_TAG_MAP[tag]
        return "Visa"  # Santander emite principalmente Visa

    def _custom_field(self, item: dict, nombre: str) -> str:
        return item.get("custom_fields", {}).get(nombre, {}).get("value", "") or ""

    def _parsear_item(self, item: dict) -> BeneficioRaw | None:
        from bs4 import BeautifulSoup

        comercio = item.get("title", "").strip()
        if not comercio:
            return None

        # "Bajada externa" = resumen corto limpio (sin HTML)
        descuento = self._custom_field(item, "Bajada externa").strip()
        if not descuento:
            # Fallback: stripear HTML de la descripción larga
            html = item.get("description", "")
            descuento = BeautifulSoup(html, "lxml").get_text(separator=" ").strip()
        if not descuento:
            return None

        tags: list[str] = item.get("tags") or []
        categoria_raw = self._categoria_desde_tags(tags)
        tarjeta_raw = self._tarjeta_desde_tags(tags)

        # El campo puede ser vacío (→ nacional) o una lista separada por comas
        # ej: "Metropolitana, O'Higgins, Ñuble, Valparaíso"
        region_raw = self._custom_field(item, "Región cobertura").strip()
        if region_raw:
            regiones_raw = [r.strip() for r in region_raw.split(",") if r.strip()]
        else:
            regiones_raw = []

        url_fuente = item.get("url") or BANCO_URL

        return BeneficioRaw(
            banco="Santander",
            comercio=comercio,
            descuento=descuento,
            categoria_raw=categoria_raw,
            tarjeta_raw=tarjeta_raw,
            regiones_raw=regiones_raw,
            url_fuente=url_fuente,
            fecha_scraping=datetime.now(),
        )

    def _hay_siguiente_pagina(self, data: dict) -> bool:
        """Detecta si hay más páginas según la estructura de paginación."""
        if not isinstance(data, dict):
            return False
        # Patrones comunes: last, last_page, hasNext, totalPages vs page
        if data.get("last") is True:
            return False
        if data.get("hasNext") is False:
            return False
        total_pages = data.get("totalPages") or data.get("total_pages")
        current_page = data.get("number") or data.get("page") or 0
        if total_pages and current_page >= total_pages - 1:
            return False
        return bool(data.get("beneficios") or data.get("items") or data.get("content"))
