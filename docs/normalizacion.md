# Normalización de datos

El normalizer transforma lo que extrae el scraper (datos crudos, con los nombres y formatos propios de cada banco) al modelo canónico de misBeneficios.

## Por qué es crítica esta etapa

Banco A llama "Restaurantes" a lo que Banco B llama "Food & Drink" y lo que Banco C llama "Gastronomía". Sin normalización, la BD tendría categorías duplicadas y los filtros del frontend no funcionarían.

---

## 1. Normalización de categorías

### Tabla de mapeo

```python
CATEGORIA_MAP: dict[str, str] = {
    # Gastronomía
    "restaurantes":         "Gastronomía",
    "gastronomia":          "Gastronomía",
    "gastronomía":          "Gastronomía",
    "food":                 "Gastronomía",
    "food & drink":         "Gastronomía",
    "comida":               "Gastronomía",
    "bar y restaurant":     "Gastronomía",
    "cafeterías":           "Gastronomía",

    # Viajes
    "viajes":               "Viajes",
    "turismo":              "Viajes",
    "travel":               "Viajes",
    "vuelos":               "Viajes",
    "hoteles":              "Viajes",
    "aerolíneas":           "Viajes",

    # Compras
    "compras":              "Compras",
    "retail":               "Compras",
    "shopping":             "Compras",
    "tiendas":              "Compras",
    "moda":                 "Compras",
    "vestuario":            "Compras",

    # Bencina
    "bencina":              "Bencina",
    "combustible":          "Bencina",
    "gasolina":             "Bencina",
    "estaciones de servicio": "Bencina",
    "autopistas":           "Bencina",  # podría mapearse a Viajes según contexto

    # Salud
    "salud":                "Salud",
    "farmacias":            "Salud",
    "health":               "Salud",
    "bienestar":            "Salud",
    "ópticas":              "Salud",
    "clínicas":             "Salud",

    # Entretenimiento
    "entretenimiento":      "Entretenimiento",
    "cine":                 "Entretenimiento",
    "teatro":               "Entretenimiento",
    "ocio":                 "Entretenimiento",
    "entertainment":        "Entretenimiento",
    "streaming":            "Entretenimiento",
    "deportes":             "Entretenimiento",

    # Supermercados
    "supermercados":        "Supermercados",
    "supermercado":         "Supermercados",
    "grocery":              "Supermercados",
    "alimentación":         "Supermercados",

    # Tecnología
    "tecnología":           "Tecnología",
    "tecnologia":           "Tecnología",
    "electrónica":          "Tecnología",
    "tech":                 "Tecnología",
    "celulares":            "Tecnología",
    "computación":          "Tecnología",
}

def normalizar_categoria(raw: str) -> str | None:
    key = raw.lower().strip()
    return CATEGORIA_MAP.get(key)
    # Si retorna None → categoría desconocida, loguear y revisar manualmente
```

### Categorías desconocidas

Cuando el normalizer no encuentra un mapeo, el beneficio se marca como `categoria_pendiente=True` y se loguea. Un operador puede revisarlos y agregar el mapeo faltante a la tabla.

---

## 2. Normalización de regiones

### Regiones canónicas (las de nuestra BD)

```
Todas las regiones
Región Metropolitana
Valparaíso
Biobío
La Araucanía
Maule
O'Higgins
Los Lagos
Antofagasta
Coquimbo
Los Ríos
Atacama
Tarapacá
Aysén
Magallanes
Arica y Parinacota
Ñuble
```

### Tabla de mapeo

