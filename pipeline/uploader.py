import psycopg2
from loguru import logger

import config
from models.beneficio import BeneficioNormalizado
from pipeline.deduplicator import fingerprint


def _cargar_catalogo(cur, tabla: str, col_nombre: str) -> dict[str, int]:
    cur.execute(f"SELECT id, {col_nombre} FROM {tabla}")
    return {row[1]: row[0] for row in cur.fetchall()}


def insertar(beneficios: list[BeneficioNormalizado]) -> int:
    if config.DRY_RUN:
        logger.info(f"[DRY RUN] Se insertarían {len(beneficios)} beneficios.")
        for b in beneficios:
            logger.debug(f"  [{b.banco}] {b.comercio} — {b.categoria} — {b.tarjeta}")
        return 0

    insertados = 0
    with psycopg2.connect(config.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            bancos      = _cargar_catalogo(cur, "bancos", "nombre")
            categorias  = _cargar_catalogo(cur, "categorias", "nombre")
            tarjetas    = _cargar_catalogo(cur, "tipos_tarjeta", "nombre")
            regiones    = _cargar_catalogo(cur, "regiones", "nombre")

            for b in beneficios:
                banco_id    = bancos.get(b.banco)
                categoria_id = categorias.get(b.categoria)
                tarjeta_id  = tarjetas.get(b.tarjeta)

                if not banco_id:
                    logger.warning(f"Banco no encontrado en BD: '{b.banco}' — omitiendo")
                    continue
                if not categoria_id:
                    logger.warning(f"Categoría no encontrada en BD: '{b.categoria}' — omitiendo")
                    continue
                if not tarjeta_id:
                    logger.warning(f"Tarjeta no encontrada en BD: '{b.tarjeta}' — omitiendo")
                    continue

                region_ids = []
                for nombre_region in b.regiones:
                    rid = regiones.get(nombre_region)
                    if rid:
                        region_ids.append(rid)
                    else:
                        logger.warning(f"Región no encontrada en BD: '{nombre_region}'")

                fp = fingerprint(b)

                cur.execute(
                    """
                    INSERT INTO beneficios
                        (comercio, descuento, condiciones, banco_id, categoria_id, tipo_tarjeta_id,
                         url_fuente, activo, fingerprint)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true, %s)
                    ON CONFLICT (fingerprint) DO UPDATE SET
                        descuento   = EXCLUDED.descuento,
                        condiciones = EXCLUDED.condiciones,
                        url_fuente  = EXCLUDED.url_fuente,
                        updated_at  = now()
                    RETURNING id
                    """,
                    (b.comercio, b.descuento, b.condiciones or None, banco_id, categoria_id,
                     tarjeta_id, b.url_fuente, fp),
                )
                row = cur.fetchone()
                if row is None:
                    # ON CONFLICT — ya existía
                    continue

                beneficio_id = row[0]
                for rid in region_ids:
                    cur.execute(
                        "INSERT INTO beneficio_regiones (beneficio_id, region_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (beneficio_id, rid),
                    )

                insertados += 1

        conn.commit()

    logger.info(f"Insertados en BD: {insertados}")
    return insertados
