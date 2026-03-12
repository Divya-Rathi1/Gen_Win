# core/ai_client.py
# ─────────────────────────────────────────────────────────────────────────────
# Azure OpenAI client — handles all GPT-4o calls for document generation,
# chat Q&A, audit scoring, and change narratives
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
from openai import AzureOpenAI
from prompts import (
    brd_prompt, tdd_prompt, fdd_prompt,
    s2t_prompt, qa_report_prompt, audit_score_prompt,
    chat_prompt, diff_narrative_prompt,
)


def _get_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )


def _call(system: str, user: str, temperature: float = 0.3, max_tokens: int = 3000) -> str:
    """Core GPT-4o call. Returns the text content."""
    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _call_with_history(system: str, history: list[dict], user_message: str) -> str:
    """GPT-4o call with full conversation history for multi-turn chat."""
    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=0.4,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()


# ─── Document generators ────────────────────────────────────────────────────

def generate_brd(metadata: dict) -> str:
    system, user = brd_prompt(metadata)
    return _call(system, user, temperature=0.4, max_tokens=3000)


def generate_tdd(metadata: dict) -> str:
    system, user = tdd_prompt(metadata)
    return _call(system, user, temperature=0.2, max_tokens=3500)


def generate_fdd(metadata: dict) -> str:
    system, user = fdd_prompt(metadata)
    return _call(system, user, temperature=0.3, max_tokens=2800)


def generate_s2t(metadata: dict) -> str:
    system, user = s2t_prompt(metadata)
    return _call(system, user, temperature=0.1, max_tokens=2500)


def generate_qa_report(metadata: dict, validation_results: dict | None = None) -> str:
    system, user = qa_report_prompt(metadata, validation_results)
    return _call(system, user, temperature=0.2, max_tokens=2500)


def generate_audit_score(metadata: dict, generated_docs: dict) -> dict:
    """Returns structured JSON with scores, gaps, risks, recommendations."""
    system, user = audit_score_prompt(metadata, generated_docs)
    raw = _call(system, user, temperature=0.1, max_tokens=1500)
    # Strip any accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_score": 0,
            "grade": "F",
            "categories": {},
            "top_risks": ["Could not parse audit score"],
            "recommendations": [],
            "raw": raw,
        }


def generate_diff_narrative(old_metadata: dict, new_metadata: dict, diff_summary: dict) -> str:
    system, user = diff_narrative_prompt(old_metadata, new_metadata, diff_summary)
    return _call(system, user, temperature=0.3, max_tokens=1000)


# ─── Chat Q&A ───────────────────────────────────────────────────────────────

def chat_with_metadata(metadata: dict, conversation_history: list[dict], question: str) -> str:
    """
    RAG-style Q&A — metadata is injected into system prompt as context.
    For prototype: context-window approach (no vector DB needed).
    conversation_history = [{"role": "user"/"assistant", "content": "..."}]
    """
    system, _ = chat_prompt(metadata, conversation_history, question)
    # Keep last 6 turns to avoid token overflow
    trimmed_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    return _call_with_history(system, trimmed_history, question)


# ─── Batch: generate all docs at once ───────────────────────────────────────

def generate_all_documents(metadata: dict) -> dict:
    """
    Generate all 5 document types + audit score in one call.
    Returns dict with doc type keys.
    Streams results as they complete (good for Streamlit progress bars).
    """
    results = {}

    results["brd"] = generate_brd(metadata)
    results["tdd"] = generate_tdd(metadata)
    results["fdd"] = generate_fdd(metadata)
    results["s2t"] = generate_s2t(metadata)
    results["qa_report"] = generate_qa_report(metadata)

    # Audit score uses doc completion status
    doc_status = {k: bool(v) for k, v in results.items()}
    results["audit_score"] = generate_audit_score(metadata, doc_status)

    return results
