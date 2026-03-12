# AutoDocAI — Prototype Setup Guide

## Project Structure
```
autodocai/
├── main.py              # FastAPI backend (all API endpoints)
├── app.py               # Streamlit frontend (full UI)
├── requirements.txt     # Python dependencies
├── .env.example         # Config template → copy to .env
│
├── prompts/
│   ├── __init__.py
│   └── templates.py     # ALL GPT-4o prompt templates
│
└── core/
    ├── __init__.py
    ├── pbi_connector.py  # Power BI REST API (no MSAL — raw token)
    ├── ai_client.py      # Azure OpenAI calls for all doc types
    ├── change_detector.py# Metadata diffing + version tracking
    ├── doc_exporter.py   # Word (.docx) + PDF generation
    └── session_store.py  # In-memory storage (no DB needed)
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env — fill in Azure OpenAI key + endpoint
```

### 3. Start the backend
```bash
python main.py
# → http://localhost:8000
# → API docs at http://localhost:8000/docs
```

### 4. Start the Streamlit UI (new terminal)
```bash
streamlit run app.py
# → http://localhost:8501
```

## Getting Your Power BI Token (No MSAL)
1. Open [app.powerbi.com](https://app.powerbi.com) in Chrome
2. Press **F12** → Network tab
3. Click on any report/dataset in PBI
4. In Network: find request to `api.powerbi.com`
5. Headers → copy `Authorization: Bearer <token>`
6. Paste into the Connect page (valid ~1 hour)

## Features

| Feature | Module | Endpoint |
|---|---|---|
| Connect PBI dataset | pbi_connector.py | POST /connect |
| Generate BRD | ai_client.py + prompts | POST /generate/brd |
| Generate TDD | ai_client.py + prompts | POST /generate/tdd |
| Generate FDD | ai_client.py + prompts | POST /generate/fdd |
| Generate S2T Mapping | ai_client.py + prompts | POST /generate/s2t |
| Generate QA Report | ai_client.py + prompts | POST /generate/qa_report |
| Generate ALL at once | ai_client.py | POST /generate/all |
| Audit-readiness score | ai_client.py + prompts | POST /generate/audit_score |
| Chat Q&A (RAG) | ai_client.py + prompts | POST /chat |
| Change detection | change_detector.py | POST /diff/{dataset_id} |
| Auto-regenerate changed docs | main.py | POST /regenerate |
| Version history | session_store.py | GET /versions/{dataset_id} |
| Export Word | doc_exporter.py | GET /export/{id}/{type}?fmt=word |
| Export PDF | doc_exporter.py | GET /export/{id}/{type}?fmt=pdf |
| Export all as ZIP | doc_exporter.py | GET /export/{id}/all/zip |

## Notes
- All storage is **in-memory** — resets on restart (fine for prototype)
- No MSAL / Azure AD auth — just paste the Bearer token
- RAG uses context-window injection (no vector DB needed for prototype)
- Change detection uses DeepDiff + metadata hash comparison
