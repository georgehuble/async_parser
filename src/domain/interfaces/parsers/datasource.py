from abc import ABC

from src.domain.interfaces.parsers.downloader import Downloader
from src.domain.interfaces.parsers.parser import Parser


class DataSource(ABC):
    def __init__(self, parser: Parser, downloader: Downloader):
        self._parser = parser
        self._downloader = downloader

    async def fetch(self) -> None:
        links = await self._parser.parse()
        await self._downloader.download(links)
