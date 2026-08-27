"""Тесты SpimexExtract: разбор XLS-бюллетеней и сохранение сделок через репозитории."""

import asyncio
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fpdf import FPDF

from src.application.parsers.spimex_extractor import SpimexExtract
from src.domain.entities import DeliveryBasisEntity, DeliveryTypeEntity, OilProductEntity, TradeEntity
from src.domain.interfaces.repositories import (
    DeliveryBasisRepositoryAbstract,
    DeliveryTypeRepositoryAbstract,
    OilProductRepositoryAbstract,
    TradeRepositoryAbstract,
)
from src.domain.value_objects import DeliveryBasisId, DeliveryTypeId, Money, Volume


class FakeTradeRepository(TradeRepositoryAbstract):
    """In-memory репозиторий сделок."""

    def __init__(self) -> None:
        self.added: list[dict] = []
        self.bulk_trades: list[TradeEntity] = []
        self.commits = 0
        self.bulletin_urls: dict[tuple[date, int], str] = {}
        self.existing_ids: set[str] = set()

    async def url_exists(self, url: str, exchange_id: int) -> bool:
        return False

    async def add_url(self, url: str, dt: date | None = None, exchange_id: int = 0) -> TradeEntity:
        return TradeEntity(url=url, date=dt, exchange_id=exchange_id)

    async def add_trades(self, trades: list[TradeEntity]) -> None:
        self.bulk_trades.extend(trades)

    async def add(
        self,
        url: str,
        dt: date | None = None,
        exchange_id: int = 0,
        exchange_trade_id: str | None = None,
        product_id: int | None = None,
        delivery_basis_id: str | None = None,
        delivery_type_id: str | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
        file_path: str | None = None,
    ) -> TradeEntity:
        self.added.append(
            {
                "url": url,
                "dt": dt,
                "exchange_id": exchange_id,
                "exchange_trade_id": exchange_trade_id,
                "product_id": product_id,
                "delivery_basis_id": delivery_basis_id,
                "delivery_type_id": delivery_type_id,
                "volume": volume,
                "total": total,
                "count": count,
                "file_path": file_path,
            }
        )
        return TradeEntity()

    async def get_max_date(self) -> date | None:
        return None

    async def get_links(self) -> list[tuple[date, str, int]]:
        return []

    async def get_bulletin_url_by_date(self, dt: date, exchange_id: int) -> str | None:
        return self.bulletin_urls.get((dt, exchange_id))

    async def get_existing_trade_ids(self, exchange_id: int, trade_ids: list[str]) -> set[str]:
        return {trade_id for trade_id in trade_ids if trade_id in self.existing_ids}

    async def update_file_path_by_url(self, url: str, exchange_id: int, file_path: str) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


class FakeOilProductRepository(OilProductRepositoryAbstract):
    """In-memory репозиторий нефтепродуктов."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, str | None, int]] = []

    async def get_or_create(
        self,
        exchange_product_id: str,
        name: str | None,
        oil_id: str | None,
        exchange_id: int,
    ) -> OilProductEntity:
        self.calls.append((exchange_product_id, name, oil_id, exchange_id))
        return OilProductEntity(product_id=10, exchange_id=exchange_id)

    async def get_by_id(self, product_id: int) -> OilProductEntity | None:
        return None


class FakeDeliveryBasisRepository(DeliveryBasisRepositoryAbstract):
    """In-memory репозиторий базисов поставки."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def get_or_create(self, delivery_basis_id: str, name: str | None) -> DeliveryBasisEntity:
        self.calls.append((delivery_basis_id, name))
        return DeliveryBasisEntity(
            delivery_basis_id=DeliveryBasisId(delivery_basis_id),
            delivery_basis_name=name,
        )

    async def get_by_id(self, basis_id: str) -> DeliveryBasisEntity | None:
        return None


