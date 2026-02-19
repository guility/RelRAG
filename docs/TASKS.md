# Детализированные задачи RelRAG

Каждая задача содержит: описание, критерии приёмки (Definition of Done), способ проверки.

---

## Правило разрешения конфликтов

**Если в процессе разработки возникает нестыковка** результата текущей задачи с результатами предыдущих этапов:

1. **Зафиксировать конфликт** в [docs/CONFLICTS.md](CONFLICTS.md) (дата, обнаруживший, задача с конфликтом, автор задачи, описание)
2. **Вернуть задачу на доработку** автору задачи, с которой возник конфликт
3. **После доработки** автор фиксирует в CONFLICTS.md, как конфликт был решён

**При 3-м возврате** одной и той же задачи:
- Привлекается **архитектор** для анализа причин
- Вносятся исправления в задачи/контракты
- Решения фиксируются в [docs/CONVENTIONS.md](CONVENTIONS.md) и в ADR (`docs/adr/`)

---

## Фаза 1: Инициализация проекта

### T1.1 — pyproject.toml и uv

**Описание**: Создать `pyproject.toml` с зависимостями, `requires-python=">=3.14"`, настройками uv.

**Definition of Done**:
- [ ] Файл `pyproject.toml` существует
- [ ] `[project]` с name, version, requires-python=">=3.14", dependencies
- [ ] `[tool.uv]` настроен
- [ ] `uv sync` успешно создаёт `uv.lock` и устанавливает зависимости

**Проверка**:
```bash
uv sync
uv run python -c "import relrag; print('OK')"
```

---

### T1.2 — ruff и mypy

**Описание**: Настроить ruff (линтинг, форматирование) и mypy (проверка типов) в `pyproject.toml`.

**Definition of Done**:
- [ ] `[tool.ruff]` с target-version, line-length, правилами
- [ ] `[tool.mypy]` с strict=true, python_version="3.14"
- [ ] `uv run ruff check .` и `uv run ruff format .` выполняются без ошибок
- [ ] `uv run mypy src/` выполняется (на пустом коде — без ошибок)

**Проверка**:
```bash
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```

---

### T1.3 — pre-commit

**Описание**: Добавить `.pre-commit-config.yaml` с хуками ruff и mypy.

**Definition of Done**:
- [ ] Файл `.pre-commit-config.yaml` существует
- [ ] Хуки: ruff, ruff-format, mypy
- [ ] `pre-commit run --all-files` проходит

**Проверка**:
```bash
pre-commit install
pre-commit run --all-files
```

---

### T1.4 — Структура папок Clean Architecture

**Описание**: Создать структуру каталогов domain, application, infrastructure, interfaces согласно плану.

**Definition of Done**:
- [ ] Папки `src/relrag/domain/entities`, `domain/value_objects`, `application/ports/repositories`, `application/use_cases`, `infrastructure/persistence/postgres`, `interfaces/api/resources` существуют
- [ ] `__init__.py` во всех пакетах
- [ ] `py.typed` в `src/relrag/` для mypy

**Проверка**:
```bash
find src/relrag -type d | sort
# Сравнить с планом
```

---

### T1.5 — config.py (pydantic-settings)

**Описание**: Реализовать `config.py` с настройками из переменных окружения.

**Definition of Done**:
- [ ] Pydantic BaseSettings с полями: database_url, keycloak_url, embedding_api_url и т.д.
- [ ] Загрузка из env; валидация при старте

**Проверка**:
```python
from relrag.config import get_settings
s = get_settings()
assert s.database_url  # или проверка наличия
```

---

### T1.6 — docs/adr/

**Описание**: Создать папку `docs/adr/` и шаблон ADR.

**Definition of Done**:
- [ ] Папка `docs/adr/` существует
- [ ] Файл-шаблон `docs/adr/0000-template.md` с форматом ADR

**Проверка**: `ls docs/adr/`

---

## Фаза 2: Domain

### T2.1 — value_objects (PropertyType, ChunkingStrategy, PermissionAction, SourceHash)

**Описание**: Реализовать value objects в `domain/value_objects/`.

**Definition of Done**:
- [ ] `PropertyType`: enum string, int, float, bool, date
- [ ] `ChunkingStrategy`: enum с поддерживаемыми стратегиями
- [ ] `PermissionAction`: enum read, write, delete, admin, migrate
- [ ] `SourceHash`: value object для MD5 (bytes)
- [ ] Нет импортов из infrastructure, interfaces, внешних библиотек (кроме typing, enum)

