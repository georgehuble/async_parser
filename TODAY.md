# Сегодня необходимо сделать: Рефакторинг проекта под SOLID

## Цель выполнения

Полное понимание паттернов проектирования SOLID через поэтапный рефакторинг проекта `async_parser`.

---

### 1. SRP — Single Responsibility Principle (Принцип единственной ответственности)

Разделить `src/downloader/spimex.py` — сейчас он отвечает и за скачивание, и за работу с БД.

- [X] **1.1** Создать `src/database/repository.py` — класс `SpimexRepository` с методами:
  - `get_links() -> list[tuple[int, str]]`
  - `update_file_path(file_id: int, file_path: str) -> None`
- [X] **1.2** Убрать из `src/downloader/spimex.py` прямые импорты `from ..database.models import Spimex` и `from ..database.database import get_session`
- [X] **1.3** Внедрить `SpimexRepository` в `downloader/spimex.py` через конструктор/параметр
- [X] **1.4** Проверить: downloader занимается только скачиванием, repository — только БД

---

### 2. OCP — Open/Closed Principle (Принцип открытости/закрытости)

Сделать систему расширяемой для новых источников данных без изменения существующего кода.

- [X] **2.1** Создать `src/core/interfaces.py` — определить абстрактные базовые классы:
  - `class Parser(ABC):` с методом `async def parse() -> list[str]`
  - `class Downloader(ABC):` с методом `async def download(links: list[tuple[int, str]]) -> None`
  - `class DataSource(ABC):` объединяющий парсер + загрузчик
- [X] **2.2** Переименовать `src/parser/spimex.py` → `src/parser/spimex_parser.py`, реализовать `SpimexParser(Parser)`
- [X] **2.3** Переименовать `src/downloader/spimex.py` → `src/downloader/spimex_downloader.py`, реализовать `SpimexDownloader(Downloader)`
- [X] **2.4** Создать `SpimexDataSource(DataSource)`, который собирает парсер + загрузчик
- [X] **2.5** Проверить: чтобы добавить MOEX, нужно только создать `MoexDataSource`, не трогая существующий код

---

### 3. LSP — Liskov Substitution Principle (Принцип подстановки Лисков)

Убедиться, что наследники корректно заменяют базовые классы.

- [ ] **3.1** Для каждой абстракции из п.2.1 написать простой тест-заглушку:
  - `MockParser(Parser)` — возвращает тестовые URL
  - `MockDownloader(Downloader)` — пишет в `/tmp/test_downloads`
- [ ] **3.2** Заменить `SpimexParser` на `MockParser` в `upload.py` — код не должен сломаться
- [ ] **3.3** Заменить `SpimexDownloader` на `MockDownloader` — код не должен сломаться

---

### 4. ISP — Interface Segregation Principle (Принцип разделения интерфейсов)

Проверить, что интерфейсы не содержат лишних методов.

- [X] **4.1** Пересмотреть `Parser` — только `parse()` и ничего лишнего
- [X] **4.2** Пересмотреть `Downloader` — только `download()`
- [X] **4.3** Если есть классы, которые используют только часть методов интерфейса — разбить интерфейс на более мелкие

---

### 5. DIP — Dependency Inversion Principle (Принцип инверсии зависимостей)

Сделать так, чтобы высокоуровневые модули не зависели от низкоуровневых.

- [X] **5.1** Переписать `src/parser/upload.py`:
  - Убрать `from parser.spimex import main`
  - Принимать `Parser` через конструктор/параметр
- [X] **5.2** Создать `src/orchestrator.py` — сервисный слой, который:
  - Принимает `DataSource` (абстракция)
  - Вызывает последовательно: `parse()` → сохраняет → `download()`
- [X] **5.3** В `__main__` (точка входа) собирать зависимости вручную (DI):
  - `parser = SpimexParser()`
  - `downloader = SpimexDownloader(repository)`
  - `source = SpimexDataSource(parser, downloader)`
  - `orchestrator = Orchestrator(source, repository)`
- [X] **5.4** Проверить: высокоуровневый код не импортирует низкоуровневые модули напрямую

---

### 6. Чистка кода

- [X] **6.1** Удалить дублирование `logging.basicConfig` — оставить один раз в `src/__init__.py`
- [ ] **6.2** Реализовать или удалить пустые пакеты: `converter/`, `extractor/`
- [X] **6.3** Обновить `pyproject.toml` при необходимости
- [X] **6.4** Запустить `poetry run ruff check --fix .`
- [X] **6.5** Запустить `poetry run mypy .` (если настроен)
- [X] **6.6** Запустить `poetry run pytest`

---

## Итоговый чек-лист понимания SOLID

- [ ] Понимаю, почему SRP нарушен и как исправить
- [ ] Понимаю, как OCP делает систему расширяемой
- [ ] Понимаю, как проверить LSP через моки
- [ ] Понимаю, зачем нужен ISP
- [ ] Понимаю, как DIP меняет направление зависимостей
- [ ] Могу объяснить каждый принцип на примере async_parser
