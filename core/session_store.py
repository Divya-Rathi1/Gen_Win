# core/session_store.py
# ─────────────────────────────────────────────────────────────────────────────
# In-memory session storage for prototype.
# Stores: metadata, generated docs, chat history, version history, audit scores
# Everything lives in RAM — resets on server restart (fine for prototype)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional
from datetime import datetime


# ─── In-memory stores ────────────────────────────────────────────────────────

_metadata_store: dict[str, dict] = {}           # dataset_id → metadata
_docs_store: dict[str, dict] = {}               # dataset_id → {doc_type: content}
_chat_store: dict[str, list] = {}               # dataset_id → [{"role":..,"content":..}]
_audit_store: dict[str, dict] = {}              # dataset_id → audit_score dict
_version_store: dict[str, list] = {}            # dataset_id → [{version, timestamp, metadata, changes}]
_active_dataset: dict = {}                      # single active session


# ─── Metadata ─────────────────────────────────────────────────────────────

def save_metadata(dataset_id: str, metadata: dict):
    _metadata_store[dataset_id] = metadata
    _active_dataset["id"] = dataset_id
    _active_dataset["name"] = metadata.get("dataset_name", "Unknown")


def get_metadata(dataset_id: str) -> Optional[dict]:
    return _metadata_store.get(dataset_id)


def get_active_dataset_id() -> Optional[str]:
    return _active_dataset.get("id")


def get_active_metadata() -> Optional[dict]:
    did = get_active_dataset_id()
    return get_metadata(did) if did else None


# ─── Documents ───────────────────────────────────────────────────────────────

def save_docs(dataset_id: str, docs: dict):
    _docs_store[dataset_id] = {
        **docs,
        "_generated_at": datetime.now().isoformat(),
    }


def get_docs(dataset_id: str) -> Optional[dict]:
    return _docs_store.get(dataset_id)


def get_active_docs() -> Optional[dict]:
    did = get_active_dataset_id()
    return get_docs(did) if did else None


# ─── Chat history ─────────────────────────────────────────────────────────

def append_chat(dataset_id: str, role: str, content: str):
    if dataset_id not in _chat_store:
        _chat_store[dataset_id] = []
    _chat_store[dataset_id].append({"role": role, "content": content})


def get_chat_history(dataset_id: str) -> list:
    return _chat_store.get(dataset_id, [])


def clear_chat(dataset_id: str):
    _chat_store[dataset_id] = []


# ─── Version history ──────────────────────────────────────────────────────

def save_version(dataset_id: str, metadata: dict, changes: dict | None = None):
    if dataset_id not in _version_store:
        _version_store[dataset_id] = []

    version_num = len(_version_store[dataset_id]) + 1
    _version_store[dataset_id].append({
        "version": f"v{version_num}",
        "timestamp": datetime.now().isoformat(),
        "metadata_snapshot": metadata,
        "table_count": metadata.get("table_count", 0),
        "measure_count": metadata.get("measure_count", 0),
        "changes": changes or {},
    })


def get_versions(dataset_id: str) -> list:
    return _version_store.get(dataset_id, [])


def get_previous_metadata(dataset_id: str) -> Optional[dict]:
    """Returns the second-to-last version's metadata (for diff comparison)."""
    versions = _version_store.get(dataset_id, [])
    if len(versions) < 2:
        return None
    return versions[-2]["metadata_snapshot"]


# ─── Audit score ──────────────────────────────────────────────────────────

def save_audit_score(dataset_id: str, score: dict):
    _audit_store[dataset_id] = {**score, "_scored_at": datetime.now().isoformat()}


def get_audit_score(dataset_id: str) -> Optional[dict]:
    return _audit_store.get(dataset_id)


# ─── Full session summary ────────────────────────────────────────────────

def session_summary() -> dict:
    did = get_active_dataset_id()
    if not did:
        return {"active": False}

    docs = get_docs(did) or {}
    doc_types = [k for k in docs.keys() if not k.startswith("_")]
    audit = get_audit_score(did) or {}

    return {
        "active": True,
        "dataset_id": did,
        "dataset_name": _active_dataset.get("name", "Unknown"),
        "docs_generated": doc_types,
        "doc_count": len([k for k in doc_types if k != "audit_score"]),
        "version_count": len(get_versions(did)),
        "chat_messages": len(get_chat_history(did)),
        "audit_score": audit.get("overall_score"),
        "audit_grade": audit.get("grade"),
    }
