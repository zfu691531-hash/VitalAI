# -*- coding: utf-8 -*-
"""Milvus integration for rule RAG."""

from __future__ import annotations

from typing import Iterable

from utils.logger import logger

try:  # pragma: no cover
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except Exception:  # pragma: no cover
    Collection = None
    CollectionSchema = None
    DataType = None
    FieldSchema = None
    connections = None
    utility = None


class MilvusRuleStore:
    def __init__(
        self,
        uri: str | None = None,
        token: str | None = None,
        collection_name: str = "school_rule_chunks",
        dense_dim: int = 1024,
    ):
        self.uri = self._normalize_uri(uri)
        self.token = token
        self.collection_name = collection_name
        self.dense_dim = dense_dim

    @property
    def enabled(self) -> bool:
        return bool(Collection and connections and self.uri)

    def ensure_ready(self) -> bool:
        if not self.enabled:
            return False
        try:
            connections.connect(alias="default", uri=self.uri, token=self.token or None)
            if not utility.has_collection(self.collection_name):
                schema = CollectionSchema(
                    fields=[
                        FieldSchema(name="chunk_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
                        FieldSchema(name="rule_id", dtype=DataType.INT64),
                        FieldSchema(name="rule_version", dtype=DataType.INT64),
                        FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=4096),
                        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dense_dim),
                        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
                    ],
                    description="school rule chunks",
                    enable_dynamic_field=False,
                )
                collection = Collection(self.collection_name, schema=schema)
                collection.create_index("dense_vector", {"index_type": "AUTOINDEX", "metric_type": "IP"})
                collection.create_index("sparse_vector", {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"})
                collection.flush()
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("milvus init failed: %s", exc)
            return False

    def upsert_chunks(self, rows: Iterable[dict]) -> dict:
        rows = list(rows)
        if not rows:
            return {"enabled": self.enabled, "upserted": 0}
        if not self.ensure_ready():
            return {"enabled": False, "upserted": 0}
        try:  # pragma: no cover
            collection = Collection(self.collection_name)
            chunk_ids = [int(row["chunk_id"]) for row in rows]
            if chunk_ids:
                collection.delete(expr=f"chunk_id in {chunk_ids}")
            collection.insert(
                [
                    chunk_ids,
                    [int(row["rule_id"]) for row in rows],
                    [int(row["rule_version"]) for row in rows],
                    [row["chunk_text"] for row in rows],
                    [row["dense_vector"] for row in rows],
                    [row["sparse_vector"] for row in rows],
                ]
            )
            collection.flush()
            return {"enabled": True, "upserted": len(rows)}
        except Exception as exc:
            logger.warning("milvus upsert failed: %s", exc)
            return {"enabled": True, "upserted": 0, "error": str(exc)}

    def recreate_collection(self) -> dict:
        if not self.enabled:
            return {"enabled": False, "recreated": False}
        try:  # pragma: no cover
            connections.connect(alias="default", uri=self.uri, token=self.token or None)
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
            ready = self.ensure_ready()
            return {"enabled": True, "recreated": ready}
        except Exception as exc:
            logger.warning("milvus recreate collection failed: %s", exc)
            return {"enabled": True, "recreated": False, "error": str(exc)}

    def search(self, dense_vector: list[float], sparse_vector: dict[int, float], limit: int = 10) -> dict[int, dict]:
        if not self.ensure_ready():
            return {}
        try:  # pragma: no cover
            collection = Collection(self.collection_name)
            collection.load()
            if utility and hasattr(utility, "wait_for_loading_complete"):
                utility.wait_for_loading_complete(self.collection_name)
            results: dict[int, dict] = {}

            dense_hits = collection.search(
                data=[dense_vector],
                anns_field="dense_vector",
                param={"metric_type": "IP", "params": {}},
                limit=limit,
                output_fields=["chunk_id", "rule_id", "rule_version", "chunk_text"],
            )
            for hit in dense_hits[0]:
                chunk_id = int(hit.entity.get("chunk_id"))
                results.setdefault(chunk_id, {})["dense"] = float(hit.score)

            if sparse_vector:
                sparse_hits = collection.search(
                    data=[sparse_vector],
                    anns_field="sparse_vector",
                    param={"metric_type": "IP", "params": {}},
                    limit=limit,
                    output_fields=["chunk_id", "rule_id", "rule_version", "chunk_text"],
                )
                for hit in sparse_hits[0]:
                    chunk_id = int(hit.entity.get("chunk_id"))
                    results.setdefault(chunk_id, {})["sparse"] = float(hit.score)

            return results
        except Exception as exc:
            logger.warning("milvus search failed: %s", exc)
            return {}

    def delete_rule_chunks(self, rule_id: int) -> dict:
        if not self.ensure_ready():
            return {"enabled": False, "deleted": 0}
        try:  # pragma: no cover
            collection = Collection(self.collection_name)
            collection.load()
            if utility and hasattr(utility, "wait_for_loading_complete"):
                utility.wait_for_loading_complete(self.collection_name)
            collection.delete(expr=f"rule_id == {int(rule_id)}")
            collection.flush()
            return {"enabled": True, "deleted": 1}
        except Exception as exc:
            logger.warning("milvus delete failed: %s", exc)
            return {"enabled": True, "deleted": 0, "error": str(exc)}

    @staticmethod
    def _normalize_uri(uri: str | None) -> str:
        if not uri:
            return ""
        normalized = uri.strip()
        if not normalized:
            return ""
        if "://" not in normalized:
            normalized = f"http://{normalized}"
        return normalized
