import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Отключаем propagation для sqlalchemy.engine, чтобы избежать дублирования логов
# (echo=True в database.py уже добавляет свой хендлер к этому логгеру)
logging.getLogger("sqlalchemy.engine").propagate = False

