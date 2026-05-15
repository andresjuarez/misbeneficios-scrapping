"""
Orquestador principal del sistema de scraping de misBeneficios.

Uso:
  python main.py                    # corre todos los scrapers habilitados
  python main.py --banco santander  # solo un banco
  python main.py --dry-run          # extrae y normaliza pero no inserta
"""
import asyncio
import os
import sys
import time
from argparse import ArgumentParser

from loguru import logger

import config
from models.beneficio import ResultadoScraping
from pipeline.deduplicator import cargar_fingerprints_existentes, filtrar_duplicados
from pipeline.normalizer import normalizar_todos
from pipeline.uploader import insertar
from scrapers.bancochile import BancoChileScraper
from scrapers.santander import SantanderScraper

os.makedirs("logs", exist_ok=True)

logger.remove()
logger.add(sys.stderr, level=config.LOG_LEVEL)
logger.add(config.LOG_FILE, level="DEBUG", rotation="10 MB", compression="zip")

SCRAPERS = {
    "santander":  SantanderScraper,
    "bancochile": BancoChileScraper,
    # Próximos:
    # "bci": BCIScraper,
    # "falabella": FalabellaScraper,
    # "bancoestado": BancoEstadoScraper,
}


async def run_scraper(nombre: str, ScraperClass, fingerprints_existentes: set[str]) -> ResultadoScraping:
    inicio = time.time()
    scraper = ScraperClass()
    errores = []

    try:
        raws = await scraper.scrape()
    except Exception as e:
        errores.append(str(e))
        return ResultadoScraping(
            banco=nombre,
            total_extraidos=0,
            total_normalizados=0,
            total_insertados=0,
            total_duplicados=0,
            errores=errores,
            duracion_segundos=round(time.time() - inicio, 1),
        )

    normalizados = normalizar_todos(raws)
    nuevos, duplicados = filtrar_duplicados(normalizados, fingerprints_existentes)

    try:
        insertados = insertar(nuevos)
    except Exception as e:
        errores.append(f"Error al insertar: {e}")
        insertados = 0

    return ResultadoScraping(
        banco=nombre,
        total_extraidos=len(raws),
        total_normalizados=len(normalizados),
        total_insertados=insertados,
        total_duplicados=duplicados,
        errores=errores,
        duracion_segundos=round(time.time() - inicio, 1),
    )


async def main(bancos: list[str] | None = None) -> None:
    if config.DRY_RUN:
        logger.info("Modo DRY RUN activo — no se insertará nada en BD")

    scrapers_a_correr = {
        nombre: cls
        for nombre, cls in SCRAPERS.items()
        if bancos is None or nombre in bancos
    }

    if not scrapers_a_correr:
        logger.warning(f"Ningún scraper encontrado para: {bancos}")
        return

    fingerprints_existentes = cargar_fingerprints_existentes()

    resultados: list[ResultadoScraping] = []
    for nombre, cls in scrapers_a_correr.items():
        logger.info(f"--- Iniciando {nombre} ---")
        resultado = await run_scraper(nombre, cls, fingerprints_existentes)
        resultados.append(resultado)

    _imprimir_resumen(resultados)


def _imprimir_resumen(resultados: list[ResultadoScraping]) -> None:
    logger.info("=" * 50)
    logger.info("RESUMEN DE EJECUCIÓN")
    logger.info("=" * 50)
    for r in resultados:
        status = "OK" if not r.errores else "ERROR"
        logger.info(
            f"[{status}] {r.banco}: "
            f"extraídos={r.total_extraidos} "
            f"normalizados={r.total_normalizados} "
            f"insertados={r.total_insertados} "
            f"duplicados={r.total_duplicados} "
            f"({r.duracion_segundos}s)"
        )
        for err in r.errores:
            logger.error(f"  Error: {err}")
    logger.info("=" * 50)


if __name__ == "__main__":
    parser = ArgumentParser(description="misBeneficios scraper")
    parser.add_argument("--banco", nargs="+", help="Nombres de bancos a scrapear (ej: santander bci)")
    parser.add_argument("--dry-run", action="store_true", help="No insertar en BD")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        # Recargar config (simplificado: setear directamente)
        config.DRY_RUN = True

    asyncio.run(main(bancos=args.banco))
