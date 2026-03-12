# # app.py  —  AutoDocAI Streamlit Prototype
# # ─────────────────────────────────────────────────────────────────────────────
# # Run with: streamlit run app.py
# # This calls the FastAPI backend at localhost:8000
# # Start backend first: python main.py
# # ─────────────────────────────────────────────────────────────────────────────

# import streamlit as st
# import requests
# import json
# import time
# from datetime import datetime

# API = "http://localhost:8000"

# st.set_page_config(
#     page_title="AutoDocAI",
#     page_icon="📄",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # ─── Styles ──────────────────────────────────────────────────────────────────
# st.markdown("""
# <style>
#     .main-header { font-size: 2.2rem; font-weight: 800; color: #C0392B; margin-bottom: 0; }
#     .sub-header  { font-size: 1rem; color: #64748B; margin-top: 0; margin-bottom: 1.5rem; }
#     .metric-card { background: #F4F6F8; border-left: 4px solid #C0392B;
#                    padding: 0.8rem 1rem; border-radius: 4px; margin-bottom: 0.5rem; }
#     .doc-card    { background: #fff; border: 1px solid #E2E8F0; border-radius: 8px;
#                    padding: 1rem; margin-bottom: 1rem; }
#     .score-high  { color: #16A34A; font-weight: 800; font-size: 2rem; }
#     .score-mid   { color: #EA580C; font-weight: 800; font-size: 2rem; }
#     .score-low   { color: #C0392B; font-weight: 800; font-size: 2rem; }
#     .change-add  { color: #16A34A; }
#     .change-rem  { color: #C0392B; }
#     .change-mod  { color: #EA580C; }
#     .chat-user   { background: #EFF6FF; padding: 0.6rem 1rem; border-radius: 8px; margin: 4px 0; }
#     .chat-bot    { background: #F4F6F8; padding: 0.6rem 1rem; border-radius: 8px; margin: 4px 0; }
#     .stButton > button { background-color: #C0392B !important; color: white !important;
#                          border: none !important; font-weight: 600 !important; }
# </style>
# """, unsafe_allow_html=True)


# # ─── Session state init ──────────────────────────────────────────────────────
# for key in ["connected", "dataset_id", "dataset_name", "token",
#             "docs", "audit_score", "chat_history", "versions", "diff_result"]:
#     if key not in st.session_state:
#         st.session_state[key] = None if key not in ["connected"] else False


# def api_post(endpoint: str, **kwargs):
#     try:
#         r = requests.post(f"{API}{endpoint}", **kwargs, timeout=120)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot reach backend. Start it with: `python main.py`")
#         return None
#     except Exception as e:
#         st.error(f"API error: {e}")
#         return None


# def api_get(endpoint: str, **kwargs):
#     try:
#         r = requests.get(f"{API}{endpoint}", **kwargs, timeout=60)
#         r.raise_for_status()
#         return r.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot reach backend. Start it with: `python main.py`")
#         return None
#     except Exception as e:
#         st.error(f"API error: {e}")
#         return None


# # ─── Sidebar ─────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.markdown('<div class="main-header">AutoDocAI</div>', unsafe_allow_html=True)
#     st.markdown('<div class="sub-header">Automated Documentation for Data Projects</div>', unsafe_allow_html=True)

#     st.divider()

#     # Navigation
#     page = st.radio(
#         "Navigate",
#         ["🔌 Connect", "📄 Generate Docs", "💬 Chat Q&A",
#          "🔍 Change Detector", "📊 Audit Score", "📜 Version History"],
#         label_visibility="collapsed",
#     )

#     st.divider()

#     # Session status
#     if st.session_state.connected:
#         st.success(f"✅ Connected")
#         st.caption(f"**Dataset:** {st.session_state.dataset_name}")
#         if st.session_state.docs:
#             doc_count = len([k for k in st.session_state.docs if not k.startswith("_") and k != "audit_score"])
#             st.caption(f"**Docs generated:** {doc_count}")
#         if st.session_state.audit_score:
#             score = st.session_state.audit_score.get("overall_score", 0)
#             grade = st.session_state.audit_score.get("grade", "?")
#             st.caption(f"**Audit score:** {score}/100 ({grade})")
#     else:
#         st.warning("⚠️ Not connected")
#         st.caption("Go to Connect tab first")

#     st.divider()
#     st.caption("AutoDocAI Prototype  •  iLink Digital")


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: CONNECT
# # ─────────────────────────────────────────────────────────────────────────────
# if "Connect" in page:
#     st.header("🔌 Connect to Power BI")
#     st.caption("Provide your Power BI Bearer token and dataset details to pull metadata.")

#     with st.expander("📖 How to get your Bearer token", expanded=False):
#         st.markdown("""
# 1. Open [app.powerbi.com](https://app.powerbi.com) in Chrome
# 2. Press **F12** → go to **Network** tab
# 3. Click on any dataset or workspace in the UI
# 4. In Network tab, find any request to `api.powerbi.com`
# 5. Click the request → **Headers** → find `Authorization: Bearer <token>`
# 6. Copy everything after `Bearer ` — that's your token
# 7. Token is valid for ~1 hour
#         """)

#     col1, col2 = st.columns(2)

#     with col1:
#         token = st.text_input(
#             "Bearer Token",
#             type="password",
#             placeholder="Paste your Power BI Bearer token here",
#             value=st.session_state.token or "",
#         )

#     with col2:
#         workspace_id = st.text_input(
#             "Workspace ID (optional)",
#             placeholder="Leave blank for My Workspace",
#         )