**Проверка**:
```python
from relrag.domain.value_objects import PropertyType, PermissionAction
assert PropertyType.STRING.value == "string"
assert PermissionAction.READ in PermissionAction
```

---

### T2.2 — domain exceptions

**Описание**: Определить доменные исключения в `domain/exceptions.py`.

**Definition of Done**:
- [ ] `PermissionDenied`, `NotFound`, `DuplicateDocument` (или аналог), `ValidationError`
- [ ] Наследуются от базового `RelRAGError`

**Проверка**:
```python
from relrag.domain.exceptions import PermissionDenied
raise PermissionDenied("test")
```

---

### T2.3 — entities (Document, Pack, Chunk, Collection, Configuration, Property, Permission, Role)

**Описание**: Реализовать доменные сущности как dataclass или Pydantic-модели.

**Definition of Done**:
- [ ] Все сущности с полями согласно ER-диаграмме
- [ ] Иммутабельность где уместно; валидация в конструкторе
- [ ] Нет импортов из infrastructure, interfaces

**Проверка**:
```python
from relrag.domain.entities import Document
d = Document(id=..., source_hash=b"...")
assert d.source_hash
```

---

## Фаза 3: Application — Ports

### T3.1 — UnitOfWork port

**Описание**: Определить Protocol `UnitOfWork` в `application/ports/unit_of_work.py`.

**Definition of Done**:
- [ ] Protocol с методами: `__aenter__`, `__aexit__`, `commit`, `rollback`
- [ ] Атрибуты: document_repository, pack_repository, chunk_repository, collection_repository, configuration_repository, permission_repository, role_repository

**Проверка**: mypy проверяет использование; unit-тест с mock UnitOfWork.

---

### T3.2 — Repository ports

**Описание**: Определить Protocol для DocumentRepository, PackRepository, ChunkRepository, CollectionRepository, **ConfigurationRepository**, PermissionRepository, RoleRepository.

**Definition of Done**:
- [ ] Каждый port с async-методами: get_by_id, list, create, update, delete (hard/soft) — где применимо
- [ ] **ConfigurationRepository**: get_by_id, create, get_by_collection_id (опционально)
- [ ] Сигнатуры принимают/возвращают domain entities или DTO

**Проверка**: Создать in-memory реализацию одного репозитория; use case использует port.

---

### T3.6 — ConfigurationRepository port

**Описание**: Protocol для Configuration (chunking_strategy, embedding_model, chunk_size, chunk_overlap).

**Definition of Done**:
- [ ] Методы: get_by_id, create
- [ ] Create принимает ChunkingConfig-подобный DTO
- [ ] Используется в LoadDocumentUseCase (получение config коллекции), MigrateCollectionUseCase, CreateCollectionUseCase

**Проверка**: LoadDocumentUseCase получает chunk_size из ConfigurationRepository через Collection.

---

### T3.3 — EmbeddingProvider port

**Описание**: Protocol для получения эмбеддингов.

**Definition of Done**:
- [ ] Метод `embed(texts: list[str]) -> list[list[float]]`
- [ ] Асинхронный

**Проверка**: FakeEmbeddingProvider возвращает фиксированные векторы; use case вызывает port.

---

### T3.4 — Chunker port

**Описание**: Protocol для разбиения текста на чанки.

**Definition of Done**:
- [ ] Метод `chunk(text: str, config: ChunkingConfig) -> list[str]`
- [ ] ChunkingConfig — DTO с chunk_size, chunk_overlap, strategy

**Проверка**: FakeChunker возвращает ["chunk1", "chunk2"]; use case вызывает port.

---

### T3.5 — PermissionChecker port

**Описание**: Protocol для проверки прав.

**Definition of Done**:
- [ ] Метод `check(user_id: str, collection_id: UUID, action: PermissionAction) -> bool`
- [ ] Асинхронный

**Проверка**: FakePermissionChecker(allow_all=True).check(...) возвращает True.

---

## Фаза 4: Application — Use Cases

### T4.1 — LoadDocumentUseCase

**Описание**: Загрузка документа в коллекцию: дедупликация по hash, chunking, embedding, сохранение.

