import asyncio
import logging
from datetime import date
from pathlib import Path

import aiohttp
from tqdm.auto import tqdm

from src.domain.interfaces.parsers import Downloader
from src.domain.interfaces.repositories import DownloadRepositoryAbstract
from src.infra.database import get_session
from src.infra.database.repositories import TradeRepository

logger = logging.getLogger(__name__)

# Маппинг Content-Type -> расширение файла
CONTENT_TYPE_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.ms-excel": "xls",
}


class SpimexDownloader(Downloader):
    """Загрузчик файлов с сайта Spimex."""

    BASE_DIR = Path(__file__).resolve().parent
    FILES_DIR = BASE_DIR / "files"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }
    MAX_CONCURRENT = 8

    def __init__(self, repository: DownloadRepositoryAbstract) -> None:
        """Инициализирует загрузчик.

        Args:
            repository: Репозиторий для работы с БД при скачивании.
        """
        self._repository = repository
        self.FILES_DIR.mkdir(parents=True, exist_ok=True)

    async def download(self, links: list[tuple[date, str, int]]) -> None:
        """Загружает файлы по переданным ссылкам.

        Args:
            links: Список кортежей (дата, url, exchange_id).
        """
        if not links:
            logger.info("Нет ссылок для скачивания")
            return

        # Фильтруем: исключаем даты, которые уже скачаны
        existing_dates = self._get_downloaded_dates()
        before = len(links)
        links = [(dt, url, exchange_id) for dt, url, exchange_id in links if dt not in existing_dates]
        if existing_dates:
            logger.info(
                "Пропущено %d уже скачанных дат, осталось %d для скачивания",
                before - len(links),
                len(links),
            )
        else:
            logger.info("Скачанных файлов не найдено. Загружаются все файлы из БД")

        if not links:
            logger.info("Все файлы уже скачаны")
            return

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

        async with aiohttp.ClientSession(headers=self.HEADERS) as http_session:
            with tqdm(total=len(links), unit=" files", desc="Скачивание") as pbar:
                tasks = [
                    self._download_file(http_session, dt, url, semaphore, pbar)
                    for dt, url, _exchange_id in links
                ]
                results: list[str | BaseException | None] = await asyncio.gather(*tasks, return_exceptions=True)

        # Обрабатываем результаты и обновляем БД последовательно
        success_count = 0
        fail_count = 0

        for (dt, url, exchange_id), result in zip(links, results):
            if not isinstance(result, (str, type(None))):
                logger.error("Исключение при скачивании даты=%s: %s", dt, result)
                fail_count += 1
                continue
            if result is not None:
                # result — это относительный путь к файлу; обновляем по бизнес-ключу (exchange_id, url)
                await self._repository.update_file_path_by_url(url, exchange_id, result)
                success_count += 1
            else:
                fail_count += 1

        await self._repository.commit()

        logger.info(
            "Скачивание завершено: успешно %d, ошибок %d из %d",
            success_count,
            fail_count,
            len(links),
        )

    @staticmethod
    def _ext_from_url(url: str) -> str | None:
        """Пытается определить расширение из URL как fallback."""
        lower_url = url.lower()
        if ".pdf" in lower_url:
            return "pdf"
        if ".xls" in lower_url:
            return "xls"
        return None

    @staticmethod
    def _get_filename(dt: date, content_type: str, url: str) -> str:
        """Определяет имя файла: {date}.{ext}.

        Сначала пробует Content-Type из ответа, затем URL.
        Если не удалось — сохраняет без расширения.
        """
        ext = CONTENT_TYPE_MAP.get(content_type)

        if ext is None:
            logger.warning("Неизвестный Content-Type '%s' для даты=%s, пробуем URL", content_type, dt)
            ext = SpimexDownloader._ext_from_url(url)

        if ext is None:
            logger.warning("Не удалось определить расширение для даты=%s, сохраняю без расширения", dt)
            return dt.isoformat()

        return f"{dt.isoformat()}.{ext}"

    async def _download_file(
        self,
        session: aiohttp.ClientSession,
        dt: date,
        url: str,
        semaphore: asyncio.Semaphore,
        pbar: tqdm,
    ) -> str | None:
        """Скачивает один файл по URL и сохраняет под именем {date}.{ext}.

        Returns:
            Относительный путь к файлу, если успешно скачан, иначе None.
        """
        async with semaphore:
            await asyncio.sleep(1)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status == 429 or response.status >= 500:
                        pbar.set_postfix_str(f"Ошибка сервера dt={dt}, status={response.status}")
                        logger.warning("Ошибка сервера %d для даты=%s, URL=%s", response.status, dt, url)
                        return None
                    response.raise_for_status()

                    content_type = response.content_type
                    filename = self._get_filename(dt, content_type, url)
                    ext: str | None = CONTENT_TYPE_MAP.get(content_type) or self._ext_from_url(url)
                    if ext in ("pdf",):
                        save_dir = self.FILES_DIR / "pdf"
                    elif ext in ("xls",):
                        save_dir = self.FILES_DIR / "xls"
                    else:
                        save_dir = self.FILES_DIR / "other"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    file_path = save_dir / filename

                    if file_path.exists():
                        pbar.update(1)
                        return str(file_path.relative_to(self.BASE_DIR))

                    content = await response.read()
                    file_path.write_bytes(content)

                pbar.update(1)
                return str(file_path.relative_to(self.BASE_DIR))
            except Exception as exc:
                pbar.set_postfix_str(f"Ошибка dt={dt}")
                logger.warning("Ошибка скачивания даты=%s, URL=%s: %s", dt, url, exc)
                pbar.update(1)
                return None

    def _get_downloaded_dates(self) -> set[date]:
        """Собирает даты уже скачанных файлов из папок pdf и xls."""
        dates: set[date] = set()
        for subdir in ("pdf", "xls"):
            dir_path = self.FILES_DIR / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.iterdir():
                if f.is_file():
                    try:
                        # Имя файла: YYYY-MM-DD.ext или YYYY-MM-DD
                        stem = f.stem
                        dt = date.fromisoformat(stem)
                        dates.add(dt)
                    except (ValueError, TypeError):
                        continue
        return dates


async def main(max_concurrent: int = 8) -> None:
    """Главная функция: подключается к БД, получает ссылки и скачивает файлы.

    Args:
        max_concurrent: Максимальное количество одновременных загрузок.
    """
    async with get_session() as db_session:
        repo: DownloadRepositoryAbstract = TradeRepository(db_session)
        links = await repo.get_links()

    downloader = SpimexDownloader(repository=repo)
    await downloader.download(links)


if __name__ == "__main__":
    asyncio.run(main())