#     if token:
#         if st.button("🔍 Browse Workspaces & Datasets"):
#             with st.spinner("Fetching workspaces..."):
#                 ws_data = api_get("/pbi/workspaces", params={"token": token})
#                 if ws_data:
#                     workspaces = ws_data.get("workspaces", [])
#                     if workspaces:
#                         st.success(f"Found {len(workspaces)} workspaces")
#                         for ws in workspaces[:10]:
#                             st.caption(f"• **{ws.get('name')}** — ID: `{ws.get('id')}`")
#                     else:
#                         st.info("No group workspaces found. You may only have 'My Workspace'.")

#     st.divider()

#     col3, col4 = st.columns(2)
#     with col3:
#         dataset_id = st.text_input("Dataset ID *", placeholder="e.g. f1234abc-...")
#     with col4:
#         dataset_name = st.text_input("Dataset Name *", placeholder="e.g. Sales Analytics")

#     workspace_name = st.text_input("Workspace Name", value="My Workspace")

#     if st.button("🔌 Connect & Pull Metadata", use_container_width=True):
#         if not token or not dataset_id or not dataset_name:
#             st.error("Token, Dataset ID, and Dataset Name are required.")
#         else:
#             with st.spinner("Connecting to Power BI and pulling metadata..."):
#                 result = api_post(
#                     "/connect",
#                     json={
#                         "token": token,
#                         "dataset_id": dataset_id,
#                         "dataset_name": dataset_name,
#                         "workspace_id": workspace_id or None,
#                         "workspace_name": workspace_name,
#                     }
#                 )

#             if result and result.get("success"):
#                 st.session_state.connected = True
#                 st.session_state.dataset_id = dataset_id
#                 st.session_state.dataset_name = dataset_name
#                 st.session_state.token = token

#                 st.success("✅ Connected successfully!")

#                 col_a, col_b, col_c = st.columns(3)
#                 col_a.metric("Tables", result["table_count"])
#                 col_b.metric("Measures", result["measure_count"])
#                 col_c.metric("Relationships", result["relationship_count"])

#                 st.caption(f"Metadata hash: `{result['metadata_hash'][:16]}...`")
#                 st.caption(f"Version: **{result['version']}**")

#                 if result.get("has_previous_version"):
#                     st.info("📌 Previous version detected — go to **Change Detector** to see what changed.")


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: GENERATE DOCS
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Generate" in page:
#     st.header("📄 Generate Documents")

#     if not st.session_state.connected:
#         st.warning("Connect to a dataset first.")
#         st.stop()

#     st.caption(f"Dataset: **{st.session_state.dataset_name}**")

#     col1, col2 = st.columns([2, 1])
#     with col1:
#         if st.button("⚡ Generate ALL Documents", use_container_width=True):
#             progress = st.progress(0, text="Starting generation...")
#             docs_result = None

#             with st.spinner("Generating all 5 documents + audit score..."):
#                 progress.progress(10, text="Calling AI engine...")
#                 docs_result = api_get("/generate/all", params={"dataset_id": st.session_state.dataset_id})
#                 progress.progress(100, text="Complete!")

#             if docs_result and docs_result.get("success"):
#                 st.session_state.docs = docs_result["docs"]
#                 st.session_state.audit_score = docs_result.get("audit")
#                 st.success(f"✅ Generated {len(docs_result['docs_generated'])} documents!")
#                 st.metric("Audit Score", f"{docs_result['audit_score']}/100 ({docs_result['audit_grade']})")

#     with col2:
#         st.caption("Or generate individually:")
#         for doc_type, label in [("brd", "BRD"), ("tdd", "TDD"), ("fdd", "FDD"), ("s2t", "S2T Map"), ("qa_report", "QA Report")]:
#             if st.button(f"Generate {label}"):
#                 with st.spinner(f"Generating {label}..."):
#                     r = api_post(f"/generate/{doc_type}", params={"dataset_id": st.session_state.dataset_id})
#                 if r and r.get("success"):
#                     if not st.session_state.docs:
#                         st.session_state.docs = {}
#                     st.session_state.docs[doc_type] = r["content"]
#                     st.success(f"✅ {label} generated!")

#     # Display generated docs
#     if st.session_state.docs:
#         st.divider()
#         st.subheader("📂 Generated Documents")

#         DOC_LABELS = {
#             "brd": "📋 Business Requirements Document",
#             "tdd": "⚙️ Technical Design Document",
#             "fdd": "🗂️ Functional Design Document",
#             "s2t": "🔁 Source-to-Target Mapping",
#             "qa_report": "✅ QA Validation Report",
#         }

#         tabs = st.tabs([DOC_LABELS.get(k, k) for k in st.session_state.docs.keys()
#                         if not k.startswith("_") and k != "audit_score" and isinstance(st.session_state.docs[k], str)])

#         doc_items = [(k, v) for k, v in st.session_state.docs.items()
#                      if not k.startswith("_") and k != "audit_score" and isinstance(v, str)]

#         for tab, (doc_type, content) in zip(tabs, doc_items):
#             with tab:
#                 st.text_area("", value=content, height=400, key=f"doc_{doc_type}", label_visibility="collapsed")

#                 col_w, col_p, col_z = st.columns(3)
#                 with col_w:
#                     word_bytes = requests.get(
#                         f"{API}/export/{st.session_state.dataset_id}/{doc_type}",
#                         params={"fmt": "word"}
#                     ).content
#                     st.download_button(
#                         f"⬇️ Download Word",
#                         data=word_bytes,
#                         file_name=f"{doc_type}_{st.session_state.dataset_name}.docx",
#                         mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#                         key=f"word_{doc_type}",
#                     )
#                 with col_p:
#                     pdf_bytes = requests.get(
#                         f"{API}/export/{st.session_state.dataset_id}/{doc_type}",
#                         params={"fmt": "pdf"}
#                     ).content
#                     st.download_button(
#                         f"⬇️ Download PDF",
#                         data=pdf_bytes,
#                         file_name=f"{doc_type}_{st.session_state.dataset_name}.pdf",
#                         mime="application/pdf",
#                         key=f"pdf_{doc_type}",
#                     )

