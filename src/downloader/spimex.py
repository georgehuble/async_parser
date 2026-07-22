import asyncio
import logging
import sys
from pathlib import Path

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm.auto import tqdm

from ..database.database import get_session
from ..database.models import Spimex

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"

# Маппинг Content-Type -> расширение файла
CONTENT_TYPE_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.ms-excel": "xls",
}


def _ext_from_url(url: str) -> str | None:
    """Пытается определить расширение из URL как fallback."""
    lower_url = url.lower()
    if ".pdf" in lower_url:
        return "pdf"
    if ".xls" in lower_url:
        return "xls"
    return None


def _get_filename(file_id: int, content_type: str, url: str) -> str:
    """Определяет имя файла: {id}.{ext}.

    Сначала пробует Content-Type из ответа, затем URL.
    Если не удалось — сохраняет без расширения.
    """
    ext = CONTENT_TYPE_MAP.get(content_type)

    if ext is None:
        logger.warning("Неизвестный Content-Type '%s' для id=%d, пробуем URL", content_type, file_id)
        ext = _ext_from_url(url)

    if ext is None:
        logger.warning("Не удалось определить расширение для id=%d, сохраняю без расширения", file_id)
        return str(file_id)

    return f"{file_id}.{ext}"


async def download_file(
    session: aiohttp.ClientSession,
    file_id: int,
    url: str,
    semaphore: asyncio.Semaphore,
    pbar: tqdm,
) -> bool:
    """Скачивает один файл по URL и сохраняет под именем {id}.{ext}.

    Returns:
        True, если файл успешно скачан, иначе False.
    """
    async with semaphore:
        await asyncio.sleep(1)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as response:
                if response.status == 429 or response.status >= 500:
                    pbar.set_postfix_str(f"Ошибка сервера {response.status}")
                    sys.exit(1)
                response.raise_for_status()

                content_type = response.content_type
                filename = _get_filename(file_id, content_type, url)
                ext: str | None = CONTENT_TYPE_MAP.get(content_type) or _ext_from_url(url)
                if ext in ("pdf",):
                    save_dir = FILES_DIR / "pdf"
                elif ext in ("xls",):
                    save_dir = FILES_DIR / "xls"
                else:
                    save_dir = FILES_DIR / "other"
                save_dir.mkdir(parents=True, exist_ok=True)
                file_path = save_dir / filename

                if file_path.exists():
                    pbar.update(1)
                    return True

                content = await response.read()
                file_path.write_bytes(content)
            pbar.update(1)
            return True
        except Exception:
            pbar.set_postfix_str(f"Ошибка id={file_id}")
            pbar.update(1)
            return False


async def update_file_path(db_session: AsyncSession, file_id: int, file_path: str) -> None:
    """Обновляет поле file_path в БД после успешного скачивания."""
    stmt = update(Spimex).where(Spimex.id == file_id).values(file_path=file_path)
    await db_session.execute(stmt)


async def get_links(db_session: AsyncSession) -> list[tuple[int, str]]:
    """Возвращает все пары (id, url) из таблицы results."""
    query = select(Spimex.id, Spimex.url)

    try:
        result = await db_session.execute(query)
        rows = result.all()
    except Exception:
        logger.exception("get_links: ошибка выполнения запроса")
        raise
    logger.info("Получено %d ссылок из БД", len(rows))
    return [(row.id, row.url) for row in rows]


def _get_downloaded_ids(files_dir: Path) -> set[int]:
    """Собирает ID уже скачанных файлов из папок pdf и xls."""
    ids: set[int] = set()
    for subdir in ("pdf", "xls"):
        dir_path = files_dir / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if f.is_file():
                try:
                    ids.add(int(f.stem))
                except ValueError:
                    continue
    return ids


async def main(max_concurrent: int = 10) -> None:
    """Главная функция: подключается к БД, получает ссылки и параллельно скачивает файлы.

    Args:
        max_concurrent: Максимальное количество одновременных загрузок.
    """
    async with get_session() as db_session:
        links = await get_links(db_session)

        if not links:
            logger.info("Нет ссылок для скачивания")
            return

        existing_ids = _get_downloaded_ids(FILES_DIR)
        if existing_ids:
            start_id = max(existing_ids)
            before = len(links)
            links = [(fid, url) for fid, url in links if fid > start_id]
            if before - len(links) > 0:
                logger.info(
                    "Пропущено %d уже скачанных файлов, продолжаем с id > %d",
                    before - len(links),
                    start_id,
                )
        else:
            logger.info("Скачанных файлов не найдено, начинаем с начала")

        if not links:
            logger.info("Все файлы уже скачаны")
            return

        semaphore = asyncio.Semaphore(max_concurrent)

        async with aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            }
        ) as http_session:
            with tqdm(total=len(links), unit=" files", desc="Скачивание") as pbar:
                tasks = [
                    download_file(http_session, file_id, url, semaphore, pbar)
                    for file_id, url in links
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

        # Обрабатываем результаты и обновляем БД
        success_count = 0
        fail_count = 0

        for (file_id, url), result in zip(links, results):
            if isinstance(result, Exception):
                logger.error("Исключение при скачивании id=%d: %s", file_id, result)
                fail_count += 1
                continue
            if result is True:
                success_count += 1
            else:
                fail_count += 1

        await db_session.commit()

        logger.info(
            "Скачивание завершено: успешно %d, ошибок %d из %d",
            success_count,
            fail_count,
            len(links),
        )


if __name__ == "__main__":
    asyncio.run(main())