**Definition of Done**:
- [ ] Вход: collection_id, content, properties, optional source_hash
- [ ] Проверка PermissionChecker(write)
- [ ] Получение Configuration коллекции (ConfigurationRepository) для chunk_size, chunk_overlap, embedding_model
- [ ] Дедупликация по source_hash (если передан)
- [ ] Сохранение **document.content** (исходный текст) — необходим для миграции
- [ ] Chunker + EmbeddingProvider через ports
- [ ] Сохранение Document, Pack, Chunks, Properties в одной транзакции (UnitOfWork)
- [ ] Выход: Document DTO

**Проверка**: Unit-тест с моками: при дубликате hash — возврат существующего; при новом — создание; document.content сохранён.

---

### T4.2 — GetDocumentUseCase, GetPackUseCase, GetCollectionUseCase

**Описание**: Получение сущности по id.

**Definition of Done**:
- [ ] **GetDocument, GetPack**: обязательный параметр `collection_id` — проверка прав по этой коллекции (Pack может быть в нескольких коллекциях)
- [ ] Проверка PermissionChecker(read) для коллекции
- [ ] При отсутствии — NotFound
- [ ] Учёт include_deleted

**Проверка**: Unit-тест: при отсутствии — NotFound; при наличии — возврат DTO; без collection_id — ValidationError.

---

### T4.3 — CreateCollectionUseCase

**Описание**: Создание коллекции с конфигурацией.

**Definition of Done**:
- [ ] Создание Collection + Configuration
- [ ] Автоназначение admin для создателя (subject) на эту коллекцию
- [ ] Транзакция

**Проверка**: Unit-тест: после создания в PermissionRepository есть запись (subject, collection_id, admin).

---

### T4.4 — UpdateDocumentUseCase, UpdatePackUseCase, UpdateCollectionUseCase (hard/soft)

**Описание**: Обновление сущностей с поддержкой hard (PUT) и soft (PATCH с history).

**Definition of Done**:
- [ ] Hard: in-place UPDATE
- [ ] Soft: запись в *_history, затем UPDATE
- [ ] Проверка PermissionChecker(write)

**Проверка**: Unit-тест: soft update — в history есть предыдущее состояние.

---

### T4.5 — DeleteDocumentUseCase, DeletePackUseCase, DeleteCollectionUseCase (hard/soft)

**Описание**: Удаление с каскадом.

**Definition of Done**:
- [ ] Soft: deleted_at = NOW(); каскад soft на дочерние
- [ ] Hard: физическое удаление; ON DELETE CASCADE в БД
- [ ] Проверка PermissionChecker(delete)

**Проверка**: Unit-тест: hard delete Document — Pack и Property удалены.

---

### T4.6 — AssignPermissionUseCase, RevokePermissionUseCase

**Описание**: Назначение и отзыв прав.

**Definition of Done**:
- [ ] Assign: создание Permission (collection_id, subject, role_id, optional actions_override)
- [ ] Revoke: удаление Permission
- [ ] Проверка: только admin может назначать/отзывать

**Проверка**: Unit-тест: без admin — PermissionDenied; с admin — успех.

---

### T4.7 — ListPermissionsUseCase, GetUserPermissionsUseCase

**Описание**: Список прав на коллекцию; права текущего пользователя.

**Definition of Done**:
- [ ] ListPermissions: для коллекции, требуется admin
- [ ] GetUserPermissions: для subject (user), возврат списка (collection_id, role, actions)

**Проверка**: Unit-тест: возврат списка Permission DTO.

---

### T4.8 — HybridSearchUseCase

**Описание**: Гибридный поиск (vector + full-text).

**Definition of Done**:
- [ ] Вход: collection_id, query, limit, optional filter по properties
- [ ] EmbeddingProvider для query
- [ ] Поиск по vector similarity + tsvector; объединение с весами
- [ ] Проверка PermissionChecker(read)

**Проверка**: Unit-тест с FakeEmbeddingProvider: возврат Chunk DTO с score.

---

### T4.9 — MigrateCollectionUseCase

**Описание**: Миграция коллекции на новую Configuration.

**Definition of Done**:
- [ ] Вход: collection_id, new_configuration_id
- [ ] Проверка PermissionChecker(migrate)
- [ ] Для каждого Document: взять **document.content** (исходный текст), переразбить (Chunker по новой Configuration), пересчитать embeddings (EmbeddingProvider), заменить Pack/Chunks
- [ ] Использует ConfigurationRepository для получения новой Configuration
- [ ] Одна транзакция или поэтапно