#         st.divider()
#         col_zip1, col_zip2 = st.columns(2)
#         with col_zip1:
#             zip_bytes = requests.get(f"{API}/export/{st.session_state.dataset_id}/all/zip", params={"fmt": "word"}).content
#             st.download_button("⬇️ Download ALL as Word ZIP", data=zip_bytes,
#                                file_name=f"AutoDocAI_{st.session_state.dataset_name}_word.zip",
#                                mime="application/zip")
#         with col_zip2:
#             zip_bytes_pdf = requests.get(f"{API}/export/{st.session_state.dataset_id}/all/zip", params={"fmt": "pdf"}).content
#             st.download_button("⬇️ Download ALL as PDF ZIP", data=zip_bytes_pdf,
#                                file_name=f"AutoDocAI_{st.session_state.dataset_name}_pdf.zip",
#                                mime="application/zip")


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: CHAT Q&A
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Chat" in page:
#     st.header("💬 Chat with Your Data Model")

#     if not st.session_state.connected:
#         st.warning("Connect to a dataset first.")
#         st.stop()

#     st.caption(f"Ask anything about **{st.session_state.dataset_name}** — powered by metadata context")

#     # Suggested questions
#     st.subheader("💡 Suggested questions")
#     suggestions = [
#         f"What tables are in this model?",
#         f"What does the largest table contain?",
#         f"Explain the key measures and what they calculate",
#         f"What are the relationships between tables?",
#         f"Which tables are fact tables and which are dimensions?",
#         f"What data sources feed into this model?",
#     ]
#     cols = st.columns(3)
#     for i, sug in enumerate(suggestions):
#         if cols[i % 3].button(sug, key=f"sug_{i}"):
#             st.session_state._pending_question = sug

#     st.divider()

#     # Chat history display
#     if st.session_state.chat_history:
#         st.subheader("Conversation")
#         for msg in st.session_state.chat_history:
#             if msg["role"] == "user":
#                 st.markdown(f'<div class="chat-user">👤 **You:** {msg["content"]}</div>', unsafe_allow_html=True)
#             else:
#                 st.markdown(f'<div class="chat-bot">🤖 **AutoDocAI:** {msg["content"]}</div>', unsafe_allow_html=True)

#     # Input
#     question = st.text_input(
#         "Ask a question",
#         placeholder="e.g. What does the Sales_Fact table contain?",
#         value=getattr(st.session_state, "_pending_question", ""),
#         key="chat_input",
#     )
#     if hasattr(st.session_state, "_pending_question"):
#         del st.session_state._pending_question

#     col_ask, col_clear = st.columns([3, 1])
#     with col_ask:
#         ask_clicked = st.button("Ask", use_container_width=True)
#     with col_clear:
#         if st.button("Clear chat"):
#             requests.delete(f"{API}/chat/{st.session_state.dataset_id}/clear")
#             st.session_state.chat_history = []
#             st.rerun()

#     if ask_clicked and question:
#         with st.spinner("Thinking..."):
#             result = api_post("/chat", json={
#                 "question": question,
#                 "dataset_id": st.session_state.dataset_id,
#             })

#         if result:
#             if not st.session_state.chat_history:
#                 st.session_state.chat_history = []
#             st.session_state.chat_history.append({"role": "user", "content": question})
#             st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
#             st.rerun()


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: CHANGE DETECTOR
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Change" in page:
#     st.header("🔍 Change Detector")

#     if not st.session_state.connected:
#         st.warning("Connect to a dataset first.")
#         st.stop()

#     st.caption("Re-pull metadata from Power BI and compare against the saved version to detect changes.")
#     st.info("💡 In production: this runs automatically via Git/DevOps webhooks on every deploy.")

#     token_for_diff = st.text_input(
#         "Bearer Token (for re-pull)",
#         type="password",
#         value=st.session_state.token or "",
#     )

#     if st.button("🔄 Check for Changes", use_container_width=True):
#         if not token_for_diff:
#             st.error("Provide your token to re-pull metadata.")
#         else:
#             with st.spinner("Re-pulling metadata and comparing versions..."):
#                 result = api_post(
#                     f"/diff/{st.session_state.dataset_id}",
#                     params={"token": token_for_diff},
#                 )

#             if result:
#                 st.session_state.diff_result = result

#     if st.session_state.diff_result:
#         diff = st.session_state.diff_result

#         if not diff["has_changes"]:
#             st.success("✅ No changes detected — all documents are up to date.")
#         else:
#             st.warning(f"⚠️ {diff['change_count']} changes detected!")

#             # Display changes
#             st.subheader("What Changed")
#             st.markdown(diff["display_summary"])

#             # AI narrative
#             if diff.get("narrative"):
#                 st.subheader("📝 AI Change Narrative")
#                 st.markdown(diff["narrative"])

#             # Docs to regenerate
#             if diff.get("docs_to_regenerate"):
#                 st.subheader("📄 Documents Needing Regeneration")
#                 st.write(", ".join([d.upper() for d in diff["docs_to_regenerate"]]))

#                 if st.button("⚡ Regenerate Affected Documents"):
#                     with st.spinner("Regenerating..."):
#                         regen_result = api_post(
#                             "/regenerate",
#                             json={
#                                 "dataset_id": st.session_state.dataset_id,
#                                 "doc_types": diff["docs_to_regenerate"],
#                             }
#                         )
#                     if regen_result and regen_result.get("success"):
#                         # Merge updated docs
#                         if not st.session_state.docs:
#                             st.session_state.docs = {}
#                         st.session_state.docs.update(regen_result.get("docs", {}))
#                         st.success(f"✅ Regenerated: {', '.join(regen_result['regenerated'])}")


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: AUDIT SCORE
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Audit" in page:
#     st.header("📊 Audit-Readiness Score")