```python
REGION_MAP: dict[str, str] = {
    # Todo chile
    "todo chile":               "Todas las regiones",
    "todo el país":             "Todas las regiones",
    "a nivel nacional":         "Todas las regiones",
    "nacional":                 "Todas las regiones",
    "all":                      "Todas las regiones",

    # RM
    "region metropolitana":     "Región Metropolitana",
    "región metropolitana":     "Región Metropolitana",
    "metropolitana":            "Región Metropolitana",
    "santiago":                 "Región Metropolitana",
    "rm":                       "Región Metropolitana",

    # Resto de regiones (normalizar tildes y variantes)
    "valparaiso":               "Valparaíso",
    "valparaíso":               "Valparaíso",
    "biobio":                   "Biobío",
    "bío-bío":                  "Biobío",
    "la araucania":             "La Araucanía",
    "araucanía":                "La Araucanía",
    "ohiggins":                 "O'Higgins",
    "o'higgins":                "O'Higgins",
    "libertador general...":    "O'Higgins",
    "los lagos":                "Los Lagos",
    "antofagasta":              "Antofagasta",
    "coquimbo":                 "Coquimbo",
    "los rios":                 "Los Ríos",
    "los ríos":                 "Los Ríos",
    "atacama":                  "Atacama",
    "tarapaca":                 "Tarapacá",
    "tarapacá":                 "Tarapacá",
    "aysen":                    "Aysén",
    "aysén":                    "Aysén",
    "magallanes":               "Magallanes",
    "arica":                    "Arica y Parinacota",
    "arica y parinacota":       "Arica y Parinacota",
    "nuble":                    "Ñuble",
    "ñuble":                    "Ñuble",
    "maule":                    "Maule",
}
```

### Lógica de inferencia

Si un banco no especifica regiones para un beneficio, la lógica es:
1. Si la vigencia dice "a nivel nacional" → `["Todas las regiones"]`
2. Si lista ciudades (ej: "Santiago, Viña del Mar") → mapear cada ciudad a su región
3. Si no hay info → `["Todas las regiones"]` (asumir nacional, marcarlo para revisión)

---

## 3. Normalización de tipo de tarjeta

```python
TARJETA_MAP: dict[str, str] = {
    "visa":             "Visa",
    "mastercard":       "Mastercard",
    "master card":      "Mastercard",
    "american express": "American Express",
    "amex":             "American Express",
    "american express": "American Express",
}

def normalizar_tarjeta(raw: str) -> str:
    key = raw.lower().strip()
    for pattern, canonical in TARJETA_MAP.items():
        if pattern in key:
            return canonical
    return "Visa"  # default: la mayoría de tarjetas de crédito en Chile son Visa
```

### Caso especial: beneficio para todas las tarjetas

Algunos beneficios no especifican tarjeta. En ese caso se puede:
- Crear **un registro por tipo de tarjeta** del banco (Visa + Mastercard)
- O crear **un solo registro sin tipo** (requeriría cambio en el modelo de BD)

Recomendación: crear un registro por cada tipo de tarjeta que emite el banco.

---

## 4. Normalización de nombres de banco

```python
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
```

---

## 5. Detección de duplicados

Un beneficio es duplicado si ya existe en BD con la misma combinación de:
- `banco` + `comercio` + `descuento` (hash de los 3 campos normalizados)

```python
import hashlib

def fingerprint(b: BeneficioNormalizado) -> str:
    s = f"{b.banco}|{b.comercio.lower().strip()}|{b.descuento.lower().strip()}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]
```

El deduplicator consulta los fingerprints existentes en BD al inicio de cada run y filtra los ya procesados.

---

## 6. Validaciones finales antes de insertar

```python
CATEGORIAS_VALIDAS = {
    "Gastronomía", "Viajes", "Compras", "Bencina",
    "Salud", "Entretenimiento", "Supermercados", "Tecnología"
}
TARJETAS_VALIDAS = {"Visa", "Mastercard", "American Express"}
REGIONES_VALIDAS = {
    "Todas las regiones", "Región Metropolitana", "Valparaíso",
    "Biobío", "La Araucanía", "Maule", "O'Higgins", "Los Lagos",
    "Antofagasta", "Coquimbo", "Los Ríos", "Atacama", "Tarapacá",
    "Aysén", "Magallanes", "Arica y Parinacota", "Ñuble"
}

def validar(b: BeneficioNormalizado) -> bool:
    assert b.categoria in CATEGORIAS_VALIDAS, f"Categoría inválida: {b.categoria}"
    assert b.tarjeta in TARJETAS_VALIDAS, f"Tarjeta inválida: {b.tarjeta}"
    assert all(r in REGIONES_VALIDAS for r in b.regiones), f"Región inválida: {b.regiones}"
    assert len(b.comercio) > 0, "Comercio vacío"
    assert len(b.descuento) > 10, "Descuento muy corto"
    return True
```
