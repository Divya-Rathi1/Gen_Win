# # main.py
# # ─────────────────────────────────────────────────────────────────────────────
# # AutoDocAI FastAPI Backend
# # All routes for: metadata ingestion, doc generation, chat, diff, export
# # ─────────────────────────────────────────────────────────────────────────────

# import os
# import sys
# sys.path.insert(0, os.path.dirname(__file__))

# from fastapi import FastAPI, HTTPException, Query
# from fastapi.responses import StreamingResponse, JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional
# import io
# from dotenv import load_dotenv

# load_dotenv()

# from core.pbi_connector import pull_full_metadata, list_workspaces, list_datasets
# from core.ai_client import (
#     generate_brd, generate_tdd, generate_fdd, generate_s2t,
#     generate_qa_report, generate_audit_score, generate_diff_narrative,
#     chat_with_metadata,
# )
# from core.change_detector import (
#     detect_changes, format_diff_for_display, metadata_hash,
# )
# from core.doc_exporter import to_word, to_pdf, export_all
# from core import session_store as store

# app = FastAPI(title="AutoDocAI", version="1.0.0", description="Automated Documentation for Power BI Projects")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ─── Pydantic models ─────────────────────────────────────────────────────────

# class ConnectRequest(BaseModel):
#     token: str
#     dataset_id: str
#     dataset_name: str
#     workspace_id: Optional[str] = None
#     workspace_name: str = "My Workspace"


# class ChatRequest(BaseModel):
#     question: str
#     dataset_id: Optional[str] = None


# class RegenerateRequest(BaseModel):
#     dataset_id: str
#     doc_types: list[str]  # e.g. ["brd", "tdd"]


# # ─── Health ──────────────────────────────────────────────────────────────────

# @app.get("/health")
# def health():
#     return {"status": "ok", "service": "AutoDocAI"}


# # ─── Power BI Connection ─────────────────────────────────────────────────────

# @app.get("/pbi/workspaces")
# def get_workspaces(token: str = Query(..., description="Bearer token from Power BI")):
#     """List all accessible workspaces for the given token."""
#     try:
#         workspaces = list_workspaces(token)
#         return {"workspaces": workspaces}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"PBI API error: {str(e)}")


# @app.get("/pbi/datasets")
# def get_datasets(
#     token: str = Query(...),
#     workspace_id: Optional[str] = Query(None)
# ):
#     """List all datasets in a workspace."""
#     try:
#         datasets = list_datasets(token, workspace_id)
#         return {"datasets": datasets}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"PBI API error: {str(e)}")


# @app.post("/connect")
# def connect_dataset(req: ConnectRequest):
#     """
#     Pull full metadata from a Power BI dataset and store in session.
#     This is the main entry point — call this first.
#     """
#     try:
#         metadata = pull_full_metadata(
#             token=req.token,
#             dataset_id=req.dataset_id,
#             dataset_name=req.dataset_name,
#             workspace_id=req.workspace_id,
#             workspace_name=req.workspace_name,
#         )

#         # Check if we already have a previous version for diff
#         previous = store.get_previous_metadata(req.dataset_id)
#         changes = None
#         if previous:
#             changes = detect_changes(previous, metadata)

#         # Save to session
#         store.save_metadata(req.dataset_id, metadata)
#         store.store_version(req.dataset_id, metadata, changes)

#         return {
#             "success": True,
#             "dataset_id": req.dataset_id,
#             "dataset_name": req.dataset_name,
#             "table_count": metadata["table_count"],
#             "measure_count": metadata["measure_count"],
#             "relationship_count": metadata["relationship_count"],
#             "metadata_hash": metadata_hash(metadata),
#             "version": f"v{len(store.get_versions(req.dataset_id))}",
#             "has_previous_version": previous is not None,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# # ─── Document Generation ─────────────────────────────────────────────────────

# @app.post("/generate/all")
# def generate_all(dataset_id: str = Query(...)):
#     """
#     Generate all 5 documents + audit score for the connected dataset.
#     Returns all docs in one response.
#     """
#     metadata = store.get_metadata(dataset_id)
#     if not metadata:
#         raise HTTPException(status_code=404, detail="Dataset not connected. Call /connect first.")

#     try:
#         docs = {}
#         docs["brd"] = generate_brd(metadata)
#         docs["tdd"] = generate_tdd(metadata)
#         docs["fdd"] = generate_fdd(metadata)
#         docs["s2t"] = generate_s2t(metadata)
#         docs["qa_report"] = generate_qa_report(metadata)

#         doc_status = {k: bool(v) for k, v in docs.items()}
#         audit = generate_audit_score(metadata, doc_status)
#         docs["audit_score"] = audit

#         store.save_docs(dataset_id, docs)
#         store.save_audit_score(dataset_id, audit)