class FakeDeliveryTypeRepository(DeliveryTypeRepositoryAbstract):
    """In-memory репозиторий типов поставки."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get_or_create(self, delivery_type_id: str) -> DeliveryTypeEntity:
        self.calls.append(delivery_type_id)
        return DeliveryTypeEntity(delivery_type_id=DeliveryTypeId(delivery_type_id))

    async def get_by_id(self, type_id: str) -> DeliveryTypeEntity | None:
        return None


def _make_bulletin(path: Path, rows: list[list[object]]) -> Path:
    """Записывает XLSX-файл с заданными строками (как их читает pandas)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False, header=False, engine="openpyxl")
    return path


def _bulletin_rows() -> list[list[object]]:
    """Строки бюллетеня: шапка, сделка и строка без сделок (только котировки)."""
    return [
        [None, "Форма СЭТ-БТ"],
        [None, "Бюллетень"],
        [None, "по итогам торгов"],
        [None, "Дата торгов: 12.01.2023"],
        [None, "Секция Биржи: «Нефтепродукты» АО «СПбМТСБ»"],
        [None, "Единица измерения: Метрическая тонна"],
        [
            None,
            "Код\nИнструмента",
            "Наименование\nИнструмента",
            "Базис\nпоставки",
            "Объем\nДоговоров\nв единицах\nизмерения",
            "Обьем\nДоговоров,\nруб.",
            "Руб.",
            "%",
            "Минимальная",
            "Средневзвешенная",
            "Максимальная",
            "Рыночная",
            "Лучшее\nпредложение",
            "Лучший\nспрос",
            "Количество\nДоговоров,\nшт.",
        ],
        [
            None,
            "A100ANK060F",
            "Бензин (АИ-100-К5), Ангарск-группа станций (ст. отправления)",
            "Ангарск-группа станций",
            60,
            3259740,
            -1600,
            -2.95,
            54329,
            54329,
            54329,
            54329,
            54329,
            54450,
            1,
        ],
        [
            None,
            "A100NEH005A",
            "Бензин (АИ-100-К5), Нефтегазохранилище х. Вязники (самовывоз автотранспортом)",
            "Нефтегазохранилище х. Вязники",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            73867,
            "-",
            "-",
        ],
        [None, "Итого:", None, None, 60, 3259740, None, None, None, None, None, None, None, None, 1],
    ]


def _make_extract() -> tuple[SpimexExtract, FakeTradeRepository]:
    """Создаёт экстрактор с in-memory репозиториями."""
    trade_repo = FakeTradeRepository()
    extract = SpimexExtract(
        exchange_id=1,
        trade_repository=trade_repo,
        oil_product_repository=FakeOilProductRepository(),
        delivery_basis_repository=FakeDeliveryBasisRepository(),
        delivery_type_repository=FakeDeliveryTypeRepository(),
    )
    return extract, trade_repo


# Кандидаты в системные шрифты с кириллицей для генерации тестовых PDF
_PDF_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


def _pdf_font_file() -> str:
    """Путь к шрифту с кириллицей (нужен fpdf2 для вставки русского текста)."""
    for candidate in _PDF_FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    pytest.skip("Шрифт с кириллицей не найден для генерации PDF")


