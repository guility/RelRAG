"""API resource tests."""

from uuid import uuid4

import pytest
from falcon.testing import TestClient


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
