"""Извлечение сделок из файлов бюллетеней Spimex (XLS/XLSX/PDF).

Класс отвечает за извлечение (extract) данных из скачанных файлов: разбор
XLS/XLSX/PDF-бюллетеней, формирование доменных сущностей сделок (TradeEntity)
и запись их в БД через абстракции репозиториев (DIP). Формат файла учитывается:
XLS/XLSX разбираются через pandas, PDF — через camelot (таблицы) и pypdfium2
(заголовки 'Дата торгов:'/'Единица измерения:' по координатам), неизвестные
форматы пропускаются с предупреждением.

Производительность: camelot/pypdfium2 не потокобезопасны, поэтому PDF
разбираются в отдельных процессах (ProcessPoolExecutor) — потоки с конкурентным
camelot зависают или роняют процесс. XLS/XLSX (pandas) потокобезопасны и
разбираются в потоках через asyncio.to_thread.
"""

import asyncio
import logging
import multiprocessing
import os
import re
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any

import camelot
import pandas as pd
import pypdfium2 as pdfium
from tqdm.auto import tqdm

from src.domain.entities import TradeEntity
from src.domain.interfaces.parsers import Extract
from src.domain.interfaces.repositories import (
    DeliveryBasisRepositoryAbstract,
    DeliveryTypeRepositoryAbstract,
    OilProductRepositoryAbstract,
    TradeRepositoryAbstract,
)
from src.domain.value_objects import Money, Volume

logger = logging.getLogger(__name__)

# Каталог со скачанными файлами (общий с SpimexDownloader)
DOWNLOADERS_DIR = Path(__file__).resolve().parent.parent / "downloaders"
FILES_DIR = DOWNLOADERS_DIR / "files"