def _make_pdf_bulletin(path: Path, rows: list[list[object]]) -> Path:
    """Генерирует PDF-бюллетень с таблицами (для camelot) через fpdf2.

    Строки 'Дата торгов: ...' и 'Единица измерения: ...' вставляются как текст
    вне таблиц; строка 'Единица измерения' начинает новую секцию с таблицей.
    Структура секции соответствует реальным бюллетеням SPIMEX.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    font_file = _pdf_font_file()

    # Разбиваем входные строки на секции: (единица измерения, строки таблицы)
    sections: list[tuple[str | None, list[list[object]]]] = []
    date_text: str | None = None
    unit: str | None = None
    data_rows: list[list[object]] = []

    for row in rows:
        marker = row[0] if len(row) > 0 else None
        if isinstance(marker, str) and marker.startswith("Дата торгов"):
            date_text = marker
        elif isinstance(marker, str) and marker.startswith("Единица измерения"):
            if unit is not None:
                sections.append((unit, data_rows))
            unit = marker
            data_rows = []
        else:
            data_rows.append(row)
    if unit is not None:
        sections.append((unit, data_rows))

    pdf = FPDF(format=(1000, 595))
    pdf.add_font("DejaVu", "", font_file)
    pdf.add_page()
    pdf.set_font("DejaVu", size=11)

    col_x = [30 + i * 58 for i in range(15)]
    row_h = 18
    y = 30

    if date_text is not None:
        pdf.set_xy(30, y)
        pdf.cell(500, 12, text=date_text)
        y += row_h

    for unit_line, section_rows in sections:
        pdf.set_xy(30, y)
        pdf.cell(500, 12, text=unit_line or "")
        y += row_h
        if not section_rows:
            continue

        # Сетка таблицы (линии нужны camelot для поиска таблиц)
        top = y
        bottom = top + row_h * len(section_rows)
        for i in range(len(section_rows) + 1):
            yy = top + i * row_h
            pdf.line(col_x[0], yy, col_x[-1], yy)
        for x in col_x:
            pdf.line(x, top, x, bottom)

        # Текст ячеек
        for i, row in enumerate(section_rows):
            for j, cell in enumerate(row):
                if cell is None:
                    continue
                pdf.set_xy(col_x[j] + 2, top + i * row_h + 2)
                pdf.set_font("DejaVu", size=7)
                pdf.cell(54, 12, text=str(cell))
                pdf.set_font("DejaVu", size=11)
        y = bottom

    pdf.output(str(path))
    return path



def test_parse_file_extracts_trade(tmp_path: Path) -> None:
    """Дата и данные сделки берутся из содержимого файла, а не из имени."""
    rows = _bulletin_rows()
    xlsx = _make_bulletin(tmp_path / "files" / "xls" / "2023-01-12.xlsx", rows)

    extract, _ = _make_extract()
    trades = extract.parse_file(xlsx)

    # Строка без сделок и 'Итого:' пропускаются — остаётся одна сделка
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exchange_id == 1
    assert trade.date == date(2023, 1, 12)
    assert trade.exchange_product_id == "A100ANK060F"
    assert trade.exchange_product_name == "Бензин (АИ-100-К5), Ангарск-группа станций (ст. отправления)"
    assert trade.oil_id == "A100"
    assert trade.delivery_basis_id == "ANK"
    assert trade.delivery_basis_name == "Ангарск-группа станций"
    assert trade.delivery_type_id == "F"
    assert trade.exchange_trade_id == "2023-01-12:A100ANK060F"
    assert trade.volume == Volume(value=60.0, unit="т")
    assert trade.total == Money(amount=3259740.0)
    assert trade.count == 1
    assert trade.file_path == str(xlsx)


def test_parse_file_multiple_sections(tmp_path: Path) -> None:
    """Несколько секций с повторяющимися шапками и разными единицами измерения."""
    rows: list[list[object]] = [
        [None, "Форма СЭТ-БТ"],
        [None, "Бюллетень"],
        [None, "по итогам торгов"],
        [None, "Дата торгов: 17.01.2023"],
        [None, "Единица измерения: Килограмм"],
        [None, "Код\nИнструмента", "Наименование\nИнструмента"],
        [
            None,
            "A592MNVK01O",
            "Бензин (АИ-92-К5) по ГОСТ, НБ Минеральные воды",
            "НБ Минеральные воды",
            50000,
            2020000,
            None,
            None,
            40,
            40,
            40,
            40,
            40,
            40,
            1,
        ],
        [None, "Итого:", None, None, 50000, 2020000, None, None, None, None, None, None, None, None, 1],
        [None, "Секция Биржи: «Нефтепродукты» АО «СПбМТСБ»"],
        [None, "Единица измерения: Метрическая тонна"],
        [None, "Код\nИнструмента", "Наименование\nИнструмента"],
        [
            None,
            "A100ANK060F",
            "Бензин (АИ-100-К5), Ангарск-группа станций (ст. отправления)",
            "Ангарск-группа станций",
            60,
            3259740,
            None,
            None,
            54329,
            54329,
            54329,
            54329,
            54329,
            54450,
            1,
        ],
        [None, "Итого по секции:", None, None, 60, 3259740, None, None, None, None, None, None, None, None, 1],
    ]
    xlsx = _make_bulletin(tmp_path / "files" / "2023-01-17.xlsx", rows)

    extract, _ = _make_extract()
    trades = extract.parse_file(xlsx)

    assert len(trades) == 2
    assert trades[0].exchange_product_id == "A592MNVK01O"
    assert trades[0].delivery_type_id == "O"
    assert trades[0].volume == Volume(value=50000.0, unit="кг")
    assert trades[1].exchange_product_id == "A100ANK060F"
    assert trades[1].volume == Volume(value=60.0, unit="т")


def test_parse_file_skips_unknown_format(tmp_path: Path) -> None:
    """Неизвестный формат пропускается без исключения."""
    extract, _ = _make_extract()

    txt = tmp_path / "notes.txt"
    txt.write_text("не файл бюллетеня", encoding="utf-8")

    assert extract.parse_file(txt) == []


def _pdf_bulletin_rows() -> list[list[object]]:
    """Строки PDF-бюллетеня: дата, единица, сделка и строка без сделок."""
    return [
        ["Дата торгов: 12.01.2023"],
        ["Единица измерения: Метрическая тонна"],
        [
            "A100ANK060F",
            "Бензин К5",
            "Ангарск",
            60,
            3259740,
            -1600,
            -2.95,
            54329,
            54329,
            54329,
            54329,
            54329,
            54450,
            1,
        ],
        ["A100NEH005A", "Бензин К5", "Вязники", "-", "-", "-", "-", "-", "-", "-", 73867, "-", "-", "-"],
        ["Итого:", None, None, 60, 3259740, None, None, None, None, None, None, None, None, 1],
    ]


def test_parse_file_extracts_pdf(tmp_path: Path) -> None:
    """PDF-бюллетень разбирается: сделка извлекается, а 'Итого:' и строки без сделок пропускаются."""
    pdf = _make_pdf_bulletin(tmp_path / "files" / "pdf" / "2023-01-12.pdf", _pdf_bulletin_rows())

    extract, _ = _make_extract()
    trades = extract.parse_file(pdf)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.exchange_id == 1
    assert trade.date == date(2023, 1, 12)
    assert trade.exchange_product_id == "A100ANK060F"
    assert trade.exchange_product_name == "Бензин К5"
    assert trade.oil_id == "A100"
    assert trade.delivery_basis_id == "ANK"
    assert trade.delivery_basis_name == "Ангарск"
    assert trade.delivery_type_id == "F"
    assert trade.exchange_trade_id == "2023-01-12:A100ANK060F"
    assert trade.volume == Volume(value=60.0, unit="т")
    assert trade.total == Money(amount=3259740.0)
    assert trade.count == 1


def test_parse_file_extracts_pdf_multiple_sections(tmp_path: Path) -> None:
    """PDF с несколькими секциями: каждой таблице сопоставляется своя единица измерения."""
    rows: list[list[object]] = [
        ["Дата торгов: 17.01.2023"],
        ["Единица измерения: Килограмм"],
        ["A592MNVK01O", "Бензин АИ-92-К5", "Минеральные воды", 50000, 2020000, None, None, 40, 40, 40, 40, 40, 40, 1],
        ["Итого:", None, None, 50000, 2020000, None, None, None, None, None, None, None, None, 1],
        ["Единица измерения: Декалитр"],
        ["PCMXSAUK53F", "Спирт этиловый", "Самара-группа", 5300, 1000000, None, None, 778, 778, 778, 778, 778, 778, 2],
        ["Итого:", None, None, 5300, 1000000, None, None, None, None, None, None, None, None, 2],
    ]
    pdf = _make_pdf_bulletin(tmp_path / "files" / "pdf" / "2023-01-17.pdf", rows)

    extract, _ = _make_extract()
    trades = extract.parse_file(pdf)

    assert len(trades) == 2
    assert trades[0].exchange_product_id == "A592MNVK01O"
    assert trades[0].volume == Volume(value=50000.0, unit="кг")
    assert trades[1].exchange_product_id == "PCMXSAUK53F"
    assert trades[1].volume == Volume(value=5300.0, unit="дал")


def test_extract_saves_trade_with_bulletin_url(tmp_path: Path) -> None:
    """extract() разбирает файлы, резолвит справочники и батчем сохраняет сделку в БД."""
    xlsx = _make_bulletin(tmp_path / "files" / "xls" / "2023-01-12.xlsx", _bulletin_rows())

    extract, trade_repo = _make_extract()
    trade_repo.bulletin_urls[(date(2023, 1, 12), 1)] = "https://spimex.example/oil_20230112120000.pdf"

    asyncio.run(extract.extract([(str(xlsx), xlsx.name)]))

    assert trade_repo.commits == 1
    assert len(trade_repo.bulk_trades) == 1
    trade = trade_repo.bulk_trades[0]
    assert trade.url == "https://spimex.example/oil_20230112120000.pdf"
    assert trade.date == date(2023, 1, 12)
    assert trade.exchange_id == 1
    assert trade.exchange_trade_id == "2023-01-12:A100ANK060F"
    assert trade.product_id == 10
    assert trade.delivery_basis_id == "ANK"
    assert trade.delivery_type_id == "F"
    assert trade.volume == Volume(value=60.0)
    assert trade.total == Money(amount=3259740.0)
    assert trade.count == 1
    assert trade.file_path == str(xlsx)


def test_extract_skips_existing_trades(tmp_path: Path) -> None:
    """Сделки, уже существующие в БД, не дублируются."""
    xlsx = _make_bulletin(tmp_path / "files" / "xls" / "2023-01-12.xlsx", _bulletin_rows())

    extract, trade_repo = _make_extract()
    trade_repo.existing_ids = {"2023-01-12:A100ANK060F"}

    asyncio.run(extract.extract([(str(xlsx), xlsx.name)]))

    assert trade_repo.commits == 1
    assert trade_repo.bulk_trades == []


def test_extract_skips_bad_file_and_commits(tmp_path: Path) -> None:
    """Сбойный файл не останавливает обработку остальных и commit всё равно выполняется."""
    bad = tmp_path / "corrupted.xlsx"
    bad.write_bytes(b"not an excel file")

    extract, trade_repo = _make_extract()
    asyncio.run(extract.extract([(str(bad), bad.name)]))

    assert trade_repo.commits == 1
    assert trade_repo.bulk_trades == []


def test_extract_processes_multiple_files_concurrently(tmp_path: Path) -> None:
    """Несколько файлов разбираются воркерами и сохраняются одним коммитом."""
    first = _make_bulletin(tmp_path / "files" / "xls" / "2023-01-12.xlsx", _bulletin_rows())

    rows = _bulletin_rows()
    rows[3] = [None, "Дата торгов: 13.01.2023"]
    second = _make_bulletin(tmp_path / "files" / "xls" / "2023-01-13.xlsx", rows)

    extract, trade_repo = _make_extract()
    asyncio.run(extract.extract([(str(first), first.name), (str(second), second.name)]))

    assert trade_repo.commits == 1
    assert len(trade_repo.bulk_trades) == 2
    trade_ids = {trade.exchange_trade_id for trade in trade_repo.bulk_trades}
    assert trade_ids == {"2023-01-12:A100ANK060F", "2023-01-13:A100ANK060F"}