#     if not st.session_state.connected:
#         st.warning("Connect to a dataset first.")
#         st.stop()

#     if not st.session_state.audit_score:
#         st.info("Generate all documents first to compute the audit score.")
#         if st.button("Generate Audit Score Now"):
#             with st.spinner("Computing audit score..."):
#                 result = api_post(f"/generate/audit_score", params={"dataset_id": st.session_state.dataset_id})
#             if result and result.get("success"):
#                 st.session_state.audit_score = result.get("audit")
#                 st.rerun()
#     else:
#         audit = st.session_state.audit_score
#         score = audit.get("overall_score", 0)
#         grade = audit.get("grade", "?")

#         # Overall score
#         score_class = "score-high" if score >= 75 else ("score-mid" if score >= 50 else "score-low")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.markdown(f'<div class="metric-card"><div class="{score_class}">{score}/100</div><div>Overall Score</div></div>', unsafe_allow_html=True)
#         with col2:
#             st.markdown(f'<div class="metric-card"><div class="{score_class}">{grade}</div><div>Grade</div></div>', unsafe_allow_html=True)
#         with col3:
#             st.markdown(f'<div class="metric-card"><div style="font-size:1.5rem;font-weight:700">{st.session_state.dataset_name}</div><div>Dataset</div></div>', unsafe_allow_html=True)

#         # Category scores
#         st.subheader("Category Breakdown")
#         categories = audit.get("categories", {})
#         for cat_key, cat_data in categories.items():
#             cat_score = cat_data.get("score", 0)
#             label = cat_key.replace("_", " ").title()
#             col_l, col_b, col_s = st.columns([2, 5, 1])
#             with col_l:
#                 st.caption(label)
#             with col_b:
#                 color = "green" if cat_score >= 75 else ("orange" if cat_score >= 50 else "red")
#                 st.progress(cat_score / 100)
#             with col_s:
#                 st.caption(f"**{cat_score}**")

#             if cat_data.get("gaps"):
#                 with st.expander(f"Gaps in {label}"):
#                     for gap in cat_data["gaps"]:
#                         st.caption(f"⚠️ {gap}")

#         # Risks and recommendations
#         col_r, col_rec = st.columns(2)
#         with col_r:
#             st.subheader("🚨 Top Risks")
#             for risk in audit.get("top_risks", []):
#                 st.markdown(f"- 🔴 {risk}")
#         with col_rec:
#             st.subheader("✅ Recommendations")
#             for rec in audit.get("recommendations", []):
#                 st.markdown(f"- 💡 {rec}")


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: VERSION HISTORY
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Version" in page:
#     st.header("📜 Version History")

#     if not st.session_state.connected:
#         st.warning("Connect to a dataset first.")
#         st.stop()

#     versions_data = api_get(f"/versions/{st.session_state.dataset_id}")

#     if versions_data:
#         versions = versions_data.get("versions", [])
#         if not versions:
#             st.info("No version history yet. Connect the dataset at least twice to see history.")
#         else:
#             st.caption(f"{len(versions)} version(s) recorded for **{st.session_state.dataset_name}**")

#             for v in reversed(versions):
#                 is_latest = v["version"] == versions[-1]["version"]
#                 badge = "🟢 **LATEST**" if is_latest else "🔵"
#                 with st.expander(f"{badge} {v['version']} — {v['timestamp'][:16].replace('T', ' ')}"):
#                     col1, col2, col3 = st.columns(3)
#                     col1.metric("Tables", v["table_count"])
#                     col2.metric("Measures", v["measure_count"])
#                     col3.metric("Changes from prev", v.get("change_count", 0))


# # ─────────────────────────────────────────────────────────────────────────────
# # PAGE: WEBHOOK LOG
# # ─────────────────────────────────────────────────────────────────────────────
# elif "Webhook" in page:
#     st.header("🔗 GitHub Webhook Log")
#     st.caption("Live log of every GitHub push event received by AutoDocAI.")

#     with st.expander("📖 Setup Instructions", expanded=not st.session_state.connected):
#         st.markdown("""
# ### Step 1 — Make your server public with ngrok
# ```bash
# # Install
# pip install pyngrok
# # OR download from https://ngrok.com

# # Run (in a new terminal, while main.py is running)
# ngrok http 8000

# # You'll see something like:
# # Forwarding  https://abc123.ngrok-free.app → localhost:8000
# # Copy that https URL
# ```

# ### Step 2 — Add webhook in GitHub
# 1. Go to your GitHub repo
# 2. **Settings** → **Webhooks** → **Add webhook**
# 3. Fill in:
#    - **Payload URL**: `https://abc123.ngrok-free.app/webhook/github`
#    - **Content type**: `application/json`
#    - **Secret**: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
#    - **Which events**: ✅ Just the **push** event
# 4. Click **Add webhook** — GitHub will send a ping immediately to test it

# ### Step 3 — Add to your .env
# ```
# GITHUB_WEBHOOK_SECRET=your_secret_here
# POWERBI_WEBHOOK_TOKEN=your_pbi_bearer_token
# ```

# ### What happens on every push
# ```
# git push origin main
#       ↓
# GitHub → POST /webhook/github
#       ↓
# AutoDocAI re-pulls PBI metadata
#       ↓
# Detects what changed (tables / measures / relationships)
#       ↓
# Regenerates only the affected documents
#       ↓
# Docs updated in the app automatically
# ```
#         """)

#     col_r, col_c = st.columns([1, 1])
#     with col_r:
#         if st.button("🔄 Refresh Log"):
#             st.rerun()
#     with col_c:
#         if st.button("🗑️ Clear Log"):
#             requests.delete(f"{API}/webhook/log")
#             st.rerun()

#     log_data = api_get("/webhook/log")
#     if log_data:
#         events = log_data.get("events", [])
#         total  = log_data.get("total", 0)

