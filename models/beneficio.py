from datetime import datetime
from pydantic import BaseModel, field_validator


class BeneficioRaw(BaseModel):
    banco: str
    comercio: str
    descuento: str
    categoria_raw: str
    tarjeta_raw: str = ""
    regiones_raw: list[str] = []
    url_fuente: str
    fecha_scraping: datetime = None

    @field_validator("fecha_scraping", mode="before")
    @classmethod
    def set_fecha(cls, v):
        return v or datetime.now()


class BeneficioNormalizado(BaseModel):
    banco: str
    comercio: str
    descuento: str
    categoria: str
    tarjeta: str
    regiones: list[str]
    url_fuente: str
    fecha_scraping: datetime
    categoria_pendiente: bool = False


class ResultadoScraping(BaseModel):
    banco: str
    total_extraidos: int
    total_normalizados: int
    total_insertados: int
    total_duplicados: int
    errores: list[str] = []
    duracion_segundos: float
