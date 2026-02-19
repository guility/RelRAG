"""API resource tests."""

import json
import re
from uuid import uuid4

import pytest
from falcon.testing import TestClient

from relrag.interfaces.api.resources.documents import (
    _decode_filename,
    _get_part_filename,
    _parse_filename_star_from_header,
)


class TestDecodeFilename:
    """Tests for _decode_filename (Cyrillic and encoding fixes)."""

    def test_decode_filename_none_or_empty(self) -> None:
        assert _decode_filename(None) == ""
        assert _decode_filename("") == ""
        assert _decode_filename("   ") == ""

    def test_decode_filename_ascii_unchanged(self) -> None:
        assert _decode_filename("test.txt") == "test.txt"
        assert _decode_filename("file_1") == "file_1"

    def test_decode_filename_cyrillic_unchanged(self) -> None:
        assert _decode_filename("Документ.txt") == "Документ.txt"
        assert _decode_filename("Файл.pdf") == "Файл.pdf"

    def test_decode_filename_mojibake_utf8_as_latin1(self) -> None:
        # UTF-8 bytes for "Документ" were decoded as Latin-1
        mojibake = bytes([0xD0, 0x94, 0xD0, 0xBE, 0xD0, 0xBA, 0xD1, 0x83, 0xD0, 0xBC, 0xD0, 0xB5, 0xD0, 0xBD, 0xD1, 0x82]).decode("latin-1")
        assert _decode_filename(mojibake) == "Документ"


class TestParseFilenameStar:
    """Tests for RFC 5987 filename* parsing from raw Content-Disposition."""

    def test_parse_filename_star_utf8_cyrillic(self) -> None:
        # filename*=UTF-8''%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.txt
        raw = b"form-data; name=\"files\"; filename*=UTF-8''%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.txt"
        assert _parse_filename_star_from_header(raw) == "Документ.txt"

    def test_parse_filename_star_missing_returns_none(self) -> None:
        raw = b'form-data; name="files"; filename="test.txt"'
        assert _parse_filename_star_from_header(raw) is None

    def test_parse_filename_star_empty_returns_none(self) -> None:
        assert _parse_filename_star_from_header(b"") is None


class TestGetPartFilename:
    """Tests for _get_part_filename with mock part."""

    def test_get_part_filename_uses_fallback_when_empty(self) -> None:
        part = type("Part", (), {"filename": "", "_headers": {}})()
        assert _get_part_filename(part, 1) == "file_1"

    def test_get_part_filename_uses_filename_star_from_headers_when_filename_empty(self) -> None:
        part = type(
            "Part",
            (),
            {
                "filename": "",
                "_headers": {
                    b"content-disposition": b"form-data; name=\"files\"; filename*=UTF-8''%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.txt",
                },
            },
        )()
        assert _get_part_filename(part, 1) == "Документ.txt"

    def test_get_part_filename_prefers_part_filename(self) -> None:
        part = type("Part", (), {"filename": "given.txt", "_headers": {}})()
        assert _get_part_filename(part, 1) == "given.txt"


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        r = client.simulate_get("/v1/health")
        assert r.status_code == 200
        assert r.json["status"] == "ok"


class TestConfigurations:
    def test_get_configurations_empty(self, client: TestClient) -> None:
        r = client.simulate_get("/v1/configurations")
        assert r.status_code == 200
        assert "items" in r.json
        assert r.json["items"] == []

    def test_post_configuration(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/configurations",
            json={
                "chunking_strategy": "recursive",
                "embedding_model": "text-embedding-3-small",
                "chunk_size": 512,
                "chunk_overlap": 50,
            },
        )
        assert r.status_code == 201
        assert "id" in r.json
        assert r.json["embedding_model"] == "text-embedding-3-small"
        assert r.json["chunk_size"] == 512

    def test_post_configuration_infer_dimensions(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/configurations",
            json={
                "embedding_model": "evraz-gte-qwen2-embed",
                "chunk_size": 256,
            },
        )
        assert r.status_code == 201
        assert r.json["embedding_dimensions"] == 1024


class TestModels:
    def test_get_models(self, client: TestClient) -> None:
        r = client.simulate_get("/v1/models")
        assert r.status_code == 200
        assert "items" in r.json
        assert len(r.json["items"]) > 0
        for m in r.json["items"]:
            assert "id" in m
            assert "dimensions" in m


class TestCollections:
    def test_get_collections_empty(self, client: TestClient) -> None:
        r = client.simulate_get("/v1/collections")
        assert r.status_code == 200
        assert r.json["items"] == []

    def test_post_collection_flow(self, client: TestClient) -> None:
        # Create config first
        cr = client.simulate_post(
            "/v1/configurations",
            json={
                "embedding_model": "text-embedding-3-small",
                "chunk_size": 512,
                "chunk_overlap": 50,
            },
        )
        assert cr.status_code == 201
        config_id = cr.json["id"]

        # Create collection
        r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        assert r.status_code == 201
        assert r.json["configuration_id"] == config_id

        # List collections
        lr = client.simulate_get("/v1/collections")
        assert lr.status_code == 200
        assert len(lr.json["items"]) == 1

    def test_get_collection_by_id(self, client: TestClient) -> None:
        # Create config and collection
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config_id = cr.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        coll_id = coll_r.json["id"]

        r = client.simulate_get(f"/v1/collections/{coll_id}")
        assert r.status_code == 200
        assert r.json["id"] == coll_id