#         return {
#             "success": True,
#             "dataset_id": dataset_id,
#             "docs_generated": [k for k in docs.keys() if k != "audit_score"],
#             "audit_score": audit.get("overall_score"),
#             "audit_grade": audit.get("grade"),
#             "docs": {k: v for k, v in docs.items() if k != "audit_score"},
#             "audit": audit,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/generate/{doc_type}")
# def generate_single(doc_type: str, dataset_id: str = Query(...)):
#     """Generate a single document type. doc_type: brd|tdd|fdd|s2t|qa_report|audit_score"""
#     metadata = store.get_metadata(dataset_id)
#     if not metadata:
#         raise HTTPException(status_code=404, detail="Dataset not connected.")

#     generators = {
#         "brd": lambda: generate_brd(metadata),
#         "tdd": lambda: generate_tdd(metadata),
#         "fdd": lambda: generate_fdd(metadata),
#         "s2t": lambda: generate_s2t(metadata),
#         "qa_report": lambda: generate_qa_report(metadata),
#         "audit_score": lambda: generate_audit_score(metadata, store.get_docs(dataset_id) or {}),
#     }

#     if doc_type not in generators:
#         raise HTTPException(status_code=400, detail=f"Unknown doc type: {doc_type}. Choose from: {list(generators.keys())}")

#     try:
#         result = generators[doc_type]()

#         # Save to existing docs
#         existing = store.get_docs(dataset_id) or {}
#         existing[doc_type] = result
#         store.save_docs(dataset_id, existing)

#         if doc_type == "audit_score":
#             store.save_audit_score(dataset_id, result)
#             return {"success": True, "doc_type": doc_type, "audit": result}

#         return {"success": True, "doc_type": doc_type, "content": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/regenerate")
# def regenerate_docs(req: RegenerateRequest):
#     """Regenerate specific doc types (called after change detection)."""
#     metadata = store.get_metadata(req.dataset_id)
#     if not metadata:
#         raise HTTPException(status_code=404, detail="Dataset not connected.")

#     results = {}
#     existing = store.get_docs(req.dataset_id) or {}

#     for doc_type in req.doc_types:
#         try:
#             resp = generate_single.__wrapped__(doc_type, req.dataset_id) if hasattr(generate_single, '__wrapped__') else None
#             # Call generator directly
#             from core.ai_client import generate_brd, generate_tdd, generate_fdd, generate_s2t, generate_qa_report, generate_audit_score
#             gen_map = {
#                 "brd": generate_brd, "tdd": generate_tdd, "fdd": generate_fdd,
#                 "s2t": generate_s2t, "qa_report": generate_qa_report,
#             }
#             if doc_type in gen_map:
#                 results[doc_type] = gen_map[doc_type](metadata)
#                 existing[doc_type] = results[doc_type]
#         except Exception as e:
#             results[doc_type] = f"Error: {str(e)}"

#     store.save_docs(req.dataset_id, existing)
#     return {"success": True, "regenerated": list(results.keys()), "docs": results}


# # ─── Retrieve docs ────────────────────────────────────────────────────────────

# @app.get("/docs/{dataset_id}")
# def get_all_docs(dataset_id: str):
#     """Get all generated documents for a dataset."""
#     docs = store.get_docs(dataset_id)
#     if not docs:
#         raise HTTPException(status_code=404, detail="No documents generated yet. Call /generate/all first.")
#     return {"dataset_id": dataset_id, "docs": docs}


# @app.get("/docs/{dataset_id}/{doc_type}")
# def get_doc(dataset_id: str, doc_type: str):
#     """Get a specific document."""
#     docs = store.get_docs(dataset_id)
#     if not docs or doc_type not in docs:
#         raise HTTPException(status_code=404, detail=f"Document '{doc_type}' not found.")
#     return {"dataset_id": dataset_id, "doc_type": doc_type, "content": docs[doc_type]}


# # ─── Export ──────────────────────────────────────────────────────────────────

# @app.get("/export/{dataset_id}/{doc_type}")
# def export_doc(
#     dataset_id: str,
#     doc_type: str,
#     fmt: str = Query("word", description="word or pdf"),
# ):
#     """Download a document as Word or PDF."""
#     docs = store.get_docs(dataset_id)
#     if not docs or doc_type not in docs:
#         raise HTTPException(status_code=404, detail=f"Document '{doc_type}' not found.")

#     content = docs[doc_type]
#     if not isinstance(content, str):
#         raise HTTPException(status_code=400, detail="audit_score cannot be exported as a document.")

#     metadata = store.get_metadata(dataset_id)
#     dataset_name = metadata.get("dataset_name", "Unknown") if metadata else "Unknown"

#     if fmt == "pdf":
#         file_bytes = to_pdf(doc_type, content, dataset_name)
#         media_type = "application/pdf"
#         filename = f"{doc_type}_{dataset_name}.pdf"
#     else:
#         file_bytes = to_word(doc_type, content, dataset_name)
#         media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#         filename = f"{doc_type}_{dataset_name}.docx"

#     return StreamingResponse(
#         io.BytesIO(file_bytes),
#         media_type=media_type,
#         headers={"Content-Disposition": f"attachment; filename={filename}"},
#     )


