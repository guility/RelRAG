# Руководство по внесению вклада в RelRAG

## Документация проекта

| Документ | Описание |
|----------|----------|
| План разработки (Cursor) | Архитектура, технологический стек, этапы |
| [docs/TASKS.md](docs/TASKS.md) | Детализированные задачи с критериями приёмки |
| [docs/CONFLICTS.md](docs/CONFLICTS.md) | Реестр конфликтов при разработке |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | Конвенции и архитектурные соглашения |
| [docs/PLAN_REVIEW.md](docs/PLAN_REVIEW.md) | Анализ плана и рекомендации |

## Правило разрешения конфликтов

При **нестыковке** результата текущей задачи с результатами предыдущих этапов:

1. Зафиксировать конфликт в [docs/CONFLICTS.md](docs/CONFLICTS.md)
2. Вернуть задачу на доработку автору задачи, с которой возник конфликт
3. После доработки автор фиксирует решение в CONFLICTS.md

При **3-м возврате** одной и той же задачи — привлекается архитектор; решения фиксируются в [docs/CONVENTIONS.md](docs/CONVENTIONS.md) и ADR.

## Запуск проекта

```bash
# Установка зависимостей
uv sync

# Линтинг и форматирование
uv run ruff check src/
uv run ruff format src/

# Проверка типов
uv run mypy src/

# Pre-commit (установить хуки)
pre-commit install
pre-commit run --all-files

# Тесты
uv run pytest tests/ -v
```

## Структура кода

Проект следует **Clean Architecture**. Зависимости направлены внутрь: `interfaces` → `application` ← `infrastructure`; `application` → `domain`.

## Коммиты

Рекомендуется использовать [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:` и т.д.