#         if not events:
#             st.info("No webhook events received yet. Push to GitHub after setup to see events here.")
#         else:
#             st.success(f"**{total}** webhook event(s) received")
#             for ev in events:
#                 status = ev.get("status", "")
#                 icon = (
#                     "✅" if "regenerat" in status else
#                     "⚠️" if "skipped"   in status else
#                     "❌" if "error"     in status else
#                     "ℹ️"
#                 )
#                 label = (
#                     f"{icon} **{ev['event_type'].upper()}** — "
#                     f"{ev.get('repository','?')} — "
#                     f"{ev.get('timestamp','')[:16].replace('T',' ')}"
#                 )
#                 with st.expander(label):
#                     col1, col2, col3, col4 = st.columns(4)
#                     col1.metric("Pusher",  ev.get("pusher", "?"))
#                     col2.metric("Commits", ev.get("commits", 0))
#                     col3.metric("Branch",  ev.get("ref","").replace("refs/heads/",""))
#                     col4.metric("Status",  status[:20])

#                     if ev.get("docs_regenerated"):
#                         st.write("**Docs regenerated:**", ", ".join(ev["docs_regenerated"]).upper())
#                     st.caption(f"Delivery ID: `{ev.get('delivery_id','?')}`")









# app.py  —  AutoDocAI Streamlit Prototype
# ─────────────────────────────────────────────────────────────────────────────
# Run with: streamlit run app.py
# This calls the FastAPI backend at localhost:8000
# Start backend first: python main.py
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import json
import time
from datetime import datetime

API = "http://localhost:8000"

