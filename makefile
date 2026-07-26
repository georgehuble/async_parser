.PHONY: install run test lint format typecheck check clean shell add update lock

# Установить зависимости из poetry.lock
install:
	poetry install

# Установить + обновить lock-файл при изменении pyproject.toml
lock:
	poetry lock

# Добавить новый пакет (использование: make add pkg=requests)
add:
	poetry add $(pkg)

# Добавить dev-зависимость (использование: make add-dev pkg=ruff)
add-dev:
	poetry add --group dev $(pkg)

# Обновить все зависимости
update:
	poetry update

# Создать новую миграцию (использование: make migrate m="описание")
migrate:
	poetry run alembic revision --autogenerate -m "$(m)"

# Применить миграции
upgrade:
	poetry run alembic upgrade head

# Запустить приложение
run:
	poetry run python -m src.main


# Зайти в shell окружения poetry
shell:
	poetry shell

# Тесты
test:
	poetry run pytest tests/ -v

# Тесты с покрытием
coverage:
	poetry run pytest --cov=. --cov-report=term-missing tests/

# Линтер + автофикс (ruff умеет и то, и другое)
lint:
	poetry run ruff check . --fix

# Форматирование (ruff format заменяет black)
format:
	poetry run ruff format .

# Проверка типов
typecheck:
	poetry run mypy .

# Прогнать всё разом перед коммитом/пушем
check: format lint typecheck test

# Очистка кэшей
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

# Запуск контейнеров
docker:
	docker compose up -d
