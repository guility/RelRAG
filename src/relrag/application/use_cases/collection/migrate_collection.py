"""Migrate collection use case - re-chunk and re-embed with new configuration."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from relrag.application.dto.chunking_config import ChunkingConfig
from relrag.application.ports import Chunker, EmbeddingProvider, PermissionChecker
from relrag.domain.entities import Chunk
from relrag.domain.exceptions import NotFound, PermissionDenied
from relrag.domain.value_objects import PermissionAction


class MigrateCollectionUseCase:
    """Migrate collection to new configuration: re-chunk and re-embed all documents."""

    def __init__(
        self,
        unit_of_work_factory: type,
        permission_checker: PermissionChecker,
        chunker: Chunker,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker
        self._chunker = chunker
        self._embedding_provider = embedding_provider

    async def execute(self, user_id: str, collection_id: UUID, new_configuration_id: UUID) -> int:
        """Migrate collection. Returns number of documents migrated."""
        has_migrate = await self._permission_checker.check(
            user_id, collection_id, PermissionAction.MIGRATE
        )
        if not has_migrate:
            raise PermissionDenied("User does not have migrate access to collection")

        async with self._uow_factory() as uow:
            new_config = await uow.configurations.get_by_id(new_configuration_id)
            if not new_config:
                raise NotFound("Configuration", str(new_configuration_id))

            collection = await uow.collections.get_by_id(collection_id)
            if not collection or collection.deleted_at:
                raise NotFound("Collection", str(collection_id))

            packs, _ = await uow.packs.list(
                collection_id=collection_id,
                limit=10000,
            )
            migrated = 0
            now = datetime.now(UTC)

            for pack in packs:
                doc = await uow.documents.get_by_id(pack.document_id)
                if not doc or doc.deleted_at or not doc.content:
                    continue

                chunking_config = ChunkingConfig(
                    chunk_size=new_config.chunk_size,
                    chunk_overlap=new_config.chunk_overlap,
                    strategy=new_config.chunking_strategy,
                )
                chunks_text = self._chunker.chunk(doc.content, chunking_config)
                embeddings = await self._embedding_provider.embed(chunks_text)

                await uow.chunks.delete_by_pack_id(pack.id)
                new_chunks = [
                    Chunk(
                        id=uuid4(),
                        pack_id=pack.id,
                        content=text,
                        embedding=emb,
                        position=i,
                    )
                    for i, (text, emb) in enumerate(zip(chunks_text, embeddings, strict=True))
                ]
                await uow.chunks.create_batch(new_chunks)

                migrated += 1

            collection.configuration_id = new_configuration_id
            collection.updated_at = now
            await uow.collections.update(collection)

        return migrated