# @app.get("/export/{dataset_id}/all/zip")
# def export_all_docs(dataset_id: str, fmt: str = Query("word")):
#     """Download all documents as a ZIP archive."""
#     import zipfile

#     docs = store.get_docs(dataset_id)
#     if not docs:
#         raise HTTPException(status_code=404, detail="No documents to export.")

#     metadata = store.get_metadata(dataset_id)
#     dataset_name = metadata.get("dataset_name", "Unknown") if metadata else "Unknown"

#     zip_buf = io.BytesIO()
#     with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
#         for doc_type, content in docs.items():
#             if doc_type.startswith("_") or not isinstance(content, str):
#                 continue
#             if fmt == "pdf":
#                 file_bytes = to_pdf(doc_type, content, dataset_name)
#                 zf.writestr(f"{doc_type}_{dataset_name}.pdf", file_bytes)
#             else:
#                 file_bytes = to_word(doc_type, content, dataset_name)
#                 zf.writestr(f"{doc_type}_{dataset_name}.docx", file_bytes)

#     zip_buf.seek(0)
#     return StreamingResponse(
#         zip_buf,
#         media_type="application/zip",
#         headers={"Content-Disposition": f"attachment; filename=AutoDocAI_{dataset_name}.zip"},
#     )


# # ─── Chat ────────────────────────────────────────────────────────────────────

# @app.post("/chat")
# def chat(req: ChatRequest):
#     """
#     Chat Q&A powered by metadata context (context-window RAG).
#     Maintains conversation history per dataset.
#     """
#     dataset_id = req.dataset_id or store.get_active_dataset_id()
#     if not dataset_id:
#         raise HTTPException(status_code=400, detail="No active dataset. Connect one first.")

#     metadata = store.get_metadata(dataset_id)
#     if not metadata:
#         raise HTTPException(status_code=404, detail="Dataset metadata not found.")

#     history = store.get_chat_history(dataset_id)

#     try:
#         answer = chat_with_metadata(metadata, history, req.question)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # Save turn to history
#     store.append_chat(dataset_id, "user", req.question)
#     store.append_chat(dataset_id, "assistant", answer)

#     return {
#         "question": req.question,
#         "answer": answer,
#         "history_length": len(store.get_chat_history(dataset_id)) // 2,
#     }


# @app.get("/chat/{dataset_id}/history")
# def get_chat_history(dataset_id: str):
#     return {"history": store.get_chat_history(dataset_id)}


# @app.delete("/chat/{dataset_id}/clear")
# def clear_chat(dataset_id: str):
#     store.clear_chat(dataset_id)
#     return {"success": True, "message": "Chat history cleared."}


# # ─── Change Detection & Diff ─────────────────────────────────────────────────

# @app.post("/diff/{dataset_id}")
# def run_diff(dataset_id: str, token: str = Query(...)):
#     """
#     Re-pull metadata and compare against saved version.
#     Returns change summary + which docs need regeneration.
#     """
#     old_metadata = store.get_metadata(dataset_id)
#     if not old_metadata:
#         raise HTTPException(status_code=404, detail="No previous metadata. Connect the dataset first.")

#     try:
#         # Re-pull fresh metadata
#         new_metadata = pull_full_metadata(
#             token=token,
#             dataset_id=dataset_id,
#             dataset_name=old_metadata["dataset_name"],
#             workspace_id=old_metadata.get("workspace_id"),
#             workspace_name=old_metadata.get("workspace_name", "My Workspace"),
#         )

#         changes = detect_changes(old_metadata, new_metadata)

#         narrative = ""
#         if changes["has_changes"]:
#             narrative = generate_diff_narrative(old_metadata, new_metadata, changes)
#             # Save new version
#             store.save_metadata(dataset_id, new_metadata)
#             store.store_version(dataset_id, new_metadata, changes)

#         return {
#             "has_changes": changes["has_changes"],
#             "change_count": changes["change_count"],
#             "changes": changes,
#             "display_summary": format_diff_for_display(changes),
#             "narrative": narrative,
#             "docs_to_regenerate": changes["docs_to_regenerate"],
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # ─── Version History ─────────────────────────────────────────────────────────

# @app.get("/versions/{dataset_id}")
# def get_versions(dataset_id: str):
#     versions = store.get_versions(dataset_id)
#     # Return without full metadata snapshots (too large)
#     summary = [{
#         "version": v["version"],
#         "timestamp": v["timestamp"],
#         "table_count": v["table_count"],
#         "measure_count": v["measure_count"],
#         "change_count": v.get("changes", {}).get("change_count", 0),
#     } for v in versions]
#     return {"dataset_id": dataset_id, "versions": summary}


# # ─── Audit Score ─────────────────────────────────────────────────────────────

# @app.get("/audit/{dataset_id}")
# def get_audit(dataset_id: str):
#     score = store.get_audit_score(dataset_id)
#     if not score:
#         raise HTTPException(status_code=404, detail="No audit score yet. Run /generate/all first.")
#     return score


