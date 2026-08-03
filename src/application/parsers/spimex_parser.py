"""Разбор HTML-страниц сайта Spimex (без сетевых запросов).

Класс отвечает только за разбор (parse) HTML, который предоставил
``SpimexFetch``: извлечение ссылок на бюллетени и определение причины
остановки перебора страниц. Скачивание страниц выполняет ``SpimexFetch`` (SRP).
"""

import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.application.parsers.spimex_config import BASE_URL, CUTOFF_YEAR
from src.domain.interfaces.parsers.parser import Parser, StopReason

logger = logging.getLogger(__name__)


class SpimexParser(Parser):
    """Разбор HTML-страниц сайта Spimex.

    Не выполняет сетевых запросов — только разбирает переданный HTML.
    """

    def extract_date(self, url: str) -> date | None:
        """Извлекает дату из URL Spimex.

        Формат URL:  .../oil_20241217162000.pdf  или  .../oil_xls_20241217162000.xls
        """
        match = re.search(r"(\d{4})(\d{2})(\d{2})\d{6}", url)
        if not match:
            return None
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(year, month, day)

    def parse_links(self, html: str, max_date: date | None = None) -> tuple[list[str], StopReason]:
        """
        Разбирает HTML страницы со списком бюллетеней.

        Возвращает (список ссылок, причина остановки).
        Причина остановки: StopReason.CONTINUE — продолжать,
        StopReason.CUTOFF — достигнут предельный год,
        StopReason.MAX_DATE — на странице встречена дата, уже имеющаяся в БД.
        """
        soup = BeautifulSoup(html, "lxml")
        daily_section = soup.find("div", class_="page-content__tabs__block", attrs={"data-tabcontent": "1"})
        if not daily_section:
            return [], StopReason.CONTINUE
        items = daily_section.find_all("div", class_="accordeon-inner__wrap-item")
        links: list[str] = []
        stop_reason = StopReason.CONTINUE

        for item in items:
            title = item.find("div", class_="accordeon-inner__item-inner__title")
            if not title:
                continue
            span = title.find("span")
            if not span:
                continue

            dt = self._extract_date_from_span(span.get_text(strip=True))
            if dt is None:
                continue

            reason = self._check_stop_reason(dt, max_date)

            # Если год <= CUTOFF_YEAR — прерываем, дальше нет смысла
            if reason is StopReason.CUTOFF:
                stop_reason = StopReason.CUTOFF
                break

            # Если дата уже есть в БД — пропускаем эту ссылку, но продолжаем
            # проверять остальные (могут быть более свежие)
            if reason is StopReason.MAX_DATE:
                stop_reason = StopReason.MAX_DATE
                continue

            link = item.find("a", href=True, string=lambda text: text and "Бюллетень по итогам торгов" in text)
            if link:
                href = link.get("href")
                if isinstance(href, str):
                    links.append(urljoin(BASE_URL, href))

        return links, stop_reason

    @staticmethod
    def _extract_date_from_span(span_text: str) -> date | None:
        """Извлекает дату из текста заголовка вида 'дд.мм.гггг'."""
        try:
            return datetime.strptime(span_text.strip(), "%d.%m.%Y").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _check_stop_reason(dt: date, max_date: date | None) -> StopReason:
        """Проверяет, нужно ли остановить парсинг и по какой причине."""
        if dt.year <= CUTOFF_YEAR:
            return StopReason.CUTOFF
        if max_date is not None and dt <= max_date:
            return StopReason.MAX_DATE
        return StopReason.CONTINUE
