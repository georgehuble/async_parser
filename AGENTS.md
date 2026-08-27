# stack
- Use poetry only, without .venv

# Language

- Write all code comments (new or modified code) in Russian.
- Write all text responses (explanations, summaries, error messages) in Russian.
- Keep variable, function, and class names in English (standard convention).
- Do not translate existing code, third-party docstrings, or file contents when quoting them.

# Rules

- After modifying Python code, run the following commands in order:
  1. `poetry run ruff check --fix .`
  2. `poetry run mypy .`
  3. `poetry run pytest`
- Run all commands from the project root (where pyproject.toml is located).
- **Comply with code W292 according to PEP 8 standard**
- If a check fails, investigate and fix the issue before considering the task complete — do not ignore failures.
- Only run `mypy` / `pytest` steps if these tools are configured in the project (check pyproject.toml).
- **Separate imports within functions and classes are not allowed.**
- Alembic files is not to change
