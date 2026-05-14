import asyncio
import random
from abc import ABC, abstractmethod

from loguru import logger

import config
from models.beneficio import BeneficioRaw


class BaseScraper(ABC):
    banco_nombre: str = ""

    async def scrape(self) -> list[BeneficioRaw]:
        logger.info(f"[{self.banco_nombre}] Iniciando scraping")
        try:
            items = await self._extraer()
            logger.info(f"[{self.banco_nombre}] {len(items)} beneficios extraídos")
            return items
        except Exception as e:
            logger.error(f"[{self.banco_nombre}] Error durante scraping: {e}")
            raise

    @abstractmethod
    async def _extraer(self) -> list[BeneficioRaw]:
        """Implementar la lógica de extracción específica del banco."""
        ...

    async def _delay(self) -> None:
        """Rate limiting entre requests."""
        delay = random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)
        await asyncio.sleep(delay)

    def _user_agent(self) -> str:
        return random.choice(config.USER_AGENTS)
