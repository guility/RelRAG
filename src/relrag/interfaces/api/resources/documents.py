"""Document API resources."""

from uuid import UUID

import falcon.asgi

from relrag.application.dto.document_dto import DocumentCreateInput, DocumentOutput
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.domain.exceptions import NotFound, PermissionDenied, ValidationError
from relrag.infrastructure.document_parsers import parse_file


class DocumentsResource:
    """POST /v1/documents - create document (JSON or multipart with files)."""

    def __init__(self, load_document: LoadDocumentUseCase) -> None:
        self._load_document = load_document

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Create document(s) in collection. JSON: one doc; multipart: one doc per file."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        content_type = req.content_type or ""
        if "multipart/form-data" in content_type:
            await self._handle_multipart(req, resp, user.user_id)
            return

        try:
            body = await req.get_media()
            collection_id = UUID(body["collection_id"])
            content = body["content"]
            properties = {k: (v["value"], v["type"]) for k, v in body.get("properties", {}).items()}
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        try:
            result = await self._load_document.execute(
                user.user_id,
                DocumentCreateInput(
                    collection_id=collection_id,
                    content=content,
                    properties=properties,
                ),
            )
            resp.media = _document_to_dict(result)
            resp.status = falcon.HTTP_201
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
        except ValidationError as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}

    async def _handle_multipart(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response, user_id: str
    ) -> None:
        """Handle multipart form: collection_id + multiple files."""
        try:
            form = await req.get_media()
        except Exception as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": f"Invalid multipart: {e}"}
            return
        collection_id_str: str | None = None
        files: list[tuple[bytes, str]] = []
        async for part in form:
            name = part.name or ""
            if name == "collection_id":
                data = await part.get_data()
                collection_id_str = data.decode("utf-8").strip()
            elif name in ("files", "files[]") and part.filename:
                data = await part.get_data()
                filename = part.secure_filename or part.filename or "file"
                files.append((bytes(data), filename))
        if not collection_id_str:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "collection_id required"}
            return
        if not files:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "At least one file required"}
            return
        try:
            collection_id = UUID(collection_id_str)
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid collection_id"}
            return
        created: list[dict] = []
        errors: list[dict] = []
        for data, filename in files:
            try:
                parsed = parse_file(data, filename=filename, content_type=None)
                props = {k: (v[0], v[1].value) for k, v in parsed.properties.items()}
                out = await self._load_document.execute(
                    user_id,
                    DocumentCreateInput(
                        collection_id=collection_id,
                        content=parsed.text or " ",
                        properties=props,
                    ),
                )
                created.append(_document_to_dict(out))
            except ValueError as e:
                errors.append({"filename": filename, "error": str(e)})
            except PermissionDenied:
                resp.status = falcon.HTTP_403
                resp.media = {"error": "Permission denied"}
                return
            except ValidationError as e:
                errors.append({"filename": filename, "error": str(e)})
        resp.media = {"documents": created, "errors": errors}
        resp.status = falcon.HTTP_201


class DocumentResource:
    """GET /v1/documents/{id} - get document (requires collection_id query param)."""

    def __init__(self, get_document: GetDocumentUseCase) -> None:
        self._get_document = get_document

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        document_id: str,
    ) -> None:
        """Get document by id."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        collection_id_str = req.get_param("collection_id")
        if not collection_id_str:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "collection_id query parameter required"}
            return

        try:
            doc_id = UUID(document_id)
            coll_id = UUID(collection_id_str)
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid UUID"}
            return

        try:
            result = await self._get_document.execute(user.user_id, doc_id, coll_id)
            resp.media = _document_to_dict(result)
            resp.status = falcon.HTTP_200
        except NotFound:
            resp.status = falcon.HTTP_404
            resp.media = {"error": "Document not found"}
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}


def _document_to_dict(d: DocumentOutput) -> dict:
    return {
        "id": str(d.id),
        "content": d.content,
        "source_hash": d.source_hash.hex(),
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
        "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
    }