# # ─── Session Summary ─────────────────────────────────────────────────────────

# @app.get("/session")
# def get_session():
#     return store.session_summary()


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# # ─── GitHub Webhook ───────────────────────────────────────────────────────────

# import hmac
# import hashlib
# from fastapi import Request, BackgroundTasks

# WEBHOOK_LOG: list[dict] = []


# def _verify_github_signature(payload_bytes: bytes, signature_header: str) -> bool:
#     secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
#     if not secret:
#         return True  # skip verification if no secret set (fine for prototype)
#     if not signature_header or not signature_header.startswith("sha256="):
#         return False
#     expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
#     return hmac.compare_digest(expected, signature_header)


# def _do_regeneration(dataset_id: str, docs_to_regen: list, metadata: dict):
#     """Background task: regenerate only the affected docs after a push."""
#     from core.ai_client import (
#         generate_brd, generate_tdd, generate_fdd,
#         generate_s2t, generate_qa_report, generate_audit_score,
#     )
#     gen_map = {
#         "brd": generate_brd, "tdd": generate_tdd, "fdd": generate_fdd,
#         "s2t": generate_s2t, "qa_report": generate_qa_report,
#     }
#     existing = store.get_docs(dataset_id) or {}
#     for doc_type in docs_to_regen:
#         if doc_type in gen_map:
#             try:
#                 existing[doc_type] = gen_map[doc_type](metadata)
#             except Exception as e:
#                 existing[doc_type] = f"[Regeneration error: {e}]"

#     doc_status = {k: bool(v) for k, v in existing.items() if not k.startswith("_")}
#     existing["audit_score"] = generate_audit_score(metadata, doc_status)
#     store.save_docs(dataset_id, existing)
#     store.save_audit_score(dataset_id, existing["audit_score"])


# @app.post("/webhook/github")
# async def github_webhook(request: Request, background_tasks: BackgroundTasks):
#     """
#     GitHub sends POST here on every push to main/master.
#     Setup: GitHub repo → Settings → Webhooks → Add webhook
#       Payload URL : https://YOUR-NGROK-URL.ngrok.io/webhook/github
#       Content type: application/json
#       Secret      : same as GITHUB_WEBHOOK_SECRET in .env
#       Events      : Just the push event
#     """
#     import datetime
#     payload_bytes = await request.body()
#     signature    = request.headers.get("X-Hub-Signature-256", "")
#     event_type   = request.headers.get("X-GitHub-Event", "unknown")
#     delivery_id  = request.headers.get("X-GitHub-Delivery", "unknown")

#     if not _verify_github_signature(payload_bytes, signature):
#         raise HTTPException(status_code=401, detail="Invalid webhook signature.")

#     try:
#         payload = await request.json()
#     except Exception:
#         payload = {}

#     log_entry = {
#         "delivery_id" : delivery_id,
#         "event_type"  : event_type,
#         "timestamp"   : datetime.datetime.now().isoformat(),
#         "repository"  : payload.get("repository", {}).get("full_name", "unknown"),
#         "pusher"      : payload.get("pusher", {}).get("name", "unknown"),
#         "commits"     : len(payload.get("commits", [])),
#         "ref"         : payload.get("ref", ""),
#         "status"      : "received",
#         "docs_regenerated": [],
#     }
#     WEBHOOK_LOG.append(log_entry)

#     # Only act on pushes to main or master
#     ref = payload.get("ref", "")
#     if event_type != "push" or ref not in ("refs/heads/main", "refs/heads/master"):
#         log_entry["status"] = f"ignored ({event_type} / {ref})"
#         return {"received": True, "action": "ignored", "reason": f"Not a push to main/master"}

#     # Need an active connected dataset
#     dataset_id = store.get_active_dataset_id()
#     if not dataset_id:
#         log_entry["status"] = "skipped — no active dataset"
#         return {"received": True, "action": "skipped", "reason": "No dataset connected."}

#     old_metadata = store.get_metadata(dataset_id)
#     if not old_metadata:
#         log_entry["status"] = "skipped — no metadata"
#         return {"received": True, "action": "skipped"}

#     # Re-pull PBI metadata using the token stored in .env
#     pbi_token = os.getenv("POWERBI_WEBHOOK_TOKEN", "")
#     if not pbi_token:
#         log_entry["status"] = "skipped — POWERBI_WEBHOOK_TOKEN not set"
#         return {
#             "received": True, "action": "skipped",
#             "reason": "Add POWERBI_WEBHOOK_TOKEN to .env for auto-refresh.",
#         }

#     try:
#         new_metadata = pull_full_metadata(
#             token=pbi_token,
#             dataset_id=dataset_id,
#             dataset_name=old_metadata["dataset_name"],
#             workspace_id=old_metadata.get("workspace_id"),
#             workspace_name=old_metadata.get("workspace_name", "My Workspace"),
#         )
#     except Exception as e:
#         log_entry["status"] = f"error: {e}"
#         return {"received": True, "action": "error", "reason": str(e)}

