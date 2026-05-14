import hashlib

import psycopg2
from loguru import logger

import config
from models.beneficio import BeneficioNormalizado


def fingerprint(b: BeneficioNormalizado) -> str:
    s = f"{b.banco}|{b.comercio.lower().strip()}|{b.descuento.lower().strip()}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def cargar_fingerprints_existentes() -> set[str]:
    """Carga fingerprints de beneficios ya presentes en BD para evitar duplicados."""
    existing: set[str] = set()
    try:
        with psycopg2.connect(config.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT fingerprint FROM beneficios WHERE fingerprint IS NOT NULL")
                rows = cur.fetchall()
                existing = {row[0] for row in rows}
        logger.info(f"Fingerprints existentes en BD: {len(existing)}")
    except Exception as e:
        logger.error(f"No se pudo cargar fingerprints: {e}. Continuando sin deduplicación.")
    return existing


def filtrar_duplicados(
    beneficios: list[BeneficioNormalizado],
    existentes: set[str],
) -> tuple[list[BeneficioNormalizado], int]:
    """Retorna (nuevos, cantidad_duplicados)."""
    nuevos = []
    duplicados = 0
    vistos_en_run: set[str] = set()

    for b in beneficios:
        fp = fingerprint(b)
        if fp in existentes or fp in vistos_en_run:
            duplicados += 1
        else:
            vistos_en_run.add(fp)
            nuevos.append(b)

    logger.info(f"Duplicados filtrados: {duplicados} — Nuevos a insertar: {len(nuevos)}")
    return nuevos, duplicados