st.set_page_config(
    page_title="AutoDocAI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 800; color: #C0392B; margin-bottom: 0; }
    .sub-header  { font-size: 1rem; color: #64748B; margin-top: 0; margin-bottom: 1.5rem; }
    .metric-card { background: #F4F6F8; border-left: 4px solid #C0392B;
                   padding: 0.8rem 1rem; border-radius: 4px; margin-bottom: 0.5rem; }
    .doc-card    { background: #fff; border: 1px solid #E2E8F0; border-radius: 8px;
                   padding: 1rem; margin-bottom: 1rem; }
    .score-high  { color: #16A34A; font-weight: 800; font-size: 2rem; }
    .score-mid   { color: #EA580C; font-weight: 800; font-size: 2rem; }
    .score-low   { color: #C0392B; font-weight: 800; font-size: 2rem; }
    .change-add  { color: #16A34A; }
    .change-rem  { color: #C0392B; }
    .change-mod  { color: #EA580C; }
    .chat-user   { background: #EFF6FF; padding: 0.6rem 1rem; border-radius: 8px; margin: 4px 0; }
    .chat-bot    { background: #F4F6F8; padding: 0.6rem 1rem; border-radius: 8px; margin: 4px 0; }
    .stButton > button { background-color: #C0392B !important; color: white !important;
                         border: none !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Session state init ──────────────────────────────────────────────────────
for key in ["connected", "dataset_id", "dataset_name", "token",
            "docs", "audit_score", "chat_history", "versions", "diff_result"]:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ["connected"] else False


def api_post(endpoint: str, **kwargs):
    try:
        r = requests.post(f"{API}{endpoint}", **kwargs, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach backend. Start it with: `python main.py`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_get(endpoint: str, **kwargs):
    try:
        r = requests.get(f"{API}{endpoint}", **kwargs, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach backend. Start it with: `python main.py`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-header">AutoDocAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated Documentation for Data Projects</div>', unsafe_allow_html=True)

    st.divider()

    # Navigation
    page = st.radio(
        "Navigate",
        ["🔌 Connect", "📄 Generate Docs", "💬 Chat Q&A",
         "🔍 Change Detector", "📊 Audit Score", "📜 Version History"],
        label_visibility="collapsed",
    )

    st.divider()

    # Session status
    if st.session_state.connected:
        st.success(f"✅ Connected")
        st.caption(f"**Dataset:** {st.session_state.dataset_name}")
        if st.session_state.docs:
            doc_count = len([k for k in st.session_state.docs if not k.startswith("_") and k != "audit_score"])
            st.caption(f"**Docs generated:** {doc_count}")
        if st.session_state.audit_score:
            score = st.session_state.audit_score.get("overall_score", 0)
            grade = st.session_state.audit_score.get("grade", "?")
            st.caption(f"**Audit score:** {score}/100 ({grade})")
    else:
        st.warning("⚠️ Not connected")
        st.caption("Go to Connect tab first")

    st.divider()
    st.caption("AutoDocAI Prototype  •  iLink Digital")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CONNECT
# ─────────────────────────────────────────────────────────────────────────────
if "Connect" in page:
    st.header("🔌 Connect to Power BI")
    st.caption("Provide your Power BI Bearer token and dataset details to pull metadata.")

    with st.expander("📖 How to get your Bearer token", expanded=False):
        st.markdown("""
1. Open [app.powerbi.com](https://app.powerbi.com) in Chrome
2. Press **F12** → go to **Network** tab
3. Click on any dataset or workspace in the UI
4. In Network tab, find any request to `api.powerbi.com`
5. Click the request → **Headers** → find `Authorization: Bearer <token>`
6. Copy everything after `Bearer ` — that's your token
7. Token is valid for ~1 hour
        """)

    col1, col2 = st.columns(2)

    with col1:
        token = st.text_input(
            "Bearer Token",
            type="password",
            placeholder="Paste your Power BI Bearer token here",
            value=st.session_state.token or "",
        )

    with col2:
        workspace_id = st.text_input(
            "Workspace ID (optional)",
            placeholder="Leave blank for My Workspace",
        )

    if token:
        if st.button("🔍 Browse Workspaces & Datasets"):
            with st.spinner("Fetching workspaces and datasets..."):
                ws_data = api_get("/pbi/workspaces", params={"token": token})
                if ws_data:
                    workspaces = ws_data.get("workspaces", [])
                    if workspaces:
                        st.success(f"Found {len(workspaces)} workspaces")
                        for ws in workspaces[:10]:
                            ws_id   = ws.get("id")
                            ws_name = ws.get("name")
                            st.markdown(f"**📁 {ws_name}**")
                            st.code(f"Workspace ID: {ws_id}", language=None)
                            ds_data = api_get("/pbi/datasets", params={"token": token, "workspace_id": ws_id})
                            if ds_data:
                                datasets = ds_data.get("datasets", [])
                                if datasets:
                                    for ds in datasets:
                                        st.markdown(f"&nbsp;&nbsp;↳ 📊 **{ds.get('name')}**")
                                        st.code(f"Dataset ID: {ds.get('id')}", language=None)
                                else:
                                    st.caption("  (no datasets in this workspace)")
                    else:
                        st.info("No group workspaces found. Checking My Workspace...")
                        ds_data = api_get("/pbi/datasets", params={"token": token})
                        if ds_data:
                            for ds in ds_data.get("datasets", []):
                                st.markdown(f"📊 **{ds.get('name')}**")
                                st.code(f"Dataset ID: {ds.get('id')}", language=None)

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        dataset_id = st.text_input("Dataset ID *", placeholder="e.g. f1234abc-...")
    with col4:
        dataset_name = st.text_input("Dataset Name *", placeholder="e.g. Sales Analytics")

    workspace_name = st.text_input("Workspace Name", value="My Workspace")

    if st.button("🔌 Connect & Pull Metadata", use_container_width=True):
        if not token or not dataset_id or not dataset_name:
            st.error("Token, Dataset ID, and Dataset Name are required.")
        else:
            with st.spinner("Connecting to Power BI and pulling metadata..."):
                result = api_post(
                    "/connect",
                    json={
                        "token": token,
                        "dataset_id": dataset_id,
                        "dataset_name": dataset_name,
                        "workspace_id": workspace_id or None,
                        "workspace_name": workspace_name,
                    }
                )

            if result and result.get("success"):
                st.session_state.connected = True
                st.session_state.dataset_id = dataset_id
                st.session_state.dataset_name = dataset_name
                st.session_state.token = token

                st.success("✅ Connected successfully!")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Tables", result["table_count"])
                col_b.metric("Measures", result["measure_count"])
                col_c.metric("Relationships", result["relationship_count"])

                st.caption(f"Metadata hash: `{result['metadata_hash'][:16]}...`")
                st.caption(f"Version: **{result['version']}**")

                if result.get("has_previous_version"):
                    st.info("📌 Previous version detected — go to **Change Detector** to see what changed.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: GENERATE DOCS
# ─────────────────────────────────────────────────────────────────────────────
elif "Generate" in page:
    st.header("📄 Generate Documents")

    if not st.session_state.connected:
        st.warning("Connect to a dataset first.")
        st.stop()

    st.caption(f"Dataset: **{st.session_state.dataset_name}**")

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("⚡ Generate ALL Documents", use_container_width=True):
            progress = st.progress(0, text="Starting generation...")
            docs_result = None

            with st.spinner("Generating all 5 documents + audit score..."):
                progress.progress(10, text="Calling AI engine...")
                docs_result = api_get("/generate/all", params={"dataset_id": st.session_state.dataset_id})
                progress.progress(100, text="Complete!")

            if docs_result and docs_result.get("success"):
                st.session_state.docs = docs_result["docs"]
                st.session_state.audit_score = docs_result.get("audit")
                st.success(f"✅ Generated {len(docs_result['docs_generated'])} documents!")
                st.metric("Audit Score", f"{docs_result['audit_score']}/100 ({docs_result['audit_grade']})")

    with col2:
        st.caption("Or generate individually:")
        for doc_type, label in [("brd", "BRD"), ("tdd", "TDD"), ("fdd", "FDD"), ("s2t", "S2T Map"), ("qa_report", "QA Report")]:
            if st.button(f"Generate {label}"):
                with st.spinner(f"Generating {label}..."):
                    r = api_post(f"/generate/{doc_type}", params={"dataset_id": st.session_state.dataset_id})
                if r and r.get("success"):
                    if not st.session_state.docs:
                        st.session_state.docs = {}
                    st.session_state.docs[doc_type] = r["content"]
                    st.success(f"✅ {label} generated!")

    # Display generated docs
    if st.session_state.docs:
        st.divider()
        st.subheader("📂 Generated Documents")

        DOC_LABELS = {
            "brd": "📋 Business Requirements Document",
            "tdd": "⚙️ Technical Design Document",
            "fdd": "🗂️ Functional Design Document",
            "s2t": "🔁 Source-to-Target Mapping",
            "qa_report": "✅ QA Validation Report",
        }

        tabs = st.tabs([DOC_LABELS.get(k, k) for k in st.session_state.docs.keys()
                        if not k.startswith("_") and k != "audit_score" and isinstance(st.session_state.docs[k], str)])

        doc_items = [(k, v) for k, v in st.session_state.docs.items()
                     if not k.startswith("_") and k != "audit_score" and isinstance(v, str)]

        for tab, (doc_type, content) in zip(tabs, doc_items):
            with tab:
                st.text_area("", value=content, height=400, key=f"doc_{doc_type}", label_visibility="collapsed")

                col_w, col_p, col_z = st.columns(3)
                with col_w:
                    word_bytes = requests.get(
                        f"{API}/export/{st.session_state.dataset_id}/{doc_type}",
                        params={"fmt": "word"}
                    ).content
                    st.download_button(
                        f"⬇️ Download Word",
                        data=word_bytes,
                        file_name=f"{doc_type}_{st.session_state.dataset_name}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"word_{doc_type}",
                    )
                with col_p:
                    pdf_bytes = requests.get(
                        f"{API}/export/{st.session_state.dataset_id}/{doc_type}",
                        params={"fmt": "pdf"}
                    ).content
                    st.download_button(
                        f"⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"{doc_type}_{st.session_state.dataset_name}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{doc_type}",
                    )

        st.divider()
        col_zip1, col_zip2 = st.columns(2)
        with col_zip1:
            zip_bytes = requests.get(f"{API}/export/{st.session_state.dataset_id}/all/zip", params={"fmt": "word"}).content
            st.download_button("⬇️ Download ALL as Word ZIP", data=zip_bytes,
                               file_name=f"AutoDocAI_{st.session_state.dataset_name}_word.zip",
                               mime="application/zip")
        with col_zip2:
            zip_bytes_pdf = requests.get(f"{API}/export/{st.session_state.dataset_id}/all/zip", params={"fmt": "pdf"}).content
            st.download_button("⬇️ Download ALL as PDF ZIP", data=zip_bytes_pdf,
                               file_name=f"AutoDocAI_{st.session_state.dataset_name}_pdf.zip",
                               mime="application/zip")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CHAT Q&A
# ─────────────────────────────────────────────────────────────────────────────
elif "Chat" in page:
    st.header("💬 Chat with Your Data Model")

    if not st.session_state.connected:
        st.warning("Connect to a dataset first.")
        st.stop()

    st.caption(f"Ask anything about **{st.session_state.dataset_name}** — powered by metadata context")

    # Suggested questions
    st.subheader("💡 Suggested questions")
    suggestions = [
        f"What tables are in this model?",
        f"What does the largest table contain?",
        f"Explain the key measures and what they calculate",
        f"What are the relationships between tables?",
        f"Which tables are fact tables and which are dimensions?",
        f"What data sources feed into this model?",
    ]
    cols = st.columns(3)
    for i, sug in enumerate(suggestions):
        if cols[i % 3].button(sug, key=f"sug_{i}"):
            st.session_state._pending_question = sug

    st.divider()

    # Chat history display
    if st.session_state.chat_history:
        st.subheader("Conversation")
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">👤 **You:** {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🤖 **AutoDocAI:** {msg["content"]}</div>', unsafe_allow_html=True)

    # Input
    question = st.text_input(
        "Ask a question",
        placeholder="e.g. What does the Sales_Fact table contain?",
        value=getattr(st.session_state, "_pending_question", ""),
        key="chat_input",
    )
    if hasattr(st.session_state, "_pending_question"):
        del st.session_state._pending_question

    col_ask, col_clear = st.columns([3, 1])
    with col_ask:
        ask_clicked = st.button("Ask", use_container_width=True)
    with col_clear:
        if st.button("Clear chat"):
            requests.delete(f"{API}/chat/{st.session_state.dataset_id}/clear")
            st.session_state.chat_history = []
            st.rerun()

    if ask_clicked and question:
        with st.spinner("Thinking..."):
            result = api_post("/chat", json={
                "question": question,
                "dataset_id": st.session_state.dataset_id,
            })

        if result:
            if not st.session_state.chat_history:
                st.session_state.chat_history = []
            st.session_state.chat_history.append({"role": "user", "content": question})
            st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CHANGE DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
elif "Change" in page:
    st.header("🔍 Change Detector")

    if not st.session_state.connected:
        st.warning("Connect to a dataset first.")
        st.stop()

    st.caption("Re-pull metadata from Power BI and compare against the saved version to detect changes.")
    st.info("💡 In production: this runs automatically via Git/DevOps webhooks on every deploy.")

    token_for_diff = st.text_input(
        "Bearer Token (for re-pull)",
        type="password",
        value=st.session_state.token or "",
    )

    if st.button("🔄 Check for Changes", use_container_width=True):
        if not token_for_diff:
            st.error("Provide your token to re-pull metadata.")
        else:
            with st.spinner("Re-pulling metadata and comparing versions..."):
                result = api_post(
                    f"/diff/{st.session_state.dataset_id}",
                    params={"token": token_for_diff},
                )

            if result:
                st.session_state.diff_result = result

    if st.session_state.diff_result:
        diff = st.session_state.diff_result

        if not diff["has_changes"]:
            st.success("✅ No changes detected — all documents are up to date.")
        else:
            st.warning(f"⚠️ {diff['change_count']} changes detected!")

            # Display changes
            st.subheader("What Changed")
            st.markdown(diff["display_summary"])

            # AI narrative
            if diff.get("narrative"):
                st.subheader("📝 AI Change Narrative")
                st.markdown(diff["narrative"])

            # Docs to regenerate
            if diff.get("docs_to_regenerate"):
                st.subheader("📄 Documents Needing Regeneration")
                st.write(", ".join([d.upper() for d in diff["docs_to_regenerate"]]))

                if st.button("⚡ Regenerate Affected Documents"):
                    with st.spinner("Regenerating..."):
                        regen_result = api_post(
                            "/regenerate",
                            json={
                                "dataset_id": st.session_state.dataset_id,
                                "doc_types": diff["docs_to_regenerate"],
                            }
                        )
                    if regen_result and regen_result.get("success"):
                        # Merge updated docs
                        if not st.session_state.docs:
                            st.session_state.docs = {}
                        st.session_state.docs.update(regen_result.get("docs", {}))
                        st.success(f"✅ Regenerated: {', '.join(regen_result['regenerated'])}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: AUDIT SCORE
# ─────────────────────────────────────────────────────────────────────────────
elif "Audit" in page:
    st.header("📊 Audit-Readiness Score")

    if not st.session_state.connected:
        st.warning("Connect to a dataset first.")
        st.stop()

    if not st.session_state.audit_score:
        st.info("Generate all documents first to compute the audit score.")
        if st.button("Generate Audit Score Now"):
            with st.spinner("Computing audit score..."):
                result = api_post(f"/generate/audit_score", params={"dataset_id": st.session_state.dataset_id})
            if result and result.get("success"):
                st.session_state.audit_score = result.get("audit")
                st.rerun()
    else:
        audit = st.session_state.audit_score
        score = audit.get("overall_score", 0)
        grade = audit.get("grade", "?")

        # Overall score
        score_class = "score-high" if score >= 75 else ("score-mid" if score >= 50 else "score-low")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="{score_class}">{score}/100</div><div>Overall Score</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="{score_class}">{grade}</div><div>Grade</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div style="font-size:1.5rem;font-weight:700">{st.session_state.dataset_name}</div><div>Dataset</div></div>', unsafe_allow_html=True)

        # Category scores
        st.subheader("Category Breakdown")
        categories = audit.get("categories", {})
        for cat_key, cat_data in categories.items():
            cat_score = cat_data.get("score", 0)
            label = cat_key.replace("_", " ").title()
            col_l, col_b, col_s = st.columns([2, 5, 1])
            with col_l:
                st.caption(label)
            with col_b:
                color = "green" if cat_score >= 75 else ("orange" if cat_score >= 50 else "red")
                st.progress(cat_score / 100)
            with col_s:
                st.caption(f"**{cat_score}**")

            if cat_data.get("gaps"):
                with st.expander(f"Gaps in {label}"):
                    for gap in cat_data["gaps"]:
                        st.caption(f"⚠️ {gap}")

        # Risks and recommendations
        col_r, col_rec = st.columns(2)
        with col_r:
            st.subheader("🚨 Top Risks")
            for risk in audit.get("top_risks", []):
                st.markdown(f"- 🔴 {risk}")
        with col_rec:
            st.subheader("✅ Recommendations")
            for rec in audit.get("recommendations", []):
                st.markdown(f"- 💡 {rec}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: VERSION HISTORY
# ─────────────────────────────────────────────────────────────────────────────
elif "Version" in page:
    st.header("📜 Version History")

    if not st.session_state.connected:
        st.warning("Connect to a dataset first.")
        st.stop()

    versions_data = api_get(f"/versions/{st.session_state.dataset_id}")

    if versions_data:
        versions = versions_data.get("versions", [])
        if not versions:
            st.info("No version history yet. Connect the dataset at least twice to see history.")
        else:
            st.caption(f"{len(versions)} version(s) recorded for **{st.session_state.dataset_name}**")

            for v in reversed(versions):
                is_latest = v["version"] == versions[-1]["version"]
                badge = "🟢 **LATEST**" if is_latest else "🔵"
                with st.expander(f"{badge} {v['version']} — {v['timestamp'][:16].replace('T', ' ')}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Tables", v["table_count"])
                    col2.metric("Measures", v["measure_count"])
                    col3.metric("Changes from prev", v.get("change_count", 0))


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: WEBHOOK LOG
# ─────────────────────────────────────────────────────────────────────────────
elif "Webhook" in page:
    st.header("🔗 GitHub Webhook Log")
    st.caption("Live log of every GitHub push event received by AutoDocAI.")

    with st.expander("📖 Setup Instructions", expanded=not st.session_state.connected):
        st.markdown("""
### Step 1 — Make your server public with ngrok
```bash
# Install
pip install pyngrok
# OR download from https://ngrok.com

# Run (in a new terminal, while main.py is running)
ngrok http 8000

# You'll see something like:
# Forwarding  https://abc123.ngrok-free.app → localhost:8000
# Copy that https URL
```

### Step 2 — Add webhook in GitHub
1. Go to your GitHub repo
2. **Settings** → **Webhooks** → **Add webhook**
3. Fill in:
   - **Payload URL**: `https://abc123.ngrok-free.app/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
   - **Which events**: ✅ Just the **push** event
4. Click **Add webhook** — GitHub will send a ping immediately to test it

### Step 3 — Add to your .env
```
GITHUB_WEBHOOK_SECRET=your_secret_here
POWERBI_WEBHOOK_TOKEN=your_pbi_bearer_token
```

### What happens on every push
```
git push origin main
      ↓
GitHub → POST /webhook/github
      ↓
AutoDocAI re-pulls PBI metadata
      ↓
Detects what changed (tables / measures / relationships)
      ↓
Regenerates only the affected documents
      ↓
Docs updated in the app automatically
```
        """)

    col_r, col_c = st.columns([1, 1])
    with col_r:
        if st.button("🔄 Refresh Log"):
            st.rerun()
    with col_c:
        if st.button("🗑️ Clear Log"):
            requests.delete(f"{API}/webhook/log")
            st.rerun()

    log_data = api_get("/webhook/log")
    if log_data:
        events = log_data.get("events", [])
        total  = log_data.get("total", 0)

        if not events:
            st.info("No webhook events received yet. Push to GitHub after setup to see events here.")
        else:
            st.success(f"**{total}** webhook event(s) received")
            for ev in events:
                status = ev.get("status", "")
                icon = (
                    "✅" if "regenerat" in status else
                    "⚠️" if "skipped"   in status else
                    "❌" if "error"     in status else
                    "ℹ️"
                )
                label = (
                    f"{icon} **{ev['event_type'].upper()}** — "
                    f"{ev.get('repository','?')} — "
                    f"{ev.get('timestamp','')[:16].replace('T',' ')}"
                )
                with st.expander(label):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Pusher",  ev.get("pusher", "?"))
                    col2.metric("Commits", ev.get("commits", 0))
                    col3.metric("Branch",  ev.get("ref","").replace("refs/heads/",""))
                    col4.metric("Status",  status[:20])

                    if ev.get("docs_regenerated"):
                        st.write("**Docs regenerated:**", ", ".join(ev["docs_regenerated"]).upper())
                    st.caption(f"Delivery ID: `{ev.get('delivery_id','?')}`")