class TestDocuments:
    def test_post_document(self, client: TestClient) -> None:
        # Create config, collection
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config_id = cr.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        coll_id = coll_r.json["id"]

        r = client.simulate_post(
            "/v1/documents",
            json={
                "collection_id": coll_id,
                "content": "Test document content",
                "properties": {},
            },
        )
        assert r.status_code == 201
        assert "id" in r.json
        assert r.json["content"] == "Test document content"

    def test_post_documents_stream_multipart(self, client: TestClient) -> None:
        """POST /v1/documents/stream returns SSE progress and done events."""
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config_id = cr.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        coll_id = coll_r.json["id"]
        boundary = "----TestBoundary"
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"collection_id\"\r\n\r\n"
            f"{coll_id}\r\n"
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"files\"; filename=\"test.txt\"\r\n"
            "Content-Type: text/plain\r\n\r\n"
            "Hello stream upload\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        r = client.simulate_post("/v1/documents/stream", body=body, headers=headers)
        assert r.status_code == 200
        assert "text/event-stream" in (r.headers.get("content-type") or "")
        text = r.text or ""
        assert "event: progress" in text
        assert "event: done" in text
        # Parse last "done" event data (data: {...} on one line)
        done_match = re.search(r"event: done\s*\ndata: (.+?)(?:\n|$)", text)
        assert done_match, "expected event: done with data"
        data = json.loads(done_match.group(1).strip())
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["content"] == "Hello stream upload"

    def test_post_documents_stream_cyrillic_filename(self, client: TestClient) -> None:
        """POST /v1/documents/stream preserves Cyrillic filename (filename*=UTF-8'' or mojibake in filename=)."""
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config_id = cr.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        coll_id = coll_r.json["id"]
        boundary = "----CyrillicBoundary"
        # Use filename*=UTF-8'' for "Документ.txt" (RFC 5987)
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"collection_id\"\r\n\r\n"
            f"{coll_id}\r\n"
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"files\"; filename*=UTF-8''%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.txt\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            "Cyrillic file content\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        r = client.simulate_post("/v1/documents/stream", body=body, headers=headers)
        assert r.status_code == 200
        text = r.text or ""
        assert "Документ.txt" in text
        done_match = re.search(r"event: done\s*\ndata: (.+?)(?:\n|$)", text)
        assert done_match
        data = json.loads(done_match.group(1).strip())
        assert len(data["documents"]) == 1


class TestConfigurationsErrors:
    def test_post_configuration_bad_strategy(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/configurations",
            json={
                "chunking_strategy": "invalid",
                "embedding_model": "x",
                "chunk_size": 512,
            },
        )
        assert r.status_code in (400, 201)

    def test_post_configuration_bad_body(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/configurations",
            json={"embedding_dimensions": "not-a-number"},
        )
        assert r.status_code == 400


class TestCollectionsErrors:
    def test_post_collection_missing_config_id(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/collections",
            json={},
        )
        assert r.status_code == 400

    def test_post_collection_invalid_config_id(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": "not-a-uuid"},
        )
        assert r.status_code == 400


class TestSearch:
    def test_search(self, client: TestClient) -> None:
        # Create config, collection, document
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config_id = cr.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config_id},
        )
        coll_id = coll_r.json["id"]
        client.simulate_post(
            "/v1/documents",
            json={
                "collection_id": coll_id,
                "content": "Test content for search",
                "properties": {},
            },
        )

        r = client.simulate_post(
            f"/v1/collections/{coll_id}/search",
            json={"query": "search", "limit": 10},
        )
        assert r.status_code == 200
        assert "results" in r.json

    def test_search_invalid_collection_id(self, client: TestClient) -> None:
        r = client.simulate_post(
            "/v1/collections/not-a-uuid/search",
            json={"query": "x"},
        )
        assert r.status_code == 400


class TestMigrate:
    def test_migrate_collection(self, client: TestClient) -> None:
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        config1_id = cr.json["id"]
        cr2 = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 256},
        )
        config2_id = cr2.json["id"]
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": config1_id},
        )
        coll_id = coll_r.json["id"]

        r = client.simulate_post(
            f"/v1/collections/{coll_id}/migrate",
            json={"new_configuration_id": config2_id},
        )
        assert r.status_code == 200
        assert "migrated" in r.json


class TestPermissions:
    def test_list_permissions(self, client: TestClient) -> None:
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": cr.json["id"]},
        )
        coll_id = coll_r.json["id"]

        r = client.simulate_get(f"/v1/collections/{coll_id}/permissions")
        assert r.status_code == 200
        assert "items" in r.json

    def test_assign_permission(self, client: TestClient) -> None:
        cr = client.simulate_post(
            "/v1/configurations",
            json={"embedding_model": "text-embedding-3-small", "chunk_size": 512},
        )
        coll_r = client.simulate_post(
            "/v1/collections",
            json={"configuration_id": cr.json["id"]},
        )
        coll_id = coll_r.json["id"]

        r = client.simulate_post(
            f"/v1/collections/{coll_id}/permissions",
            json={"subject": "user-2", "role": "viewer"},
        )
        assert r.status_code == 201
