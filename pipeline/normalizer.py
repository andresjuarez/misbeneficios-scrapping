from loguru import logger

from models.beneficio import BeneficioNormalizado, BeneficioRaw

CATEGORIA_MAP: dict[str, str] = {
    # Gastronomía
    "restaurantes":             "Gastronomía",
    "gastronomia":              "Gastronomía",
    "gastronomía":              "Gastronomía",
    "food":                     "Gastronomía",
    "food & drink":             "Gastronomía",
    "comida":                   "Gastronomía",
    "bar y restaurant":         "Gastronomía",
    "cafeterías":               "Gastronomía",
    "cafeterias":               "Gastronomía",
    "delivery":                 "Gastronomía",

    # Viajes
    "viajes":                   "Viajes",
    "turismo":                  "Viajes",
    "travel":                   "Viajes",
    "vuelos":                   "Viajes",
    "hoteles":                  "Viajes",
    "aerolíneas":               "Viajes",
    "aerolineas":               "Viajes",

    # Compras
    "compras":                  "Compras",
    "retail":                   "Compras",
    "shopping":                 "Compras",
    "tiendas":                  "Compras",
    "moda":                     "Compras",
    "vestuario":                "Compras",
    "hogar":                    "Compras",
    "decoración":               "Compras",
    "decoracion":               "Compras",

    # Bencina
    "bencina":                  "Bencina",
    "combustible":              "Bencina",
    "gasolina":                 "Bencina",
    "estaciones de servicio":   "Bencina",
    "autopistas":               "Bencina",

    # Salud
    "salud":                    "Salud",
    "farmacias":                "Salud",
    "health":                   "Salud",
    "bienestar":                "Salud",
    "ópticas":                  "Salud",
    "opticas":                  "Salud",
    "clínicas":                 "Salud",
    "clinicas":                 "Salud",
    "salud y bienestar":        "Salud",

    # Entretenimiento
    "entretenimiento":          "Entretenimiento",
    "cine":                     "Entretenimiento",
    "teatro":                   "Entretenimiento",
    "ocio":                     "Entretenimiento",
    "entertainment":            "Entretenimiento",
    "streaming":                "Entretenimiento",
    "deportes":                 "Entretenimiento",
    "cine y teatro":            "Entretenimiento",

    # Supermercados
    "supermercados":            "Supermercados",
    "supermercado":             "Supermercados",
    "grocery":                  "Supermercados",
    "alimentación":             "Supermercados",
    "alimentacion":             "Supermercados",

    # Tecnología
    "tecnología":               "Tecnología",
    "tecnologia":               "Tecnología",
    "electrónica":              "Tecnología",
    "electronica":              "Tecnología",
    "tech":                     "Tecnología",
    "celulares":                "Tecnología",
    "computación":              "Tecnología",
    "computacion":              "Tecnología",

}

REGION_MAP: dict[str, str] = {
    # Todo Chile
    "todo chile":               "Todas las regiones",
    "todo el país":             "Todas las regiones",
    "todo el pais":             "Todas las regiones",
    "a nivel nacional":         "Todas las regiones",
    "nacional":                 "Todas las regiones",
    "all":                      "Todas las regiones",
    "todas":                    "Todas las regiones",
    "todo el territorio":       "Todas las regiones",

    # RM
    "region metropolitana":     "Región Metropolitana",
    "región metropolitana":     "Región Metropolitana",
    "metropolitana":            "Región Metropolitana",
    "santiago":                 "Región Metropolitana",
    "rm":                       "Región Metropolitana",

    # Resto
    "valparaiso":               "Valparaíso",
    "valparaíso":               "Valparaíso",
    "viña del mar":             "Valparaíso",
    "vina del mar":             "Valparaíso",
    "biobio":                   "Biobío",
    "bío-bío":                  "Biobío",
    "bio-bio":                  "Biobío",
    "biobío":                   "Biobío",
    "concepcion":               "Biobío",
    "concepción":               "Biobío",
    "la araucania":             "La Araucanía",
    "la araucanía":             "La Araucanía",
    "araucanía":                "La Araucanía",
    "araucania":                "La Araucanía",
    "temuco":                   "La Araucanía",
    "maule":                    "Maule",
    "talca":                    "Maule",
    "ohiggins":                 "O'Higgins",
    "o'higgins":                "O'Higgins",
    "libertador general...":    "O'Higgins",
    "rancagua":                 "O'Higgins",
    "los lagos":                "Los Lagos",
    "puerto montt":             "Los Lagos",
    "antofagasta":              "Antofagasta",
    "coquimbo":                 "Coquimbo",
    "la serena":                "Coquimbo",
    "los rios":                 "Los Ríos",
    "los ríos":                 "Los Ríos",
    "valdivia":                 "Los Ríos",
    "atacama":                  "Atacama",
    "copiapo":                  "Atacama",
    "copiapó":                  "Atacama",
    "tarapaca":                 "Tarapacá",
    "tarapacá":                 "Tarapacá",
    "iquique":                  "Tarapacá",
    "aysen":                    "Aysén",
    "aysén":                    "Aysén",
    "magallanes":               "Magallanes",
    "punta arenas":             "Magallanes",
    "arica":                    "Arica y Parinacota",
    "arica y parinacota":       "Arica y Parinacota",
    "nuble":                    "Ñuble",
    "ñuble":                    "Ñuble",
    "chillan":                  "Ñuble",
    "chillán":                  "Ñuble",
}