**Проверка**: Unit-тест: после миграции Chunks имеют новые embedding (проверка через mock).

---

### T4.10 — CreateConfigurationUseCase

**Описание**: Создание Configuration (для использования при создании коллекции или миграции).

**Definition of Done**:
- [ ] Вход: chunking_strategy, embedding_model, embedding_dimensions, chunk_size, chunk_overlap
- [ ] Выход: Configuration DTO
- [ ] Транзакция

**Проверка**: Unit-тест: созданная Configuration возвращается с id.

---

## Фаза 5: Infrastructure

### T5.1 — Postgres connection pool

**Описание**: Настроить async connection pool (psycopg).

**Definition of Done**:
- [ ] Connection pool с настройками из config
- [ ] pgvector зарегистрирован (register_vector_async)
- [ ] Контекстный менеджер для получения соединения

**Проверка**: Интеграционный тест: `async with pool.connection() as conn: await conn.execute("SELECT 1")`.

---

### T5.2 — Alembic migrations

**Описание**: Настроить Alembic, первая миграция со всеми таблицами.

**Definition of Done**:
- [ ] `alembic init` выполнен
- [ ] Миграция создаёт: document (с полем **content** TEXT), pack, chunk, property, collection, configuration, role, role_permission, permission, pack_collection
- [ ] pgvector extension, tsvector в chunk, индексы, ON DELETE CASCADE
- [ ] `alembic upgrade head` применяется без ошибок

**Проверка**:
```bash
alembic upgrade head
# Проверить таблицы в БД
alembic downgrade -1
alembic upgrade head
```

---

### T5.2a — Seed ролей RBAC

**Описание**: Заполнить role и role_permission начальными данными (viewer, editor, admin).

**Definition of Done**:
- [ ] Миграция Alembic или скрипт `uv run relrag seed-roles`
- [ ] Роли: viewer (read), editor (read, write), admin (read, write, delete, admin, migrate)
- [ ] Идемпотентность: повторный запуск не создаёт дубликаты

**Проверка**: После применения — в role 3 записи, в role_permission — соответствующие связи.

---

### T5.3 — Postgres UnitOfWork

**Описание**: Реализация UnitOfWork с транзакцией.

**Definition of Done**:
- [ ] `async with unit_of_work()` — начало транзакции
- [ ] При выходе без исключения — commit
- [ ] При исключении — rollback
- [ ] Репозитории получают connection из UnitOfWork

**Проверка**: Тест: при исключении в use case — rollback, данные не сохранены.

---

### T5.4 — Postgres repositories

**Описание**: Реализации DocumentRepository, PackRepository, ChunkRepository, CollectionRepository, ConfigurationRepository, PermissionRepository, RoleRepository.

**Definition of Done**:
- [ ] DocumentRepository, PackRepository, CollectionRepository, PermissionRepository, RoleRepository: полный CRUD с hard/soft
- [ ] **ChunkRepository**: create_batch, delete_by_pack_id, get_by_pack_id, search (для hybrid) — без отдельного Update/Delete по id
- [ ] **ConfigurationRepository**: get_by_id, create
- [ ] Каскад при hard delete
- [ ] Фильтр deleted_at по умолчанию

**Проверка**: Интеграционные тесты с Testcontainers (или реальным Postgres).

---

### T5.5 — OpenAI EmbeddingProvider

**Описание**: Реализация EmbeddingProvider через OpenAI-совместимый API.

**Definition of Done**:
- [ ] HTTP-клиент к embedding API
- [ ] Метод embed(texts) -> list[list[float]]
- [ ] Обработка ошибок, retry

**Проверка**: Интеграционный тест с mock HTTP server или реальным API (если доступен).

---

### T5.6 — RecursiveChunker

**Описание**: Реализация Chunker (RecursiveCharacterSplitter).

**Definition of Done**:
- [ ] Разбиение по separators ["\n\n", "\n", " ", ""]
- [ ] chunk_size, chunk_overlap из ChunkingConfig

**Проверка**: Unit-тест: длинный текст разбивается на чанки заданного размера.

---

### T5.7 — KeycloakProvider

**Описание**: Проверка JWT через Keycloak JWKS.

**Definition of Done**:
- [ ] Загрузка JWKS по URL
- [ ] Валидация токена, извлечение sub, roles
- [ ] Возврат OIDCUser или None при невалидном токене

