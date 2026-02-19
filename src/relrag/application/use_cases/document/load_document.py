"""Load document use case."""

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from relrag.application.dto.chunking_config import ChunkingConfig
from relrag.application.dto.document_dto import DocumentCreateInput, DocumentOutput
from relrag.application.ports import Chunker, EmbeddingProvider, PermissionChecker
from relrag.domain.entities import Chunk, Document, Pack, Property
from relrag.domain.exceptions import PermissionDenied
from relrag.domain.value_objects import PermissionAction, PropertyType


class LoadDocumentUseCase:
    """Load document into collection: deduplication, chunking, embedding, save."""

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

    async def execute(self, user_id: str, input_data: DocumentCreateInput) -> DocumentOutput:
        """Load document into collection."""
        has_write = await self._permission_checker.check(
            user_id, input_data.collection_id, PermissionAction.WRITE
        )
        if not has_write:
            raise PermissionDenied("User does not have write access to collection")

        source_hash = input_data.source_hash or hashlib.md5(input_data.content.encode()).digest()

        async with self._uow_factory() as uow:
            existing = await uow.documents.get_by_source_hash(source_hash)
            if existing and existing.deleted_at is None:
                packs, _ = await uow.packs.list(
                    document_id=existing.id,
                    limit=1,
                )
                if packs:
                    await uow.packs.add_to_collection(
                        packs[0].id, input_data.collection_id
                    )
                return DocumentOutput(
                    id=existing.id,
                    content=existing.content,
                    source_hash=existing.source_hash,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    deleted_at=existing.deleted_at,
                )

            config = await uow.configurations.get_by_collection_id(input_data.collection_id)
            if not config:
                raise ValueError("Collection has no configuration")

            chunking_config = ChunkingConfig(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                strategy=config.chunking_strategy,
            )
            chunks_text = self._chunker.chunk(input_data.content, chunking_config)
            embeddings = await self._embedding_provider.embed(chunks_text)

            now = datetime.now(UTC)
            doc_id = uuid4()
            document = Document(
                id=doc_id,
                content=input_data.content,
                source_hash=source_hash,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            pack = Pack(
                id=uuid4(),
                document_id=doc_id,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )

            await uow.documents.create(document)
            await uow.packs.create(pack)

            chunk_entities = [
                Chunk(
                    id=uuid4(),
                    pack_id=pack.id,
                    content=text,
                    embedding=emb,
                    position=i,
                )
                for i, (text, emb) in enumerate(zip(chunks_text, embeddings, strict=True))
            ]
            await uow.chunks.create_batch(chunk_entities)

            properties = [
                Property(
                    document_id=doc_id,
                    key=k,
                    value=v[0],
                    property_type=PropertyType(v[1]),
                )
                for k, v in input_data.properties.items()
            ]
            if properties:
                await uow.properties.create_batch(properties)

            await uow.packs.add_to_collection(pack.id, input_data.collection_id)

        return DocumentOutput(
            id=document.id,
            content=document.content,
            source_hash=document.source_hash,
            created_at=document.created_at,
            updated_at=document.updated_at,
            deleted_at=document.deleted_at,
        )
