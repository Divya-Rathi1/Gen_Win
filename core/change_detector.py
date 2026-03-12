# core/change_detector.py
# ─────────────────────────────────────────────────────────────────────────────
# Compares old vs new metadata versions.
# Returns: structured diff + which doc sections need regeneration.
# Uses in-memory storage for prototype (no DB).
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import json
from typing import Optional
from deepdiff import DeepDiff


# ─── In-memory version store (prototype — lives for session lifetime) ────────
# Structure: { dataset_id: { "v1": metadata_dict, "v2": metadata_dict, ... } }
_version_store: dict[str, dict] = {}
_version_counter: dict[str, int] = {}


def save_version(dataset_id: str, metadata: dict) -> str:
    """Save a metadata snapshot. Returns version label like 'v1', 'v2'."""
    if dataset_id not in _version_counter:
        _version_counter[dataset_id] = 0
        _version_store[dataset_id] = {}

    _version_counter[dataset_id] += 1
    version_label = f"v{_version_counter[dataset_id]}"
    _version_store[dataset_id][version_label] = metadata
    return version_label


def get_version(dataset_id: str, version_label: str) -> Optional[dict]:
    return _version_store.get(dataset_id, {}).get(version_label)


def list_versions(dataset_id: str) -> list[str]:
    return list(_version_store.get(dataset_id, {}).keys())


def get_latest_version(dataset_id: str) -> Optional[dict]:
    versions = list_versions(dataset_id)
    if not versions:
        return None
    return _version_store[dataset_id][versions[-1]]


def metadata_hash(metadata: dict) -> str:
    """SHA256 of metadata — quick check if anything changed."""
    canonical = json.dumps(metadata, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def detect_changes(old_metadata: dict, new_metadata: dict) -> dict:
    """
    Deep diff between two metadata snapshots.
    Returns structured change summary with:
    - changed tables, added tables, removed tables
    - changed/added/removed measures
    - changed relationships
    - which document types need regeneration
    """
    diff = DeepDiff(old_metadata, new_metadata, ignore_order=True, verbose_level=2)

    # Build human-readable change summary
    changes = {
        "has_changes": bool(diff),
        "tables_added": [],
        "tables_removed": [],
        "tables_modified": [],
        "measures_added": [],
        "measures_removed": [],
        "measures_modified": [],
        "relationships_changed": False,
        "raw_diff": diff.to_json() if diff else "{}",
        "docs_to_regenerate": [],
        "change_count": 0,
    }

    if not diff:
        return changes

    diff_dict = json.loads(diff.to_json())

    # Parse table changes
    old_table_names = {t["name"] for t in old_metadata.get("tables", [])}
    new_table_names = {t["name"] for t in new_metadata.get("tables", [])}
    changes["tables_added"] = list(new_table_names - old_table_names)
    changes["tables_removed"] = list(old_table_names - new_table_names)

    # Parse measure changes
    old_measure_names = {m["name"] for m in old_metadata.get("measures", [])}
    new_measure_names = {m["name"] for m in new_metadata.get("measures", [])}
    changes["measures_added"] = list(new_measure_names - old_measure_names)
    changes["measures_removed"] = list(old_measure_names - new_measure_names)

    # Detect modified measures (same name, different expression)
    old_measures_map = {m["name"]: m["expression"] for m in old_metadata.get("measures", [])}
    new_measures_map = {m["name"]: m["expression"] for m in new_metadata.get("measures", [])}
    for name in old_measure_names & new_measure_names:
        if old_measures_map.get(name) != new_measures_map.get(name):
            changes["measures_modified"].append(name)

    # Detect modified tables (column changes)
    old_tables_map = {t["name"]: t for t in old_metadata.get("tables", [])}
    new_tables_map = {t["name"]: t for t in new_metadata.get("tables", [])}
    for name in old_table_names & new_table_names:
        old_cols = {c["name"] for c in old_tables_map[name].get("columns", [])}
        new_cols = {c["name"] for c in new_tables_map[name].get("columns", [])}
        if old_cols != new_cols:
            changes["tables_modified"].append(name)

    # Relationship changes
    old_rels = set(json.dumps(r, sort_keys=True) for r in old_metadata.get("relationships", []))
    new_rels = set(json.dumps(r, sort_keys=True) for r in new_metadata.get("relationships", []))
    changes["relationships_changed"] = old_rels != new_rels

    # Count total changes
    changes["change_count"] = (
        len(changes["tables_added"]) + len(changes["tables_removed"]) +
        len(changes["tables_modified"]) + len(changes["measures_added"]) +
        len(changes["measures_removed"]) + len(changes["measures_modified"]) +
        (1 if changes["relationships_changed"] else 0)
    )

    # Determine which docs need regeneration
    docs_to_regen = set()
    if changes["tables_added"] or changes["tables_removed"] or changes["tables_modified"]:
        docs_to_regen.update(["brd", "tdd", "fdd", "s2t", "qa_report", "audit_score"])
    if changes["measures_added"] or changes["measures_removed"] or changes["measures_modified"]:
        docs_to_regen.update(["tdd", "fdd", "qa_report", "audit_score"])
    if changes["relationships_changed"]:
        docs_to_regen.update(["tdd", "s2t", "audit_score"])

    changes["docs_to_regenerate"] = list(docs_to_regen)

    return changes


def format_diff_for_display(changes: dict) -> str:
    """Format changes dict into a readable string for UI display."""
    if not changes["has_changes"]:
        return "No changes detected since last version."

    lines = [f"**{changes['change_count']} changes detected:**\n"]

    if changes["tables_added"]:
        lines.append(f"✅ Tables Added: {', '.join(changes['tables_added'])}")
    if changes["tables_removed"]:
        lines.append(f"❌ Tables Removed: {', '.join(changes['tables_removed'])}")
    if changes["tables_modified"]:
        lines.append(f"✏️ Tables Modified: {', '.join(changes['tables_modified'])}")
    if changes["measures_added"]:
        lines.append(f"✅ Measures Added: {', '.join(changes['measures_added'])}")
    if changes["measures_removed"]:
        lines.append(f"❌ Measures Removed: {', '.join(changes['measures_removed'])}")
    if changes["measures_modified"]:
        lines.append(f"✏️ Measures Modified: {', '.join(changes['measures_modified'])}")
    if changes["relationships_changed"]:
        lines.append("🔗 Relationships changed")

    if changes["docs_to_regenerate"]:
        lines.append(f"\n📄 Docs needing regeneration: {', '.join(changes['docs_to_regenerate']).upper()}")

    return "\n".join(lines)