**Проверка**: Unit-тест с mock JWKS: валидный токен — OIDCUser; невалидный — исключение.

---

### T5.8 — PermissionChecker (infrastructure)

**Описание**: Реализация PermissionChecker port.

**Definition of Done**:
- [ ] Запрос к Permission, Role, RolePermission
- [ ] Учёт actions_override
- [ ] Обход для relrag_admin (если в Keycloak roles)

**Проверка**: Unit-тест: user с role admin — check(write)=True; user без прав — False.

---

## Фаза 6: Interfaces (API)

### T6.1 — Falcon app и роутинг

**Описание**: Создать falcon.asgi.App, зарегистрировать routes под /v1/.

**Definition of Done**:
- [ ] App создаётся в app.py
- [ ] Routes: /v1/documents, /v1/packs, /v1/collections, /v1/collections/{id}/permissions, /v1/search, /v1/health, /v1/health/ready

**Проверка**: `curl http://localhost:8000/v1/health` возвращает 200.

---

### T6.2 — Auth middleware

**Описание**: Middleware проверки JWT, установка req.context.user.

**Definition of Done**:
- [ ] Извлечение Bearer token из заголовка
- [ ] KeycloakProvider.decode(token) -> OIDCUser
- [ ] req.context.user = user; при отсутствии/невалидном — 401

**Проверка**: Запрос без токена — 401; с валидным токеном — 200 (для защищённого эндпоинта).

---

### T6.3 — Request context middleware

**Описание**: Middleware для request_id, DB session.

**Definition of Done**:
- [ ] Генерация request_id (UUID)
- [ ] Передача UnitOfWork в контекст или dependency
- [ ] structlog: bind request_id, user_id

**Проверка**: В логах присутствует request_id.

---

### T6.4 — DocumentResource, PackResource, CollectionResource

**Описание**: Falcon Resources для CRUD документов, packs, коллекций.

**Definition of Done**:
- [ ] on_post, on_get, on_put, on_patch, on_delete
- [ ] **GetDocument, GetPack**: обязательный query-параметр `collection_id` — проверка прав
- [ ] Парсинг query params: include_deleted, hard, **cursor**, **limit** (пагинация)
- [ ] Вызов соответствующих use cases
- [ ] Сериализация в JSON (Pydantic)
- [ ] Ответ list-эндпоинтов: `{ "items": [...], "next_cursor": "..." }`

**Проверка**: E2E тест: POST document -> GET by id (с collection_id) -> 200, тело совпадает.

---

### T6.4a — ConfigurationResource

**Описание**: Falcon Resource для создания Configuration.

**Definition of Done**:
- [ ] POST /v1/configurations — создание Configuration
- [ ] Body: chunking_strategy, embedding_model, embedding_dimensions, chunk_size, chunk_overlap
- [ ] Вызов CreateConfigurationUseCase

**Проверка**: E2E: POST configuration -> 201, возврат с id.

---

### T6.5 — PermissionResource

**Описание**: CRUD для прав.

**Definition of Done**:
- [ ] POST /v1/collections/{id}/permissions — назначить
- [ ] GET /v1/collections/{id}/permissions — список
- [ ] GET /v1/users/me/permissions — права пользователя
- [ ] DELETE — отозвать

**Проверка**: E2E: POST permission -> GET list -> запись присутствует.

---

### T6.6 — SearchResource

**Описание**: Эндпоинт гибридного поиска.

**Definition of Done**:
- [ ] GET /v1/search?collection_id=...&q=...&limit=...
- [ ] Вызов HybridSearchUseCase
- [ ] Возврат списка chunks с score

**Проверка**: E2E: поиск по существующей коллекции — 200, список результатов.

---

### T6.6a — Cursor-based пагинация

**Описание**: Реализовать пагинацию для list-эндпоинтов.

**Definition of Done**:
- [ ] Query params: `?cursor=...&limit=...` (limit по умолчанию, напр. 20)
- [ ] Ответ: `{ "items": [...], "next_cursor": "..." }` (next_cursor отсутствует на последней странице)
- [ ] Cursor — непрозрачная строка (UUID последнего элемента или base64)

**Проверка**: E2E: GET list с limit=2 -> 2 items + next_cursor; запрос с next_cursor -> следующая страница.

---

### T6.7 — Health endpoints

**Описание**: /health и /health/ready.

