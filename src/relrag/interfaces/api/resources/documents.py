"""Document API resources."""

import json
import re
from urllib.parse import unquote_to_bytes
from uuid import UUID

import falcon.asgi

from relrag.application.dto.document_dto import DocumentCreateInput, DocumentOutput
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.domain.exceptions import NotFound, PermissionDenied, ValidationError
from relrag.infrastructure.document_parsers import parse_file

# RFC 5987: filename*=charset''percent-encoded (two single quotes)
_FILENAME_STAR_RFC5987 = re.compile(r"([\w-]+)''(.+)")


def _decode_filename(raw: str | None) -> str:
    """Decode filename to UTF-8, fixing mojibake when UTF-8 bytes were read as Latin-1."""
    if not raw or not raw.strip():
        return ""
    raw = raw.strip()
    try:
        return raw.encode("latin-1").decode("utf-8")
    except UnicodeEncodeError:
        return raw
    except UnicodeDecodeError:
        try:
            return raw.encode("latin-1").decode("cp1251")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return raw
    return raw


def _parse_filename_star_from_header(raw_header_value: bytes) -> str | None:
    """Parse Content-Disposition raw value for filename*=charset''percent-encoded (RFC 5987)."""
    if not raw_header_value:
        return None
    try:
        # Header value may be: form-data; name="files"; filename*=UTF-8''%D0%94%D0%BE%D0%BA...
        decoded = raw_header_value.decode("utf-8", errors="replace")
    except Exception:
        return None
    # Find filename*= (parameter name can be filename*)
    idx = decoded.find("filename*=")
    if idx == -1:
        return None
    rest = decoded[idx + len("filename*=") :].strip()
    match = _FILENAME_STAR_RFC5987.match(rest)
    if not match:
        return None
    charset, encoded = match.groups()
    try:
        return unquote_to_bytes(encoded).decode(charset)
    except (ValueError, LookupError):
        return None


def _get_part_filename(part: object, fallback_index: int) -> str:
    """Get filename from multipart part: part.filename / filename* from raw header + _decode_filename, else file_N."""
    raw = ""
    try:
        raw = (getattr(part, "filename", None) or "").strip()
    except Exception:
        pass
    if not raw:
        headers = getattr(part, "_headers", None)
        if isinstance(headers, dict):
            cd = headers.get(b"content-disposition", b"")
            raw_star = _parse_filename_star_from_header(cd)
            if raw_star:
                raw = raw_star.strip()
    decoded = _decode_filename(raw) if raw else ""
    return decoded if decoded else f"file_{fallback_index}"


def _sse_event(event: str, data: dict) -> bytes:
    """Format one Server-Sent Event (event + data)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


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
        file_index = 0
        async for part in form:
            name = part.name or ""
            if name == "collection_id":
                data = await part.get_data()
                collection_id_str = data.decode("utf-8").strip()
            elif name in ("files", "files[]"):
                data = await part.get_data()
                if not data:
                    continue
                file_index += 1
                filename = _get_part_filename(part, file_index)
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


class DocumentsStreamResource:
    """POST /v1/documents/stream - create documents from multipart, stream progress via SSE."""

    def __init__(self, load_document: LoadDocumentUseCase) -> None:
        self._load_document = load_document

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Create documents from multipart; respond with text/event-stream progress then done."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        content_type = req.content_type or ""
        if "multipart/form-data" not in content_type:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "multipart/form-data required"}
            return

        try:
            form = await req.get_media()
        except Exception as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": f"Invalid multipart: {e}"}
            return

        collection_id_str: str | None = None
        files: list[tuple[bytes, str]] = []
        file_index = 0
        async for part in form:
            name = (part.name or "").strip()
            if name == "collection_id":
                data = await part.get_data()
                collection_id_str = data.decode("utf-8").strip()
            elif name in ("files", "files[]"):
                data = await part.get_data()
                if not data:
                    continue
                file_index += 1
                filename = _get_part_filename(part, file_index)
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

        resp.status = falcon.HTTP_200
        resp.content_type = "text/event-stream"
        resp.cache_control = ["no-store"]
        resp.stream = self._stream_upload_events(user.user_id, collection_id, files)

    async def _stream_upload_events(
        self, user_id: str, collection_id: UUID, files: list[tuple[bytes, str]]
    ):
        """Async generator yielding SSE events: progress (per file) then done."""
        total = len(files)
        created: list[dict] = []
        errors: list[dict] = []

        for index, (data, filename) in enumerate(files):
            yield _sse_event(
                "progress",
                {
                    "total": total,
                    "current": index + 1,
                    "filename": filename,
                    "status": "processing",
                },
            )
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
                yield _sse_event(
                    "progress",
                    {
                        "total": total,
                        "current": index + 1,
                        "filename": filename,
                        "status": "ok",
                    },
                )
            except PermissionDenied:
                yield _sse_event(
                    "error",
                    {"message": "Permission denied", "filename": filename},
                )
                return
            except ValueError as e:
                errors.append({"filename": filename, "error": str(e)})
                yield _sse_event(
                    "progress",
                    {
                        "total": total,
                        "current": index + 1,
                        "filename": filename,
                        "status": "error",
                        "error": str(e),
                    },
                )
            except ValidationError as e:
                errors.append({"filename": filename, "error": str(e)})
                yield _sse_event(
                    "progress",
                    {
                        "total": total,
                        "current": index + 1,
                        "filename": filename,
                        "status": "error",
                        "error": str(e),
                    },
                )

        yield _sse_event("done", {"documents": created, "errors": errors})


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