class SpimexExtract(Extract):
    """Извлечение сделок из файлов бюллетеней Spimex.

    Принимает список файлов (path, name), разбирает XLS-бюллетени и
    сохраняет извлечённые сделки в БД через абстракции репозиториев.
    """

    # Код инструмента (например, 'A592KOB060F', 'TRD-PYG060R')
    CODE_PATTERN = re.compile(r"^[A-Z0-9-]{5,20}$")
    DATE_PREFIX = "Дата торгов:"
    UNIT_PREFIX = "Единица измерения:"
    # Периодичность вывода лога INFO о ходе извлечения (в дополнение к tqdm)
    LOG_INTERVAL = 100
    # Число воркеров-разборщиков: XLS/XLSX разбираются в потоках (pandas
    # потокобезопасен), PDF — в отдельных процессах (camelot не потокобезопасен).
    # WORKERS должно быть не меньше PDF_WORKERS, чтобы пул процессов был занят
    WORKERS = 8
    # Размер пула процессов для разбора PDF. Не больше числа ядер и числа воркеров:
    # каждый camelot внутри сам распараллеливается (OpenCV), поэтому берём потолок 8
    PDF_WORKERS = min(WORKERS, os.cpu_count() or 4)

    def __init__(
        self,
        exchange_id: int,
        trade_repository: TradeRepositoryAbstract,
        oil_product_repository: OilProductRepositoryAbstract,
        delivery_basis_repository: DeliveryBasisRepositoryAbstract,
        delivery_type_repository: DeliveryTypeRepositoryAbstract,
    ) -> None:
        """Инициализирует экстрактор.

        Args:
            exchange_id: Идентификатор биржевого источника (SPIMEX).
            trade_repository: Репозиторий сделок (запись в БД).
            oil_product_repository: Репозиторий справочника нефтепродуктов.
            delivery_basis_repository: Репозиторий справочника базисов поставки.
            delivery_type_repository: Репозиторий справочника типов поставки.
        """
        self._exchange_id = exchange_id
        self._trade_repository = trade_repository
        self._oil_product_repository = oil_product_repository
        self._delivery_basis_repository = delivery_basis_repository
        self._delivery_type_repository = delivery_type_repository

        # Кэши справочников и URL бюллетеней — избегаем N+1 запросов к БД
        self._oil_product_ids: dict[tuple[str, int], int | None] = {}
        self._delivery_bases: set[str] = set()
        self._delivery_types: set[str] = set()
        self._bulletin_urls: dict[tuple[date, int], str] = {}
        self._seen_trade_ids: set[str] = set()

    async def extract(self, files: list[tuple[str, str]]) -> None:
        """Извлекает сделки из файлов (path, name) и сохраняет их в БД.

        Разбор файлов — синхронная CPU-работа, поэтому выполняется в фоне, не
        блокируя event loop: XLS/XLSX (pandas) — параллельно в потоках через
        asyncio.to_thread, PDF (camelot/pypdfium2) — в отдельных процессах через
        ProcessPoolExecutor, т.к. camelot не потокобезопасен (конкурентные потоки
        зависают или роняют процесс повреждением кучи). Запись в БД выполняет
        единственный потребитель результатов строго последовательно: общая
        AsyncSession не рассчитана на конкурентные запросы, а кэши справочников и
        дедупликация сделок (_seen_trade_ids) требуют последовательной обработки.
        Это исключает N+1 запросов к БД.

        Args:
            files: Список кортежей (путь к файлу, имя файла).
        """
        if not files:
            logger.info("Нет файлов для извлечения")
            await self._trade_repository.commit()
            return

        workers_count = min(self.WORKERS, len(files))
        # Пул процессов нужен только если в списке есть PDF — иначе лишние процессы
        pdf_count = sum(1 for path, _ in files if Path(path).suffix.lower() == ".pdf")
        process_pool = self._make_process_pool() if pdf_count else None

        # Очередь задач: воркеры берут по одному файлу и разбирают его
        tasks: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
        for path, name in files:
            tasks.put_nowait((path, name))
        # Сентинелы завершения — по одному на воркера
        for _ in range(workers_count):
            tasks.put_nowait(None)

        # Очередь результатов: (name, path, trades); trades=None — файл не разобран.
        # Потребитель результатов один, поэтому запись в БД не создаёт гонок.
        # Ограниченный размер даёт backpressure: воркеры ждут, пока потребитель освободит место.
        results: asyncio.Queue[tuple[str, str, list[TradeEntity] | None] | None] = asyncio.Queue(
            maxsize=workers_count * 2
        )

        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(self._save_worker(results, len(files), workers_count))
                for _ in range(workers_count):
                    group.create_task(self._parse_worker(tasks, results, process_pool))
        except* Exception:
            # Сбой одного воркера отменяет остальных через TaskGroup — логируем и пробрасываем
            logger.exception("Ошибка при параллельном извлечении файлов")
            raise
        finally:
            if process_pool is not None:
                process_pool.shutdown(wait=True, cancel_futures=True)

    @staticmethod
    def _make_process_pool() -> ProcessPoolExecutor:
        """Создаёт пул процессов для разбора PDF.

        Используется контекст forkserver: он безопасен при вызове из
        многопоточного процесса (asyncio.to_thread уже запускал потоки), в отличие
        от fork, который в дочернем процессе может унаследовать блокировки чужих
        потоков и зависнуть.
        """
        context = multiprocessing.get_context("forkserver")
        return ProcessPoolExecutor(max_workers=SpimexExtract.PDF_WORKERS, mp_context=context)

    async def _parse_worker(
        self,
        tasks: asyncio.Queue[tuple[str, str] | None],
        results: asyncio.Queue[tuple[str, str, list[TradeEntity] | None] | None],
        process_pool: ProcessPoolExecutor | None,
    ) -> None:
        """Разбирает файлы из очереди задач и кладёт результаты в очередь результатов.

        Args:
            tasks: Очередь файлов (path, name) с сентинелами завершения.
            results: Очередь результатов (name, path, trades).
            process_pool: Пул процессов для PDF (None, если PDF в списке нет).
        """
        while True:
            item = await tasks.get()
            if item is None:
                break
            path, name = item
            file_path = Path(path)
            try:
                # XLS/XLSX: pandas потокобезопасен, разбираются параллельно в потоках.
                # PDF: camelot/pypdfium2 не потокобезопасны — разбираются в процессах,
                # изолированных от event loop и друг от друга
                if process_pool is not None and file_path.suffix.lower() == ".pdf":
                    trades = await asyncio.get_running_loop().run_in_executor(
                        process_pool,
                        _parse_pdf_in_process,
                        str(file_path),
                        self._exchange_id,
                    )
                else:
                    trades = await asyncio.to_thread(self.parse_file, file_path)
            except Exception as exc:
                logger.error("Ошибка извлечения из %s (%s): %s", name, path, exc)
                trades = None
            await results.put((name, path, trades))
        await results.put(None)

    async def _save_worker(
        self,
        results: asyncio.Queue[tuple[str, str, list[TradeEntity] | None] | None],
        total: int,
        workers_count: int,
    ) -> None:
        """Последовательно сохраняет результаты разбора в БД и коммитит транзакцию."""
        saved = 0
        stops = 0
        processed = 0
        with tqdm(total=total, unit=" файлов", desc="Извлечение сделок") as pbar:
            while stops < workers_count:
                item = await results.get()
                if item is None:
                    stops += 1
                    continue
                name, path, trades = item
                if trades:
                    try:
                        saved += await self._save_trades(trades)
                    except Exception as exc:
                        logger.error("Ошибка сохранения из %s (%s): %s", name, path, exc)
                processed += 1
                pbar.update(1)
                if processed % self.LOG_INTERVAL == 0:
                    logger.info(
                        "Обработано %d из %d файлов (накоплено сделок: %d)",
                        processed,
                        total,
                        saved,
                    )
        await self._trade_repository.commit()
        logger.info("Сохранено сделок: %d", saved)

    def parse_file(self, file_path: Path) -> list[TradeEntity]:
        """Разбирает один файл в зависимости от его формата.

        Args:
            file_path: Путь к файлу бюллетеня.

        Returns:
            Список извлечённых сделок (TradeEntity).
        """
        suffix = file_path.suffix.lower()
        if suffix in (".xls", ".xlsx"):
            return self._extract_xls(file_path)
        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        logger.warning("Неизвестный формат файла '%s': %s", suffix, file_path)
        return []

    def _extract_xls(self, file_path: Path) -> list[TradeEntity]:
        """Разбирает XLS/XLSX-бюллетень в список сделок."""
        df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=object)
        return self._parse_table(df, file_path)

    def _extract_pdf(self, file_path: Path) -> list[TradeEntity]:
        """Разбирает PDF-бюллетень в список сделок через camelot и pypdfium2.

        Таблицы извлекаются camelot (flavor=lattice, требуется Ghostscript) —
        их структура колонок совпадает с XLS (код инструмента, наименование,
        базис, объём, сумма, количество договоров). Заголовки 'Дата торгов:' и
        'Единица измерения:' находятся вне таблиц: они берутся из текстовых
        прямоугольников pypdfium2 и привязываются к таблицам по координатам
        (единица измерений берётся из ближайшей строки выше таблицы).
        """
        tables = camelot.read_pdf(str(file_path), pages="all", flavor="lattice")
        if tables.n == 0:
            return []

        rows: list[list[Any]] = []
        trade_date: str | None = None
        current_unit: str | None = None
        # Заголовки страниц: страница (0-based) -> [(y_center, текст) сверху вниз]
        page_units: dict[int, list[tuple[float, str]]] = {}

        with pdfium.PdfDocument(str(file_path)) as pdf:
            for page_idx in range(len(pdf)):
                text_page = pdf[page_idx].get_textpage()
                units: list[tuple[float, str]] = []
                rect_count = text_page.count_rects()
                for rect_idx in range(rect_count):
                    rect = text_page.get_rect(rect_idx)
                    text = " ".join(
                        text_page.get_text_bounded(rect[0], rect[1], rect[2], rect[3]).split()
                    )
                    if not text:
                        continue
                    y_center = (rect[1] + rect[3]) / 2
                    if text.startswith(self.UNIT_PREFIX):
                        units.append((y_center, text))
                    elif text.startswith(self.DATE_PREFIX) and trade_date is None:
                        trade_date = text
                page_units[page_idx] = sorted(units, key=lambda item: item[0], reverse=True)

        # camelot нумерует страницы с 1 — приводим к 0-based индексации pypdfium2
        by_page: dict[int, list[Any]] = {}
        for table in tables:
            by_page.setdefault(table.page - 1, []).append(table)

        for page_idx in sorted(by_page):
            units = page_units.get(page_idx, [])
            unit_idx = 0
            for table in sorted(by_page[page_idx], key=lambda t: t.order):
                table_top = table.rows[0][0] if table.rows else 0.0
                # Единицы измерения идут сверху вниз: пока очередная выше таблицы —
                # она задаёт единицу для текущей (и последующих) секции
                while unit_idx < len(units) and units[unit_idx][0] > table_top:
                    current_unit = units[unit_idx][1]
                    unit_idx += 1
                if current_unit:
                    rows.append([None, current_unit])
                for data_row in table.data:
                    rows.append(self._normalize_pdf_row(data_row))

        if trade_date is not None:
            rows.insert(0, [None, trade_date])

        if not rows:
            return []
        return self._parse_table(pd.DataFrame(rows), file_path)

    @staticmethod
    def _normalize_pdf_row(raw_row: list[Any]) -> list[Any]:
        """Выравнивает строку таблицы PDF к формату XLS (пустая первая колонка).

        camelot возвращает код инструмента в первой колонке, а XLS-таблицы имеют
        пустую первую колонку и код во второй — добавляем None слева, чтобы
        колонки 4 (объём), 5 (сумма) и 14 (количество) совпали с XLS.
        """
        return [None] + [
            re.sub(r"\s+", " ", str(cell).replace("\n", " ")).strip() if cell is not None else None
            for cell in raw_row
        ]

    async def _save_trades(self, trades: list[TradeEntity]) -> int:
        """Разрешает справочники и добавляет новые сделки (пропуская существующие).

        Args:
            trades: Сделки из одного файла.

        Returns:
            Количество добавленных сделок.
        """
        if not trades:
            return 0

        for trade in trades:
            await self._resolve_references(trade)

        # Пропускаем сделки, уже существующие в БД или добавленные в этом запуске
        existing = await self._trade_repository.get_existing_trade_ids(
            self._exchange_id,
            [trade.exchange_trade_id for trade in trades if trade.exchange_trade_id],
        )
        new_trades: list[TradeEntity] = []
        for trade in trades:
            trade_id = trade.exchange_trade_id
            if not trade_id or trade_id in self._seen_trade_ids or trade_id in existing:
                continue
            self._seen_trade_ids.add(trade_id)
            new_trades.append(trade)

        await self._trade_repository.add_trades(new_trades)
        return len(new_trades)

    async def _resolve_references(self, trade: TradeEntity) -> None:
        """Разрешает product_id и справочники (с кэшем), url бюллетеня по дате."""
        exchange_id = trade.exchange_id or 0

        # Нефтепродукт: кэш (exchange_product_id, exchange_id) -> product_id
        if trade.exchange_product_id:
            cache_key = (trade.exchange_product_id, exchange_id)
            if cache_key not in self._oil_product_ids:
                product = await self._oil_product_repository.get_or_create(
                    exchange_product_id=trade.exchange_product_id,
                    name=trade.exchange_product_name,
                    oil_id=trade.oil_id,
                    exchange_id=exchange_id,
                )
                self._oil_product_ids[cache_key] = product.product_id
            trade.product_id = self._oil_product_ids[cache_key]

        # Базис поставки (кэш по business-ключу)
        if trade.delivery_basis_id and trade.delivery_basis_id not in self._delivery_bases:
            await self._delivery_basis_repository.get_or_create(
                trade.delivery_basis_id,
                trade.delivery_basis_name,
            )
            self._delivery_bases.add(trade.delivery_basis_id)

        # Тип поставки (кэш по business-ключу)
        if trade.delivery_type_id and trade.delivery_type_id not in self._delivery_types:
            await self._delivery_type_repository.get_or_create(trade.delivery_type_id)
            self._delivery_types.add(trade.delivery_type_id)

        # URL бюллетеня — один запрос на (дата, exchange_id), а не на сделку
        if trade.date is not None:
            url_key = (trade.date, exchange_id)
            if url_key not in self._bulletin_urls:
                self._bulletin_urls[url_key] = (
                    await self._trade_repository.get_bulletin_url_by_date(*url_key)
                ) or ""
            trade.url = self._bulletin_urls[url_key] or trade.file_path or ""
        else:
            trade.url = trade.file_path or ""

    def _parse_table(self, df: pd.DataFrame, file_path: Path) -> list[TradeEntity]:
        """Преобразует таблицу бюллетеня (TRADE_SUMMARY) в список сделок.

        Структура листа (может содержать несколько секций с повторяющимися
        шапками):
        - строка 'Дата торгов: дд.мм.гггг' — дата торгов;
        - строка 'Единица измерения: ...' — единица измерения секции;
        - строки сделок: код инструмента, наименование, базис, объём,
          объём в руб., ..., количество договоров.
        """
        trades: list[TradeEntity] = []
        trade_date: date | None = None
        unit = "т"

        for _, row in df.iterrows():
            marker = self._cell_str(row, 1)

            if marker.startswith(self.DATE_PREFIX):
                trade_date = self._parse_date(marker)
                continue

            if marker.startswith(self.UNIT_PREFIX):
                if "Декалитр" in marker:
                    unit = "дал"
                elif "Килограмм" in marker:
                    unit = "кг"
                else:
                    unit = "т"
                continue

            if not self.CODE_PATTERN.fullmatch(marker):
                continue

            if trade_date is None:
                logger.warning("Не найдена дата торгов до строки с кодом %s", marker)
                continue

            volume = self._cell_float(row, 4)
            total = self._cell_float(row, 5)
            count = self._cell_int(row, 14)

            # Строки без сделок (только котировки) не сохраняем
            if volume is None and count is None:
                continue

            trades.append(
                TradeEntity(
                    exchange_id=self._exchange_id,
                    exchange_trade_id=f"{trade_date.isoformat()}:{marker}",
                    file_path=self._relative_path(file_path),
                    date=trade_date,
                    exchange_product_id=marker,
                    exchange_product_name=self._cell_str(row, 2),
                    oil_id=marker[:4],
                    delivery_basis_id=marker[4:7],
                    delivery_basis_name=self._cell_str(row, 3),
                    delivery_type_id=marker[-1],
                    volume=Volume(value=volume, unit=unit) if volume is not None else None,
                    total=Money(amount=total) if total is not None else None,
                    count=count,
                )
            )

        return trades

    @classmethod
    def _relative_path(cls, file_path: Path) -> str:
        """Возвращает путь относительно каталога downloaders (как у загрузчика)."""
        try:
            return str(file_path.relative_to(DOWNLOADERS_DIR))
        except ValueError:
            return str(file_path)

    @staticmethod
    def _cell(row: pd.Series, index: int) -> Any:
        """Возвращает ячейку строки или None, если колонки нет."""
        try:
            return row.iloc[index]
        except IndexError:
            return None

    @classmethod
    def _cell_str(cls, row: pd.Series, index: int) -> str:
        """Возвращает текстовое значение ячейки (пустую строку для None/NaN)."""
        value = cls._cell(row, index)
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    @classmethod
    def _cell_float(cls, row: pd.Series, index: int) -> float | None:
        """Возвращает число с плавающей точкой или None ('-', пусто)."""
        value = cls._cell(row, index)
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            text = value.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
            if text in ("-", "", "—"):
                return None
            try:
                return float(text)
            except ValueError:
                return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _cell_int(cls, row: pd.Series, index: int) -> int | None:
        """Возвращает целое число или None ('-', пусто)."""
        value = cls._cell(row, index)
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            text = value.strip().replace("\xa0", "").replace(" ", "")
            if text in ("-", "", "—"):
                return None
            try:
                return int(float(text))
            except ValueError:
                return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_date(text: str) -> date | None:
        """Извлекает дату из строки вида 'Дата торгов: 12.01.2023'."""
        match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
        if not match:
            return None
        try:
            return datetime.strptime(match.group(1), "%d.%m.%Y").date()
        except ValueError:
            return None


def _parse_pdf_in_process(file_path: str, exchange_id: int) -> list[TradeEntity]:
    """Разбирает PDF-бюллетень в отдельном процессе (воркер ProcessPoolExecutor).

    camelot/pypdfium2 не потокобезопасны, поэтому конкурентный разбор PDF
    выполняется в отдельных процессах, а не потоках (потоки с конкурентным
    camelot зависают или роняют процесс). Экземпляр экстрактора создаётся в обход
    __init__: разбор PDF использует только exchange_id, репозитории не требуются.

    Args:
        file_path: Путь к PDF-файлу бюллетеня.
        exchange_id: Идентификатор биржевого источника (SPIMEX).

    Returns:
        Список извлечённых сделок (TradeEntity).
    """
    extractor = object.__new__(SpimexExtract)
    extractor._exchange_id = exchange_id
    return extractor._extract_pdf(Path(file_path))