**Definition of Done**:
- [ ] /health — всегда 200 (liveness)
- [ ] /health/ready — проверка БД (SELECT 1), опционально Keycloak; при ошибке — 503

**Проверка**: При работающей БД — 200; при недоступной БД — 503.

---

## Фаза 7: Composition Root

### T7.1 — main.py

**Описание**: Точка входа, сборка приложения, DI.

**Definition of Done**:
- [ ] Создание всех адаптеров (repositories включая ConfigurationRepository, EmbeddingProvider, Chunker, PermissionChecker)
- [ ] Инъекция в use cases
- [ ] Регистрация use cases в Resources (или через фабрику)
- [ ] Запуск uvicorn

**Проверка**: `uv run uvicorn relrag.main:app` — приложение стартует, /health отвечает.

---

## Фаза 8: Observability

### T8.1 — structlog

**Описание**: Настроить структурированное логирование.

**Definition of Done**:
- [ ] JSON в prod (env), pretty в dev
- [ ] Processors: timestamp, request_id, user_id
- [ ] Логирование входящих запросов, ошибок

**Проверка**: Запрос к API — в логах JSON с request_id.

---

### T8.2 — OpenTelemetry

**Описание**: Инструментация Falcon, psycopg.

**Definition of Done**:
- [ ] opentelemetry-instrumentation-falcon
- [ ] opentelemetry-instrumentation-psycopg
- [ ] Экспорт в OTLP или console для dev

**Проверка**: Запрос — span в tracer; при настроенном Jaeger — trace виден.

---

## Фаза 9: Docker и Kubernetes

### T9.1 — Dockerfile

**Описание**: Multi-stage Dockerfile.

**Definition of Done**:
- [ ] Stage 1: uv build
- [ ] Stage 2: python:3.14-slim, копирование артефактов
- [ ] CMD: uvicorn
- [ ] .dockerignore исключает .git, __pycache__, tests

**Проверка**: `docker build -t relrag . && docker run -p 8000:8000 relrag` — /health отвечает.

---

### T9.2 — docker-compose.yml

**Описание**: Compose с relrag-api и postgres.

**Definition of Done**:
- [ ] Сервисы: api, postgres
- [ ] postgres: образ с pgvector
- [ ] api depends_on postgres
- [ ] env_file, healthcheck

**Проверка**: `docker compose up -d && docker compose ps` — оба healthy.

---

### T9.3 — Kubernetes manifests

**Описание**: Deployment, Service, ConfigMap, Secret.

**Definition of Done**:
- [ ] deployment.yaml: replicas, probes, env from configmap/secret
- [ ] service.yaml: ClusterIP
- [ ] configmap.yaml: DATABASE_URL и т.д.
- [ ] secret.yaml: placeholder или External Secrets

**Проверка**: `kubectl apply -f k8s/` — pod в Running, /health через port-forward.

---

## Фаза 10: Тесты

### T10.1 — pytest и фикстуры

**Описание**: Настроить pytest, фикстуры для моков.

**Definition of Done**:
- [ ] pytest, pytest-asyncio в dev-dependencies
- [ ] conftest.py: фикстуры FakeUnitOfWork, FakeDocumentRepository и т.д.
- [ ] Фикстура in-memory БД (опционально)

**Проверка**: `uv run pytest tests/ -v` — тесты запускаются.

---

### T10.2 — Unit-тесты use cases

**Описание**: Тесты для всех use cases с моками портов.

**Definition of Done**:
- [ ] Минимум 1 тест на use case
- [ ] Покрытие успешного сценария и ошибок (PermissionDenied, NotFound)

**Проверка**: `uv run pytest tests/unit/ -v --cov=relrag.application`

---

### T10.3 — Интеграционные тесты (опционально Testcontainers)

**Описание**: Тесты с реальным Postgres.

**Definition of Done**:
- [ ] Testcontainers или фиксированный test DB
- [ ] Тесты репозиториев, UnitOfWork
- [ ] Тесты E2E через TestClient (Falcon)

**Проверка**: `uv run pytest tests/integration/ -v`

---

## Сводка: порядок выполнения

Задачи можно выполнять в указанном порядке; зависимости:
- T2.x зависят от T1.x
- T3.x зависят от T2.x
- T4.x зависят от T3.x
- T5.x зависят от T3.x, T2.x
- T6.x зависят от T4.x, T5.x
- T7.1 зависит от T5.x, T6.x
- T8.x, T9.x, T10.x — параллельно после T7.1