#     changes = detect_changes(old_metadata, new_metadata)

#     if not changes["has_changes"]:
#         log_entry["status"] = "no changes detected"
#         return {"received": True, "action": "no_changes"}

#     store.save_metadata(dataset_id, new_metadata)
#     store.store_version(dataset_id, new_metadata, changes)

#     narrative = generate_diff_narrative(old_metadata, new_metadata, changes)
#     docs_to_regen = changes.get("docs_to_regenerate", [])
#     log_entry["docs_regenerated"] = docs_to_regen
#     log_entry["status"] = "regenerating in background"

#     # Regenerate affected docs without blocking the response
#     background_tasks.add_task(_do_regeneration, dataset_id, docs_to_regen, new_metadata)

#     return {
#         "received"        : True,
#         "action"          : "regenerating",
#         "change_count"    : changes["change_count"],
#         "changes_summary" : format_diff_for_display(changes),
#         "narrative"       : narrative,
#         "docs_to_regen"   : docs_to_regen,
#         "delivery_id"     : delivery_id,
#     }


# @app.get("/webhook/log")
# def get_webhook_log():
#     """See all webhook events received — useful for demo / debugging."""
#     return {"events": list(reversed(WEBHOOK_LOG)), "total": len(WEBHOOK_LOG)}


# @app.delete("/webhook/log")
# def clear_webhook_log():
#     WEBHOOK_LOG.clear()
#     return {"cleared": True}


# main.py
# ─────────────────────────────────────────────────────────────────────────────
# AutoDocAI FastAPI Backend
# All routes for: metadata ingestion, doc generation, chat, diff, export
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import io
from dotenv import load_dotenv

load_dotenv()

from core.pbi_connector import pull_full_metadata, list_workspaces, list_datasets
from core.ai_client import (
    generate_brd, generate_tdd, generate_fdd, generate_s2t,
    generate_qa_report, generate_audit_score, generate_diff_narrative,
    chat_with_metadata,
)
from core.change_detector import (
    detect_changes, format_diff_for_display, metadata_hash,
)
from core.doc_exporter import to_word, to_pdf, export_all
from core import session_store as store

app = FastAPI(title="AutoDocAI", version="1.0.0", description="Automated Documentation for Power BI Projects")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic models ─────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    token: str
    dataset_id: str
    dataset_name: str
    workspace_id: Optional[str] = None
    workspace_name: str = "My Workspace"


class ChatRequest(BaseModel):
    question: str
    dataset_id: Optional[str] = None


class RegenerateRequest(BaseModel):
    dataset_id: str
    doc_types: list[str]  # e.g. ["brd", "tdd"]


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "AutoDocAI"}


# ─── Power BI Connection ─────────────────────────────────────────────────────

@app.get("/pbi/workspaces")
def get_workspaces(token: str = Query(..., description="Bearer token from Power BI")):
    """List all accessible workspaces for the given token."""
    try:
        workspaces = list_workspaces(token)
        return {"workspaces": workspaces}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PBI API error: {str(e)}")


@app.get("/pbi/datasets")
def get_datasets(
    token: str = Query(...),
    workspace_id: Optional[str] = Query(None)
):
    """List all datasets in a workspace."""
    try:
        datasets = list_datasets(token, workspace_id)
        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PBI API error: {str(e)}")


