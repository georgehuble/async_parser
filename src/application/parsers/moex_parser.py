"""Заглушка разборщика HTML для MOEX."""

import logging
from datetime import date

from src.domain.interfaces.parsers import Parser, StopReason

logger = logging.getLogger(__name__)


class MoexParser(Parser):
    """Разбор HTML для сайта MOEX (заглушка)."""

    def parse_links(self, html: str, max_date: date | None = None) -> tuple[list[str], StopReason]:
        """Заглушка: возвращает пустой список ссылок."""
        logger.info("MoexParser.parse_links() — заглушка")
        return [], StopReason.CONTINUE
