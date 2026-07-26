"""Заглушка парсера для MOEX."""

import logging

from src.domain.interfaces import Parser

logger = logging.getLogger(__name__)


class MoexParser(Parser):
    """Парсер для сайта MOEX (заглушка)."""

    async def parse(self) -> list[str]:
        """Заглушка: возвращает пустой список."""
        logger.info("MoexParser.parse() — заглушка")
        return []