@app.post("/connect")
def connect_dataset(req: ConnectRequest):
    """
    Pull full metadata from a Power BI dataset and store in session.
    This is the main entry point — call this first.
    """
    try:
        metadata = pull_full_metadata(
            token=req.token,
            dataset_id=req.dataset_id,
            dataset_name=req.dataset_name,
            workspace_id=req.workspace_id,
            workspace_name=req.workspace_name,
        )

        # Check if we already have a previous version for diff
        previous = store.get_previous_metadata(req.dataset_id)
        changes = None
        if previous:
            changes = detect_changes(previous, metadata)

        # Save to session
        store.save_metadata(req.dataset_id, metadata)
        store.save_version(req.dataset_id, metadata, changes)

        return {
            "success": True,
            "dataset_id": req.dataset_id,
            "dataset_name": req.dataset_name,
            "table_count": metadata["table_count"],
            "measure_count": metadata["measure_count"],
            "relationship_count": metadata["relationship_count"],
            "metadata_hash": metadata_hash(metadata),
            "version": f"v{len(store.get_versions(req.dataset_id))}",
            "has_previous_version": previous is not None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Document Generation ─────────────────────────────────────────────────────

@app.post("/generate/all")
def generate_all(dataset_id: str = Query(...)):
    """
    Generate all 5 documents + audit score for the connected dataset.
    Returns all docs in one response.
    """
    metadata = store.get_metadata(dataset_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset not connected. Call /connect first.")

    try:
        docs = {}
        docs["brd"] = generate_brd(metadata)
        docs["tdd"] = generate_tdd(metadata)
        docs["fdd"] = generate_fdd(metadata)
        docs["s2t"] = generate_s2t(metadata)
        docs["qa_report"] = generate_qa_report(metadata)

        doc_status = {k: bool(v) for k, v in docs.items()}
        audit = generate_audit_score(metadata, doc_status)
        docs["audit_score"] = audit

        store.save_docs(dataset_id, docs)
        store.save_audit_score(dataset_id, audit)

        return {
            "success": True,
            "dataset_id": dataset_id,
            "docs_generated": [k for k in docs.keys() if k != "audit_score"],
            "audit_score": audit.get("overall_score"),
            "audit_grade": audit.get("grade"),
            "docs": {k: v for k, v in docs.items() if k != "audit_score"},
            "audit": audit,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/{doc_type}")
def generate_single(doc_type: str, dataset_id: str = Query(...)):
    """Generate a single document type. doc_type: brd|tdd|fdd|s2t|qa_report|audit_score"""
    metadata = store.get_metadata(dataset_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset not connected.")

    generators = {
        "brd": lambda: generate_brd(metadata),
        "tdd": lambda: generate_tdd(metadata),
        "fdd": lambda: generate_fdd(metadata),
        "s2t": lambda: generate_s2t(metadata),
        "qa_report": lambda: generate_qa_report(metadata),
        "audit_score": lambda: generate_audit_score(metadata, store.get_docs(dataset_id) or {}),
    }

    if doc_type not in generators:
        raise HTTPException(status_code=400, detail=f"Unknown doc type: {doc_type}. Choose from: {list(generators.keys())}")

    try:
        result = generators[doc_type]()

        # Save to existing docs
        existing = store.get_docs(dataset_id) or {}
        existing[doc_type] = result
        store.save_docs(dataset_id, existing)

        if doc_type == "audit_score":
            store.save_audit_score(dataset_id, result)
            return {"success": True, "doc_type": doc_type, "audit": result}

        return {"success": True, "doc_type": doc_type, "content": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate")
def regenerate_docs(req: RegenerateRequest):
    """Regenerate specific doc types (called after change detection)."""
    metadata = store.get_metadata(req.dataset_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset not connected.")

    results = {}
    existing = store.get_docs(req.dataset_id) or {}

    for doc_type in req.doc_types:
        try:
            resp = generate_single.__wrapped__(doc_type, req.dataset_id) if hasattr(generate_single, '__wrapped__') else None
            # Call generator directly
            from core.ai_client import generate_brd, generate_tdd, generate_fdd, generate_s2t, generate_qa_report, generate_audit_score
            gen_map = {
                "brd": generate_brd, "tdd": generate_tdd, "fdd": generate_fdd,
                "s2t": generate_s2t, "qa_report": generate_qa_report,
            }
            if doc_type in gen_map:
                results[doc_type] = gen_map[doc_type](metadata)
                existing[doc_type] = results[doc_type]
        except Exception as e:
            results[doc_type] = f"Error: {str(e)}"

    store.save_docs(req.dataset_id, existing)
    return {"success": True, "regenerated": list(results.keys()), "docs": results}


# ─── Retrieve docs ────────────────────────────────────────────────────────────

@app.get("/docs/{dataset_id}")
def get_all_docs(dataset_id: str):
    """Get all generated documents for a dataset."""
    docs = store.get_docs(dataset_id)
    if not docs:
        raise HTTPException(status_code=404, detail="No documents generated yet. Call /generate/all first.")
    return {"dataset_id": dataset_id, "docs": docs}


@app.get("/docs/{dataset_id}/{doc_type}")
def get_doc(dataset_id: str, doc_type: str):
    """Get a specific document."""
    docs = store.get_docs(dataset_id)
    if not docs or doc_type not in docs:
        raise HTTPException(status_code=404, detail=f"Document '{doc_type}' not found.")
    return {"dataset_id": dataset_id, "doc_type": doc_type, "content": docs[doc_type]}


# ─── Export ──────────────────────────────────────────────────────────────────

@app.get("/export/{dataset_id}/{doc_type}")
def export_doc(
    dataset_id: str,
    doc_type: str,
    fmt: str = Query("word", description="word or pdf"),
):
    """Download a document as Word or PDF."""
    docs = store.get_docs(dataset_id)
    if not docs or doc_type not in docs:
        raise HTTPException(status_code=404, detail=f"Document '{doc_type}' not found.")

    content = docs[doc_type]
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="audit_score cannot be exported as a document.")

    metadata = store.get_metadata(dataset_id)
    dataset_name = metadata.get("dataset_name", "Unknown") if metadata else "Unknown"

    if fmt == "pdf":
        file_bytes = to_pdf(doc_type, content, dataset_name)
        media_type = "application/pdf"
        filename = f"{doc_type}_{dataset_name}.pdf"
    else:
        file_bytes = to_word(doc_type, content, dataset_name)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{doc_type}_{dataset_name}.docx"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export/{dataset_id}/all/zip")
def export_all_docs(dataset_id: str, fmt: str = Query("word")):
    """Download all documents as a ZIP archive."""
    import zipfile

    docs = store.get_docs(dataset_id)
    if not docs:
        raise HTTPException(status_code=404, detail="No documents to export.")

    metadata = store.get_metadata(dataset_id)
    dataset_name = metadata.get("dataset_name", "Unknown") if metadata else "Unknown"

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc_type, content in docs.items():
            if doc_type.startswith("_") or not isinstance(content, str):
                continue
            if fmt == "pdf":
                file_bytes = to_pdf(doc_type, content, dataset_name)
                zf.writestr(f"{doc_type}_{dataset_name}.pdf", file_bytes)
            else:
                file_bytes = to_word(doc_type, content, dataset_name)
                zf.writestr(f"{doc_type}_{dataset_name}.docx", file_bytes)

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=AutoDocAI_{dataset_name}.zip"},
    )


# ─── Chat ────────────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest):
    """
    Chat Q&A powered by metadata context (context-window RAG).
    Maintains conversation history per dataset.
    """
    dataset_id = req.dataset_id or store.get_active_dataset_id()
    if not dataset_id:
        raise HTTPException(status_code=400, detail="No active dataset. Connect one first.")

    metadata = store.get_metadata(dataset_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset metadata not found.")

    history = store.get_chat_history(dataset_id)

    try:
        answer = chat_with_metadata(metadata, history, req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Save turn to history
    store.append_chat(dataset_id, "user", req.question)
    store.append_chat(dataset_id, "assistant", answer)

    return {
        "question": req.question,
        "answer": answer,
        "history_length": len(store.get_chat_history(dataset_id)) // 2,
    }


@app.get("/chat/{dataset_id}/history")
def get_chat_history(dataset_id: str):
    return {"history": store.get_chat_history(dataset_id)}


@app.delete("/chat/{dataset_id}/clear")
def clear_chat(dataset_id: str):
    store.clear_chat(dataset_id)
    return {"success": True, "message": "Chat history cleared."}


# ─── Change Detection & Diff ─────────────────────────────────────────────────

@app.post("/diff/{dataset_id}")
def run_diff(dataset_id: str, token: str = Query(...)):
    """
    Re-pull metadata and compare against saved version.
    Returns change summary + which docs need regeneration.
    """
    old_metadata = store.get_metadata(dataset_id)
    if not old_metadata:
        raise HTTPException(status_code=404, detail="No previous metadata. Connect the dataset first.")

    try:
        # Re-pull fresh metadata
        new_metadata = pull_full_metadata(
            token=token,
            dataset_id=dataset_id,
            dataset_name=old_metadata["dataset_name"],
            workspace_id=old_metadata.get("workspace_id"),
            workspace_name=old_metadata.get("workspace_name", "My Workspace"),
        )

        changes = detect_changes(old_metadata, new_metadata)

        narrative = ""
        if changes["has_changes"]:
            narrative = generate_diff_narrative(old_metadata, new_metadata, changes)
            # Save new version
            store.save_metadata(dataset_id, new_metadata)
            store.save_version(dataset_id, new_metadata, changes)

        return {
            "has_changes": changes["has_changes"],
            "change_count": changes["change_count"],
            "changes": changes,
            "display_summary": format_diff_for_display(changes),
            "narrative": narrative,
            "docs_to_regenerate": changes["docs_to_regenerate"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Version History ─────────────────────────────────────────────────────────

@app.get("/versions/{dataset_id}")
def get_versions(dataset_id: str):
    versions = store.get_versions(dataset_id)
    # Return without full metadata snapshots (too large)
    summary = [{
        "version": v["version"],
        "timestamp": v["timestamp"],
        "table_count": v["table_count"],
        "measure_count": v["measure_count"],
        "change_count": v.get("changes", {}).get("change_count", 0),
    } for v in versions]
    return {"dataset_id": dataset_id, "versions": summary}


# ─── Audit Score ─────────────────────────────────────────────────────────────

@app.get("/audit/{dataset_id}")
def get_audit(dataset_id: str):
    score = store.get_audit_score(dataset_id)
    if not score:
        raise HTTPException(status_code=404, detail="No audit score yet. Run /generate/all first.")
    return score


# ─── Session Summary ─────────────────────────────────────────────────────────

@app.get("/session")
def get_session():
    return store.session_summary()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# ─── GitHub Webhook ───────────────────────────────────────────────────────────

import hmac
import hashlib
from fastapi import Request, BackgroundTasks

WEBHOOK_LOG: list[dict] = []


def _verify_github_signature(payload_bytes: bytes, signature_header: str) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        return True  # skip verification if no secret set (fine for prototype)
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _do_regeneration(dataset_id: str, docs_to_regen: list, metadata: dict):
    """Background task: regenerate only the affected docs after a push."""
    from core.ai_client import (
        generate_brd, generate_tdd, generate_fdd,
        generate_s2t, generate_qa_report, generate_audit_score,
    )
    gen_map = {
        "brd": generate_brd, "tdd": generate_tdd, "fdd": generate_fdd,
        "s2t": generate_s2t, "qa_report": generate_qa_report,
    }
    existing = store.get_docs(dataset_id) or {}
    for doc_type in docs_to_regen:
        if doc_type in gen_map:
            try:
                existing[doc_type] = gen_map[doc_type](metadata)
            except Exception as e:
                existing[doc_type] = f"[Regeneration error: {e}]"

    doc_status = {k: bool(v) for k, v in existing.items() if not k.startswith("_")}
    existing["audit_score"] = generate_audit_score(metadata, doc_status)
    store.save_docs(dataset_id, existing)
    store.save_audit_score(dataset_id, existing["audit_score"])


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    GitHub sends POST here on every push to main/master.
    Setup: GitHub repo → Settings → Webhooks → Add webhook
      Payload URL : https://YOUR-NGROK-URL.ngrok.io/webhook/github
      Content type: application/json
      Secret      : same as GITHUB_WEBHOOK_SECRET in .env
      Events      : Just the push event
    """
    import datetime
    payload_bytes = await request.body()
    signature    = request.headers.get("X-Hub-Signature-256", "")
    event_type   = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id  = request.headers.get("X-GitHub-Delivery", "unknown")

    if not _verify_github_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    log_entry = {
        "delivery_id" : delivery_id,
        "event_type"  : event_type,
        "timestamp"   : datetime.datetime.now().isoformat(),
        "repository"  : payload.get("repository", {}).get("full_name", "unknown"),
        "pusher"      : payload.get("pusher", {}).get("name", "unknown"),
        "commits"     : len(payload.get("commits", [])),
        "ref"         : payload.get("ref", ""),
        "status"      : "received",
        "docs_regenerated": [],
    }
    WEBHOOK_LOG.append(log_entry)

    # Only act on pushes to main or master
    ref = payload.get("ref", "")
    if event_type != "push" or ref not in ("refs/heads/main", "refs/heads/master"):
        log_entry["status"] = f"ignored ({event_type} / {ref})"
        return {"received": True, "action": "ignored", "reason": f"Not a push to main/master"}

    # Need an active connected dataset
    dataset_id = store.get_active_dataset_id()
    if not dataset_id:
        log_entry["status"] = "skipped — no active dataset"
        return {"received": True, "action": "skipped", "reason": "No dataset connected."}

    old_metadata = store.get_metadata(dataset_id)
    if not old_metadata:
        log_entry["status"] = "skipped — no metadata"
        return {"received": True, "action": "skipped"}

    # Re-pull PBI metadata using the token stored in .env
    pbi_token = os.getenv("POWERBI_WEBHOOK_TOKEN", "")
    if not pbi_token:
        log_entry["status"] = "skipped — POWERBI_WEBHOOK_TOKEN not set"
        return {
            "received": True, "action": "skipped",
            "reason": "Add POWERBI_WEBHOOK_TOKEN to .env for auto-refresh.",
        }

    try:
        new_metadata = pull_full_metadata(
            token=pbi_token,
            dataset_id=dataset_id,
            dataset_name=old_metadata["dataset_name"],
            workspace_id=old_metadata.get("workspace_id"),
            workspace_name=old_metadata.get("workspace_name", "My Workspace"),
        )
    except Exception as e:
        log_entry["status"] = f"error: {e}"
        return {"received": True, "action": "error", "reason": str(e)}

    changes = detect_changes(old_metadata, new_metadata)

    if not changes["has_changes"]:
        log_entry["status"] = "no changes detected"
        return {"received": True, "action": "no_changes"}

    store.save_metadata(dataset_id, new_metadata)
    store.save_version(dataset_id, new_metadata, changes)

    narrative = generate_diff_narrative(old_metadata, new_metadata, changes)
    docs_to_regen = changes.get("docs_to_regenerate", [])
    log_entry["docs_regenerated"] = docs_to_regen
    log_entry["status"] = "regenerating in background"

    # Regenerate affected docs without blocking the response
    background_tasks.add_task(_do_regeneration, dataset_id, docs_to_regen, new_metadata)

    return {
        "received"        : True,
        "action"          : "regenerating",
        "change_count"    : changes["change_count"],
        "changes_summary" : format_diff_for_display(changes),
        "narrative"       : narrative,
        "docs_to_regen"   : docs_to_regen,
        "delivery_id"     : delivery_id,
    }


@app.get("/webhook/log")
def get_webhook_log():
    """See all webhook events received — useful for demo / debugging."""
    return {"events": list(reversed(WEBHOOK_LOG)), "total": len(WEBHOOK_LOG)}


@app.delete("/webhook/log")
def clear_webhook_log():
    WEBHOOK_LOG.clear()
    return {"cleared": True}