TARJETA_MAP: dict[str, str] = {
    "visa":             "Visa",
    "mastercard":       "Mastercard",
    "master card":      "Mastercard",
    "american express": "American Express",
    "amex":             "American Express",
}

BANCO_MAP: dict[str, str] = {
    "banco de chile":   "BancoChile",
    "bancochile":       "BancoChile",
    "bci":              "BCI",
    "banco bci":        "BCI",
    "santander":        "Santander",
    "banco santander":  "Santander",
    "bancoestado":      "BancoEstado",
    "banco estado":     "BancoEstado",
    "scotiabank":       "Scotiabank",
    "itau":             "Itaú",
    "itaú":             "Itaú",
    "falabella":        "Falabella",
    "banco falabella":  "Falabella",
    "ripley":           "Ripley",
    "banco ripley":     "Ripley",
    "bice":             "BICE",
    "security":         "Security",
    "banco security":   "Security",
}

CATEGORIAS_VALIDAS = {
    "Gastronomía", "Viajes", "Compras", "Bencina",
    "Salud", "Entretenimiento", "Supermercados", "Tecnología",
}
TARJETAS_VALIDAS = {"Visa", "Mastercard", "American Express"}
REGIONES_VALIDAS = {
    "Todas las regiones", "Región Metropolitana", "Valparaíso",
    "Biobío", "La Araucanía", "Maule", "O'Higgins", "Los Lagos",
    "Antofagasta", "Coquimbo", "Los Ríos", "Atacama", "Tarapacá",
    "Aysén", "Magallanes", "Arica y Parinacota", "Ñuble",
}


def normalizar_categoria(raw: str) -> str | None:
    key = raw.lower().strip()
    result = CATEGORIA_MAP.get(key)
    if result is None:
        logger.warning(f"Categoría desconocida: '{raw}'")
    return result


def normalizar_region(raw: str) -> str | None:
    key = raw.lower().strip()
    result = REGION_MAP.get(key)
    if result is None:
        logger.warning(f"Región desconocida: '{raw}'")
    return result


def normalizar_tarjeta(raw: str) -> str:
    key = raw.lower().strip()
    for pattern, canonical in TARJETA_MAP.items():
        if pattern in key:
            return canonical
    return "Visa"


def normalizar_regiones(regiones_raw: list[str]) -> list[str]:
    if not regiones_raw:
        return ["Todas las regiones"]

    normalizadas = []
    for r in regiones_raw:
        norm = normalizar_region(r)
        if norm and norm not in normalizadas:
            normalizadas.append(norm)

    if not normalizadas:
        return ["Todas las regiones"]

    return normalizadas


def normalizar(raw: BeneficioRaw) -> BeneficioNormalizado | None:
    categoria = normalizar_categoria(raw.categoria_raw)
    categoria_pendiente = categoria is None
    if categoria_pendiente:
        categoria = raw.categoria_raw  # guardar original para revisión

    tarjeta = normalizar_tarjeta(raw.tarjeta_raw)
    regiones = normalizar_regiones(raw.regiones_raw)

    return BeneficioNormalizado(
        banco=raw.banco,
        comercio=raw.comercio.strip(),
        descuento=raw.descuento.strip(),
        categoria=categoria,
        tarjeta=tarjeta,
        regiones=regiones,
        url_fuente=raw.url_fuente,
        fecha_scraping=raw.fecha_scraping,
        categoria_pendiente=categoria_pendiente,
    )


def normalizar_todos(raws: list[BeneficioRaw]) -> list[BeneficioNormalizado]:
    resultados = []
    for raw in raws:
        try:
            norm = normalizar(raw)
            if norm:
                resultados.append(norm)
        except Exception as e:
            logger.error(f"Error normalizando beneficio de {raw.banco} / {raw.comercio}: {e}")
    return resultados
