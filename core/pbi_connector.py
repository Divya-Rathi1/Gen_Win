# # # core/pbi_connector.py
# # # ─────────────────────────────────────────────────────────────────────────────
# # # Power BI REST API connector — no MSAL, uses a raw Bearer token
# # # For prototype: paste your token from browser DevTools
# # # ─────────────────────────────────────────────────────────────────────────────

# # import os
# # import requests
# # from typing import Optional


# # BASE_URL = os.getenv("POWERBI_BASE_URL", "https://api.powerbi.com/v1.0/myorg")


# # def _headers(token: str) -> dict:
# #     return {
# #         "Authorization": f"Bearer {token}",
# #         "Content-Type": "application/json",
# #     }


# # def _get(url: str, token: str) -> dict:
# #     resp = requests.get(url, headers=_headers(token), timeout=30)
# #     resp.raise_for_status()
# #     return resp.json()


# # # ─── Workspace / Group ──────────────────────────────────────────────────────

# # def list_workspaces(token: str) -> list[dict]:
# #     """Return all workspaces accessible to the token owner."""
# #     data = _get(f"{BASE_URL}/groups", token)
# #     return data.get("value", [])


# # def list_datasets(token: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     """Return all datasets in a workspace (or My Workspace if None)."""
# #     if workspace_id:
# #         url = f"{BASE_URL}/groups/{workspace_id}/datasets"
# #     else:
# #         url = f"{BASE_URL}/datasets"
# #     data = _get(url, token)
# #     return data.get("value", [])


# # # ─── Schema extraction ──────────────────────────────────────────────────────

# # def get_tables(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     """Return table schemas with columns for a dataset."""
# #     if workspace_id:
# #         url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/tables"
# #     else:
# #         url = f"{BASE_URL}/datasets/{dataset_id}/tables"
# #     data = _get(url, token)
# #     return data.get("value", [])


# # def get_datasources(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     """Return data sources connected to the dataset."""
# #     if workspace_id:
# #         url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/datasources"
# #     else:
# #         url = f"{BASE_URL}/datasets/{dataset_id}/datasources"
# #     try:
# #         data = _get(url, token)
# #         return data.get("value", [])
# #     except Exception:
# #         return []  # datasource info may be restricted — non-fatal


# # def execute_dax(token: str, dataset_id: str, dax_query: str, workspace_id: Optional[str] = None) -> dict:
# #     """Execute a DAX query and return results (used for data samples)."""
# #     if workspace_id:
# #         url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
# #     else:
# #         url = f"{BASE_URL}/datasets/{dataset_id}/executeQueries"

# #     payload = {
# #         "queries": [{"query": dax_query}],
# #         "serializerSettings": {"includeNulls": True}
# #     }
# #     resp = requests.post(url, headers=_headers(token), json=payload, timeout=30)
# #     resp.raise_for_status()
# #     return resp.json()


# # def get_refresh_history(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     """Return dataset refresh history — useful for QA reports."""
# #     if workspace_id:
# #         url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
# #     else:
# #         url = f"{BASE_URL}/datasets/{dataset_id}/refreshes"
# #     try:
# #         data = _get(url, token)
# #         return data.get("value", [])
# #     except Exception:
# #         return []


# # # ─── Full metadata pull ─────────────────────────────────────────────────────

# # def pull_full_metadata(token: str, dataset_id: str, dataset_name: str,
# #                         workspace_id: Optional[str] = None,
# #                         workspace_name: str = "My Workspace") -> dict:
# #     """
# #     Pull all available metadata for a dataset and return a unified dict.
# #     This is the main entry point — feeds into all AI generation.
# #     """
# #     tables_raw = get_tables(token, dataset_id, workspace_id)
# #     datasources = get_datasources(token, dataset_id, workspace_id)
# #     refresh_history = get_refresh_history(token, dataset_id, workspace_id)

# #     # Extract tables + columns
# #     tables = []
# #     all_measures = []

# #     for table in tables_raw:
# #         tname = table.get("name", "Unknown")
# #         columns = []
# #         for col in table.get("columns", []):
# #             columns.append({
# #                 "name": col.get("name", ""),
# #                 "dataType": col.get("dataType", "unknown"),
# #                 "isHidden": col.get("isHidden", False),
# #                 "description": col.get("description", ""),
# #             })

# #         # Measures live inside tables in the PBI API
# #         for measure in table.get("measures", []):
# #             all_measures.append({
# #                 "name": measure.get("name", ""),
# #                 "table": tname,
# #                 "expression": measure.get("expression", ""),
# #                 "description": measure.get("description", ""),
# #                 "formatString": measure.get("formatString", ""),
# #             })

# #         tables.append({
# #             "name": tname,
# #             "columns": columns,
# #             "isHidden": table.get("isHidden", False),
# #             "description": table.get("description", ""),
# #         })

# #     # Extract relationships
# #     relationships = []
# #     for table in tables_raw:
# #         for rel in table.get("relationships", []):
# #             relationships.append({
# #                 "fromTable": rel.get("fromTable", ""),
# #                 "fromColumn": rel.get("fromColumn", ""),
# #                 "toTable": rel.get("toTable", ""),
# #                 "toColumn": rel.get("toColumn", ""),
# #                 "crossFilteringBehavior": rel.get("crossFilteringBehavior", "single"),
# #             })

# #     # Source system inference from datasource info
# #     source_systems = []
# #     for ds in datasources:
# #         src = {
# #             "type": ds.get("datasourceType", "Unknown"),
# #             "connection": ds.get("connectionDetails", {}),
# #         }
# #         source_systems.append(src)

# #     return {
# #         "dataset_id": dataset_id,
# #         "dataset_name": dataset_name,
# #         "workspace_id": workspace_id,
# #         "workspace_name": workspace_name,
# #         "tables": tables,
# #         "measures": all_measures,
# #         "relationships": relationships,
# #         "datasources": source_systems,
# #         "refresh_history": refresh_history[:5],  # last 5 refreshes
# #         "table_count": len(tables),
# #         "measure_count": len(all_measures),
# #         "relationship_count": len(relationships),
# #     }






# # core/pbi_connector.py
# # Uses INFO() DAX functions — works on all dataset types without admin perms

# # core/pbi_connector.py
# # ─────────────────────────────────────────────────────────────────────────────
# # Power BI REST API connector — no MSAL, uses a raw Bearer token
# # Strategy (in order):
# #   1. REST /tables endpoint  → always works, returns tables + columns + measures
# #   2. REST /relationships    → dedicated endpoint (more reliable than DAX)
# #   3. DAX INFO() fallback    → only if REST tables returns nothing
# #   4. DMV fallback           → last resort
# # ─────────────────────────────────────────────────────────────────────────────

# # import os
# # import requests
# # from typing import Optional

# # BASE_URL = os.getenv("POWERBI_BASE_URL", "https://api.powerbi.com/v1.0/myorg")


# # def _headers(token: str) -> dict:
# #     return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# # def _get(url: str, token: str) -> dict:
# #     resp = requests.get(url, headers=_headers(token), timeout=30)
# #     print(f"[PBI] GET {resp.status_code} → {url.split('myorg/')[-1]}")
# #     if not resp.ok:
# #         print(f"[PBI] Error: {resp.text[:400]}")
# #         resp.raise_for_status()
# #     return resp.json()


# # def _query(token: str, workspace_id: str, dataset_id: str, dax: str) -> list[dict]:
# #     """Execute a DAX query. Returns [] on any error (non-fatal fallback)."""
# #     url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
# #     payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
# #     resp = requests.post(url, headers=_headers(token), json=payload, timeout=30)
# #     print(f"[PBI] DAX {resp.status_code} → {dax[:70]}")
# #     if not resp.ok:
# #         print(f"[PBI] DAX Error: {resp.text[:300]}")
# #         return []
# #     try:
# #         rows = resp.json()["results"][0]["tables"][0].get("rows", [])
# #         # Strip "[TableName].[ColumnName]" key prefixes → plain key names
# #         return [{k.split("].[")[-1].strip("[]"): v for k, v in r.items()} for r in rows]
# #     except Exception as e:
# #         print(f"[PBI] DAX parse error: {e}")
# #         return []


# # # ─── Public helpers ──────────────────────────────────────────────────────────

# # def list_workspaces(token: str) -> list[dict]:
# #     return _get(f"{BASE_URL}/groups", token).get("value", [])


# # def list_datasets(token: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     url = (f"{BASE_URL}/groups/{workspace_id}/datasets"
# #            if workspace_id else f"{BASE_URL}/datasets")
# #     return _get(url, token).get("value", [])


# # def get_datasources(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/datasources"
# #            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/datasources")
# #     try:
# #         return _get(url, token).get("value", [])
# #     except Exception:
# #         return []


# # def get_refresh_history(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
# #     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
# #            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/refreshes")
# #     try:
# #         return _get(url, token).get("value", [])
# #     except Exception:
# #         return []


# # # ─── Strategy 1: REST /tables endpoint ──────────────────────────────────────

# # def _get_schema_via_rest(token: str, dataset_id: str, workspace_id: Optional[str]) -> tuple[list, list, list]:
# #     """
# #     Use the Power BI REST /tables endpoint.
# #     This is the most reliable method — works on all capacity types.
# #     Returns (tables, measures, relationships).
# #     """
# #     tables, measures, relationships = [], [], []

# #     # Tables + columns + measures
# #     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/tables"
# #            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/tables")
# #     try:
# #         data = _get(url, token)
# #         tables_raw = data.get("value", [])
# #         print(f"[PBI] REST tables → {len(tables_raw)} tables found")
# #     except Exception as e:
# #         print(f"[PBI] REST /tables failed: {e}")
# #         return [], [], []

# #     for table in tables_raw:
# #         tname = table.get("name", "Unknown")

# #         # Skip hidden system tables
# #         if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
# #             continue

# #         columns = []
# #         for col in table.get("columns", []):
# #             cname = col.get("name", "")
# #             if not cname or cname.startswith("RowNumber"):
# #                 continue
# #             columns.append({
# #                 "name": cname,
# #                 "dataType": col.get("dataType", "unknown"),
# #                 "isHidden": col.get("isHidden", False),
# #                 "description": col.get("description", ""),
# #             })

# #         for m in table.get("measures", []):
# #             measures.append({
# #                 "name": m.get("name", ""),
# #                 "table": tname,
# #                 "expression": m.get("expression", ""),
# #                 "formatString": m.get("formatString", ""),
# #                 "description": m.get("description", ""),
# #             })

# #         tables.append({
# #             "name": tname,
# #             "columns": columns,
# #             "isHidden": table.get("isHidden", False),
# #             "description": table.get("description", ""),
# #         })

# #     # Relationships via dedicated REST endpoint
# #     rel_url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/relationships"
# #                if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/relationships")
# #     try:
# #         rel_data = _get(rel_url, token)
# #         for r in rel_data.get("value", []):
# #             relationships.append({
# #                 "fromTable": r.get("fromTable", "?"),
# #                 "fromColumn": r.get("fromColumn", "?"),
# #                 "toTable": r.get("toTable", "?"),
# #                 "toColumn": r.get("toColumn", "?"),
# #                 "crossFilteringBehavior": r.get("crossFilteringBehavior", "oneDirection"),
# #             })
# #         print(f"[PBI] REST relationships → {len(relationships)} found")
# #     except Exception as e:
# #         print(f"[PBI] REST /relationships failed (non-fatal): {e}")

# #     return tables, measures, relationships


# # # ─── Strategy 2: DAX INFO() functions ───────────────────────────────────────

# # def _get_schema_via_dax_info(token: str, dataset_id: str, workspace_id: str) -> tuple[list, list, list]:
# #     """
# #     Fallback: use DAX INFO.TABLES(), INFO.COLUMNS(), INFO.MEASURES(), INFO.RELATIONSHIPS().
# #     Works on Premium/Fabric datasets with XMLA endpoint access.
# #     """
# #     tables, measures, relationships = [], [], []

# #     tables_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.TABLES()")
# #     print(f"[PBI] INFO.TABLES() → {len(tables_rows)} rows")

# #     table_id_map = {}
# #     for t in tables_rows:
# #         tid = t.get("ID")
# #         tname = t.get("Name", "")
# #         if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
# #             continue
# #         table_id_map[tid] = tname
# #         tables.append({"name": tname, "isHidden": t.get("IsHidden", False), "columns": []})

# #     col_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.COLUMNS()")
# #     print(f"[PBI] INFO.COLUMNS() → {len(col_rows)} rows")

# #     col_id_map = {}
# #     dtype_map = {"2": "string", "6": "integer", "8": "float",
# #                  "9": "decimal", "10": "datetime", "11": "boolean"}
# #     for c in col_rows:
# #         cname = c.get("ExplicitName") or c.get("Name", "")
# #         if not cname or cname.startswith("RowNumber"):
# #             continue
# #         col_id_map[c.get("ID")] = cname
# #         tname = table_id_map.get(c.get("TableID"))
# #         if not tname:
# #             continue
# #         dtype = dtype_map.get(str(c.get("DataType", "")), str(c.get("DataType", "")))
# #         for tbl in tables:
# #             if tbl["name"] == tname:
# #                 tbl["columns"].append({"name": cname, "dataType": dtype, "isHidden": c.get("IsHidden", False)})
# #                 break

# #     meas_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.MEASURES()")
# #     print(f"[PBI] INFO.MEASURES() → {len(meas_rows)} rows")
# #     for m in meas_rows:
# #         measures.append({
# #             "name": m.get("Name", ""),
# #             "table": table_id_map.get(m.get("TableID"), "Unknown"),
# #             "expression": m.get("Expression", ""),
# #             "formatString": m.get("FormatString", ""),
# #         })

# #     rel_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.RELATIONSHIPS()")
# #     print(f"[PBI] INFO.RELATIONSHIPS() → {len(rel_rows)} rows")
# #     for r in rel_rows:
# #         relationships.append({
# #             "fromTable": table_id_map.get(r.get("FromTableID"), "?"),
# #             "fromColumn": col_id_map.get(r.get("FromColumnID"), str(r.get("FromColumnID", "?"))),
# #             "toTable": table_id_map.get(r.get("ToTableID"), "?"),
# #             "toColumn": col_id_map.get(r.get("ToColumnID"), str(r.get("ToColumnID", "?"))),
# #         })

# #     return tables, measures, relationships


# # # ─── Strategy 3: DMV schema queries ─────────────────────────────────────────

# # def _get_schema_via_dmv(token: str, dataset_id: str, workspace_id: str) -> tuple[list, list, list]:
# #     """Last-resort fallback using DMV $SYSTEM schema queries."""
# #     tables = []
# #     schema_rows = _query(token, workspace_id, dataset_id,
# #                          "SELECT * FROM $SYSTEM.DBSCHEMA_TABLES WHERE TABLE_TYPE = 'TABLE'")
# #     print(f"[PBI] DMV DBSCHEMA_TABLES → {len(schema_rows)} rows")

# #     for t in schema_rows:
# #         tname = t.get("TABLE_NAME", "")
# #         if tname and not tname.startswith(("$", "Date")):
# #             tables.append({"name": tname, "columns": [], "isHidden": False})

# #     if tables:
# #         col_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.DBSCHEMA_COLUMNS")
# #         for c in col_rows:
# #             tname = c.get("TABLE_NAME", "")
# #             cname = c.get("COLUMN_NAME", "")
# #             for tbl in tables:
# #                 if tbl["name"] == tname and cname and not cname.startswith("RowNumber"):
# #                     tbl["columns"].append({"name": cname, "dataType": c.get("DATA_TYPE", ""), "isHidden": False})
# #                     break

# #     return tables, [], []


# # # ─── Main entry point ────────────────────────────────────────────────────────

# # def pull_full_metadata(token: str, dataset_id: str, dataset_name: str,
# #                        workspace_id: Optional[str] = None,
# #                        workspace_name: str = "My Workspace") -> dict:
# #     """
# #     Pull all available metadata for a dataset.
# #     Tries three strategies in order:
# #       1. REST /tables + /relationships  (most compatible — works without DAX exec perms)
# #       2. DAX INFO() functions           (Premium/Fabric with XMLA)
# #       3. DMV $SYSTEM queries            (last resort)
# #     """
# #     print(f"\n[PBI] Pulling metadata: {dataset_name} | {workspace_name}")

# #     tables, measures, relationships = [], [], []

# #     # ── Strategy 1: REST API (preferred) ────────────────────────────────────
# #     print("[PBI] Trying REST /tables endpoint...")
# #     tables, measures, relationships = _get_schema_via_rest(token, dataset_id, workspace_id)

# #     # ── Strategy 2: DAX INFO() ───────────────────────────────────────────────
# #     if not tables and workspace_id:
# #         print("[PBI] REST returned nothing — trying DAX INFO() functions...")
# #         tables, measures, relationships = _get_schema_via_dax_info(token, dataset_id, workspace_id)

# #     # ── Strategy 3: DMV ──────────────────────────────────────────────────────
# #     if not tables and workspace_id:
# #         print("[PBI] DAX INFO() returned nothing — trying DMV fallback...")
# #         tables, measures, relationships = _get_schema_via_dmv(token, dataset_id, workspace_id)

# #     # ── Supplementary calls (non-fatal) ─────────────────────────────────────
# #     datasources = get_datasources(token, dataset_id, workspace_id)
# #     refresh_history = get_refresh_history(token, dataset_id, workspace_id)

# #     print(f"[PBI] Final result: {len(tables)} tables, {len(measures)} measures, {len(relationships)} relationships")

# #     if not tables:
# #         raise Exception(
# #             "Could not extract schema via any method. Possible causes:\n"
# #             "  • Token expired — get a fresh Bearer token from browser DevTools\n"
# #             "  • Dataset has no published tables (push datasets, streaming datasets)\n"
# #             "  • Insufficient permissions on this workspace\n"
# #             "  • Dataset is in a Personal workspace (try a shared workspace)\n"
# #             "Open the report in Power BI, let it load fully, copy a fresh token, then retry."
# #         )

# #     return {
# #         "dataset_id": dataset_id,
# #         "dataset_name": dataset_name,
# #         "workspace_id": workspace_id,
# #         "workspace_name": workspace_name,
# #         "tables": tables,
# #         "measures": measures,
# #         "relationships": relationships,
# #         "datasources": [{"type": d.get("datasourceType"), "connection": d.get("connectionDetails", {})}
# #                         for d in datasources],
# #         "refresh_history": refresh_history[:5],
# #         "table_count": len(tables),
# #         "measure_count": len(measures),
# #         "relationship_count": len(relationships),
# #     }


# # core/pbi_connector.py
# # ─────────────────────────────────────────────────────────────────────────────
# # Power BI REST API connector — no MSAL, uses a raw Bearer token
# #
# # Strategy order:
# #   1. Admin Scanner API  → best: full schema, any dataset type (needs admin)
# #   2. DMV via executeQueries  → fixed parser, works on most Import models
# #   3. DAX INFO() functions    → Premium/Fabric with XMLA
# # ─────────────────────────────────────────────────────────────────────────────

# # core/pbi_connector.py
# # Power BI REST API connector - no MSAL, uses a raw Bearer token
# #
# # Strategy order:
# #   1. Admin Scanner API  - best: full schema, any dataset type (needs admin)
# #   2. DMV via executeQueries - works on most Import models
# #   3. DAX INFO() functions   - Premium/Fabric with XMLA

# # core/pbi_connector.py
# # Power BI REST API connector - no MSAL, uses raw Bearer token
# #
# # Strategy order:
# #   1. Admin Scanner API  - full schema, any dataset (needs tenant/workspace admin)
# #   2. DMV via executeQueries - Import/DirectQuery models
# #   3. DAX INFO() functions  - Premium/Fabric XMLA

# import os
# import json
# import time
# import requests
# from typing import Optional

# BASE_URL = os.getenv("POWERBI_BASE_URL", "https://api.powerbi.com/v1.0/myorg")

# # DMV system tables/schemas to skip - exact TABLE_TYPE values Power BI returns
# DMV_SYSTEM_TYPES = {"SYSTEM TABLE", "SCHEMA", "GLOBAL TEMPORARY"}

# # Name prefixes that indicate system/hidden objects
# SYSTEM_NAME_PREFIXES = (
#     "$", "DateTableTemplate", "LocalDateTable", "~",
#     "Rows In ", "DBSCHEMA_", "DISCOVER_", "MDSCHEMA_",
#     "TMSCHEMA_", "SYSTEMRESTRICTEDSCHEMA",
# )


# def _headers(token: str) -> dict:
#     return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# def _get(url: str, token: str) -> dict:
#     resp = requests.get(url, headers=_headers(token), timeout=30)
#     print(f"[PBI] GET {resp.status_code} -> {url.split('myorg/')[-1]}")
#     if not resp.ok:
#         print(f"[PBI] Error: {resp.text[:400]}")
#         resp.raise_for_status()
#     return resp.json()


# def _post(url: str, token: str, payload: dict) -> dict:
#     resp = requests.post(url, headers=_headers(token), json=payload, timeout=60)
#     print(f"[PBI] POST {resp.status_code} -> {url.split('myorg/')[-1]}")
#     if not resp.ok:
#         print(f"[PBI] Error: {resp.text[:400]}")
#         resp.raise_for_status()
#     return resp.json()


# def _execute_query(token: str, workspace_id: str, dataset_id: str, dax: str) -> dict:
#     url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
#     payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
#     resp = requests.post(url, headers=_headers(token), json=payload, timeout=30)
#     print(f"[PBI] DAX {resp.status_code} -> {dax[:80]}")
#     if not resp.ok:
#         print(f"[PBI] DAX Error: {resp.text[:300]}")
#         return {}
#     try:
#         return resp.json()
#     except Exception as e:
#         print(f"[PBI] DAX JSON parse error: {e}")
#         return {}


# def _parse_query_response(raw: dict) -> list[dict]:
#     """Parse executeQueries response, stripping key prefixes."""
#     if not raw:
#         return []
#     try:
#         result_tables = raw["results"][0]["tables"]
#         if not result_tables:
#             return []
#         rows = result_tables[0].get("rows", [])
#         cleaned = []
#         for row in rows:
#             clean_row = {}
#             for k, v in row.items():
#                 if "].[" in k:
#                     clean_key = k.split("].[")[-1].rstrip("]")
#                 elif k.startswith("[") and k.endswith("]"):
#                     clean_key = k[1:-1]
#                 else:
#                     clean_key = k
#                 clean_row[clean_key] = v
#             cleaned.append(clean_row)
#         return cleaned
#     except (KeyError, IndexError, TypeError) as e:
#         print(f"[PBI] Response parse error: {e}")
#         try:
#             print(f"[PBI] Raw: {json.dumps(raw, default=str)[:500]}")
#         except Exception:
#             pass
#         return []


# def _query(token: str, workspace_id: str, dataset_id: str, dax: str) -> list[dict]:
#     return _parse_query_response(_execute_query(token, workspace_id, dataset_id, dax))


# # Public helpers

# def list_workspaces(token: str) -> list[dict]:
#     return _get(f"{BASE_URL}/groups", token).get("value", [])


# def list_datasets(token: str, workspace_id: Optional[str] = None) -> list[dict]:
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets"
#            if workspace_id else f"{BASE_URL}/datasets")
#     return _get(url, token).get("value", [])


# def get_datasources(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/datasources"
#            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/datasources")
#     try:
#         return _get(url, token).get("value", [])
#     except Exception:
#         return []


# def get_refresh_history(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
#            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/refreshes")
#     try:
#         return _get(url, token).get("value", [])
#     except Exception:
#         return []


# # Strategy 1: Admin Scanner API

# def _get_schema_via_scanner(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     """Requires Power BI tenant admin or workspace admin."""
#     tables, measures, relationships = [], [], []
#     try:
#         scan_resp = _post(
#             f"{BASE_URL}/admin/workspaces/getInfo"
#             "?lineage=true&datasourceDetails=true&datasetSchema=true&datasetExpressions=true",
#             token, {"workspaces": [workspace_id]}
#         )
#         scan_id = scan_resp.get("id")
#         if not scan_id:
#             return [], [], []
#         print(f"[PBI] Scanner ID: {scan_id} - polling...")
#         for i in range(8):
#             time.sleep(4)
#             status = _get(f"{BASE_URL}/admin/workspaces/scanStatus/{scan_id}", token).get("status", "")
#             print(f"[PBI] Scanner poll {i+1}: {status}")
#             if status == "Succeeded":
#                 break
#         else:
#             return [], [], []

#         result = _get(f"{BASE_URL}/admin/workspaces/scanResult/{scan_id}", token)
#         for ws in result.get("workspaces", []):
#             for ds in ws.get("datasets", []):
#                 if ds.get("id") != dataset_id:
#                     continue
#                 for t in ds.get("tables", []):
#                     tname = t.get("name", "")
#                     if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
#                         continue
#                     columns = [
#                         {"name": c.get("name",""), "dataType": c.get("dataType","unknown"),
#                          "isHidden": c.get("isHidden", False), "description": c.get("description","")}
#                         for c in t.get("columns", [])
#                         if c.get("name") and not c.get("name","").startswith("RowNumber")
#                     ]
#                     for m in t.get("measures", []):
#                         measures.append({"name": m.get("name",""), "table": tname,
#                                          "expression": m.get("expression",""),
#                                          "formatString": m.get("formatString",""),
#                                          "description": m.get("description","")})
#                     tables.append({"name": tname, "columns": columns,
#                                    "isHidden": t.get("isHidden", False),
#                                    "description": t.get("description","")})
#                 for r in ds.get("relationships", []):
#                     relationships.append({"fromTable": r.get("fromTable","?"),
#                                           "fromColumn": r.get("fromColumn","?"),
#                                           "toTable": r.get("toTable","?"),
#                                           "toColumn": r.get("toColumn","?"),
#                                           "crossFilteringBehavior": r.get("crossFilteringBehavior","oneDirection")})
#         print(f"[PBI] Scanner: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
#     except Exception as e:
#         print(f"[PBI] Scanner failed: {e}")
#         return [], [], []
#     return tables, measures, relationships


# # Strategy 2: DMV $SYSTEM queries

# def _get_schema_via_dmv(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     """
#     DMV queries. Filters TABLE_TYPE strictly to 'TABLE' only (not SCHEMA/SYSTEM TABLE).
#     Fetches columns per-table to avoid row-limit truncation.
#     """
#     tables, measures, relationships = [], [], []

#     # Step 1: Get tables - ONLY TABLE_TYPE = 'TABLE'
#     table_rows = _query(token, workspace_id, dataset_id,
#                         "SELECT [TABLE_NAME], [TABLE_TYPE] FROM $SYSTEM.DBSCHEMA_TABLES "
#                         "WHERE [TABLE_TYPE] = 'TABLE'")
#     print(f"[PBI] DMV TABLE_TYPE='TABLE' filter -> {len(table_rows)} rows")

#     if not table_rows:
#         # Fallback: get all and filter manually in case WHERE isn't supported
#         table_rows = _query(token, workspace_id, dataset_id,
#                             "SELECT [TABLE_NAME], [TABLE_TYPE] FROM $SYSTEM.DBSCHEMA_TABLES")
#         print(f"[PBI] DMV all tables -> {len(table_rows)} rows")
#         type_counts = {}
#         for r in table_rows:
#             t = r.get("TABLE_TYPE","")
#             type_counts[t] = type_counts.get(t, 0) + 1
#         print(f"[PBI] TABLE_TYPE breakdown: {type_counts}")
#         # Keep only TABLE type
#         table_rows = [r for r in table_rows if r.get("TABLE_TYPE") == "TABLE"]
#         print(f"[PBI] After TABLE_TYPE='TABLE' filter: {len(table_rows)} rows")

#     for t in table_rows:
#         tname = t.get("TABLE_NAME", "")
#         if tname and not any(tname.startswith(p) for p in SYSTEM_NAME_PREFIXES):
#             tables.append({"name": tname, "columns": [], "isHidden": False, "description": ""})

#     print(f"[PBI] DMV user tables: {len(tables)} -> {[t['name'] for t in tables[:8]]}")

#     # Step 2: Columns - query per-table to avoid row-limit truncation
#     # The executeQueries API caps results at 100k rows per call but
#     # a WHERE per table ensures we get all columns for each table.
#     for tbl in tables:
#         tname = tbl["name"]
#         # Escape single quotes in table name
#         safe_name = tname.replace("'", "''")
#         col_rows = _query(
#             token, workspace_id, dataset_id,
#             f"SELECT [COLUMN_NAME], [DATA_TYPE] FROM $SYSTEM.DBSCHEMA_COLUMNS "
#             f"WHERE [TABLE_NAME] = '{safe_name}'"
#         )
#         for c in col_rows:
#             cname = c.get("COLUMN_NAME", "")
#             if cname and not cname.startswith("RowNumber"):
#                 tbl["columns"].append({
#                     "name": cname,
#                     "dataType": str(c.get("DATA_TYPE", "unknown")),
#                     "isHidden": False,
#                 })
#         if tbl["columns"]:
#             print(f"[PBI] DMV {tname}: {len(tbl['columns'])} columns")

#     total_cols = sum(len(t["columns"]) for t in tables)
#     print(f"[PBI] DMV total columns: {total_cols}")

#     # Step 3: Measures - use CUBE_NAME filter to get only user measures
#     # CUBE_NAME in PBI DMV = the dataset/model name, not system catalogs
#     meas_rows = _query(token, workspace_id, dataset_id,
#                        "SELECT * FROM $SYSTEM.MDSCHEMA_MEASURES WHERE MEASURE_IS_VISIBLE = true")
#     print(f"[PBI] DMV MDSCHEMA_MEASURES (visible only) -> {len(meas_rows)} rows")

#     if not meas_rows:
#         # Some tenants don't support boolean filter - try without
#         meas_rows = _query(token, workspace_id, dataset_id,
#                            "SELECT * FROM $SYSTEM.MDSCHEMA_MEASURES")
#         print(f"[PBI] DMV MDSCHEMA_MEASURES (all) -> {len(meas_rows)} rows")

#     if meas_rows:
#         print(f"[PBI] Measure keys: {list(meas_rows[0].keys())}")

#     # Find the real user measure group name (= dataset name, not a system cube)
#     # System entries typically have MEASURE_CAPTION matching MEASURE_NAME with no expression
#     for m in meas_rows:
#         mname = m.get("MEASURE_NAME") or m.get("MEASURENAME") or ""
#         expr  = m.get("EXPRESSION") or m.get("MEASURE_EXPRESSION") or ""
#         tname = m.get("MEASUREGROUP_NAME") or m.get("MEASUREGROUPNAME") or "Unknown"
#         caption = m.get("MEASURE_CAPTION") or mname
#         visible = m.get("MEASURE_IS_VISIBLE")
#         # Skip if no name, starts with _, or is an implicit auto-measure (no expression, caption == name)
#         if not mname or mname.startswith("_"):
#             continue
#         # Skip system implicit measures that have no DAX expression
#         # Real user measures have an EXPRESSION; implicit ones don't
#         measures.append({
#             "name": mname,
#             "table": tname,
#             "expression": expr,
#             "formatString": m.get("DEFAULT_FORMAT_STRING", ""),
#             "description": "",
#         })

#     print(f"[PBI] DMV result: {len(tables)} tables, {len(measures)} measures")
#     return tables, measures, relationships


# # Strategy 3: DAX INFO() functions

# def _get_schema_via_dax_info(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     """Premium/Fabric XMLA fallback."""
#     tables, measures, relationships = [], [], []
#     dtype_map = {"2":"string","6":"integer","8":"float","9":"decimal","10":"datetime","11":"boolean"}

#     tables_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.TABLES()")
#     print(f"[PBI] INFO.TABLES() -> {len(tables_rows)} rows")
#     table_id_map = {}
#     for t in tables_rows:
#         tid = t.get("ID")
#         tname = t.get("Name", "")
#         if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
#             continue
#         table_id_map[tid] = tname
#         tables.append({"name": tname, "isHidden": t.get("IsHidden", False), "columns": [], "description": ""})

#     col_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.COLUMNS()")
#     col_id_map = {}
#     for c in col_rows:
#         cname = c.get("ExplicitName") or c.get("Name", "")
#         if not cname or cname.startswith("RowNumber"):
#             continue
#         col_id_map[c.get("ID")] = cname
#         tname = table_id_map.get(c.get("TableID"))
#         if not tname:
#             continue
#         for tbl in tables:
#             if tbl["name"] == tname:
#                 tbl["columns"].append({"name": cname,
#                                        "dataType": dtype_map.get(str(c.get("DataType","")), "unknown"),
#                                        "isHidden": c.get("IsHidden", False)})
#                 break

#     meas_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.MEASURES()")
#     for m in meas_rows:
#         measures.append({"name": m.get("Name",""), "table": table_id_map.get(m.get("TableID"),"Unknown"),
#                          "expression": m.get("Expression",""), "formatString": m.get("FormatString",""),
#                          "description": ""})

#     rel_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.RELATIONSHIPS()")
#     for r in rel_rows:
#         relationships.append({"fromTable": table_id_map.get(r.get("FromTableID"),"?"),
#                                "fromColumn": col_id_map.get(r.get("FromColumnID"),"?"),
#                                "toTable": table_id_map.get(r.get("ToTableID"),"?"),
#                                "toColumn": col_id_map.get(r.get("ToColumnID"),"?")})

#     print(f"[PBI] INFO(): {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
#     return tables, measures, relationships


# # Main entry point

# def pull_full_metadata(token: str, dataset_id: str, dataset_name: str,
#                        workspace_id: Optional[str] = None,
#                        workspace_name: str = "My Workspace") -> dict:
#     print(f"\n[PBI] === Pulling: {dataset_name} | {workspace_name} ===")

#     tables, measures, relationships = [], [], []

#     if workspace_id:
#         print("[PBI] -> Strategy 1: Admin Scanner API")
#         tables, measures, relationships = _get_schema_via_scanner(token, workspace_id, dataset_id)

#     if not tables and workspace_id:
#         print("[PBI] -> Strategy 2: DMV $SYSTEM queries")
#         tables, measures, relationships = _get_schema_via_dmv(token, workspace_id, dataset_id)

#     if not tables and workspace_id:
#         print("[PBI] -> Strategy 3: DAX INFO() functions")
#         tables, measures, relationships = _get_schema_via_dax_info(token, workspace_id, dataset_id)

#     datasources = get_datasources(token, dataset_id, workspace_id)
#     refresh_history = get_refresh_history(token, dataset_id, workspace_id)

#     print(f"[PBI] === Final: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels ===\n")

#     if not tables:
#         raise Exception(
#             "Could not extract schema via any method.\n\n"
#             "FIXES TO TRY:\n"
#             "  1. Get a fresh token from DevTools (expires in ~1 hour)\n"
#             "  2. Make sure you are a Member or Admin of this workspace (not Viewer)\n"
#             "  3. Enable 'XMLA Endpoints' in PBI Admin Portal -> Tenant Settings\n"
#             "  4. If you have tenant admin rights, Strategy 1 (Scanner API) will work\n\n"
#             "WORKAROUND: POST to /connect/manual with your schema JSON."
#         )

#     return {
#         "dataset_id": dataset_id,
#         "dataset_name": dataset_name,
#         "workspace_id": workspace_id,
#         "workspace_name": workspace_name,
#         "tables": tables,
#         "measures": measures,
#         "relationships": relationships,
#         "datasources": [{"type": d.get("datasourceType"), "connection": d.get("connectionDetails", {})}
#                         for d in datasources],
#         "refresh_history": refresh_history[:5],
#         "table_count": len(tables),
#         "measure_count": len(measures),
#         "relationship_count": len(relationships),
#     }


# core/pbi_connector.py
# Power BI REST API connector - no MSAL, uses raw Bearer token
#
# KEY INSIGHT: Power BI DMV uses INVERTED TABLE_TYPE conventions:
#   TABLE_TYPE='SYSTEM TABLE' = actual user data tables  (e.g. 'Sheet1', 'Sales')
#   TABLE_TYPE='TABLE'        = internal $ shadow copies (e.g. '$Sheet1')
#   TABLE_TYPE='SCHEMA'       = DMV catalog views
#
# Strategy order:
#   1. Admin Scanner API    - full schema, any type (needs tenant/workspace admin)
#   2. TMSCHEMA views       - richest metadata, works on Import/DirectQuery models
#   3. DBSCHEMA + MDSCHEMA  - fallback DMV approach
#   4. DAX INFO()           - Premium/Fabric XMLA only

# core/pbi_connector.py
# Power BI REST API connector - no MSAL, uses raw Bearer token
#
# KEY INSIGHT: Power BI DMV TABLE_TYPE is counterintuitive:
#   'SYSTEM TABLE' = actual user data tables
#   'TABLE'        = internal $-prefixed shadow copies
#   'SCHEMA'       = DMV catalog views

# import os
# import json
# import time
# import requests
# from typing import Optional

# BASE_URL = os.getenv("POWERBI_BASE_URL", "https://api.powerbi.com/v1.0/myorg")


# def _headers(token: str) -> dict:
#     return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# def _get(url: str, token: str) -> dict:
#     resp = requests.get(url, headers=_headers(token), timeout=30)
#     print(f"[PBI] GET {resp.status_code} -> {url.split('myorg/')[-1]}")
#     if not resp.ok:
#         print(f"[PBI] Error: {resp.text[:400]}")
#         resp.raise_for_status()
#     return resp.json()


# def _post(url: str, token: str, payload: dict) -> dict:
#     resp = requests.post(url, headers=_headers(token), json=payload, timeout=60)
#     print(f"[PBI] POST {resp.status_code} -> {url.split('myorg/')[-1]}")
#     if not resp.ok:
#         print(f"[PBI] Error: {resp.text[:400]}")
#         resp.raise_for_status()
#     return resp.json()


# def _execute_query(token: str, workspace_id: str, dataset_id: str, dax: str) -> dict:
#     url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
#     payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
#     resp = requests.post(url, headers=_headers(token), json=payload, timeout=30)
#     print(f"[PBI] DAX {resp.status_code} -> {dax[:80]}")
#     if not resp.ok:
#         print(f"[PBI] DAX Error: {resp.text[:300]}")
#         return {}
#     try:
#         return resp.json()
#     except Exception as e:
#         print(f"[PBI] DAX JSON parse error: {e}")
#         return {}


# def _parse_query_response(raw: dict) -> list[dict]:
#     """Parse executeQueries response, stripping key prefixes."""
#     if not raw:
#         return []
#     try:
#         result_tables = raw["results"][0]["tables"]
#         if not result_tables:
#             return []
#         rows = result_tables[0].get("rows", [])
#         cleaned = []
#         for row in rows:
#             clean_row = {}
#             for k, v in row.items():
#                 if "].[" in k:
#                     clean_key = k.split("].[")[-1].rstrip("]")
#                 elif k.startswith("[") and k.endswith("]"):
#                     clean_key = k[1:-1]
#                 else:
#                     clean_key = k
#                 clean_row[clean_key] = v
#             cleaned.append(clean_row)
#         return cleaned
#     except (KeyError, IndexError, TypeError) as e:
#         print(f"[PBI] Response parse error: {e}")
#         try:
#             print(f"[PBI] Raw: {json.dumps(raw, default=str)[:600]}")
#         except Exception:
#             pass
#         return []


# def _query(token: str, workspace_id: str, dataset_id: str, dax: str) -> list[dict]:
#     return _parse_query_response(_execute_query(token, workspace_id, dataset_id, dax))


# # Public helpers

# def list_workspaces(token: str) -> list[dict]:
#     return _get(f"{BASE_URL}/groups", token).get("value", [])


# def list_datasets(token: str, workspace_id: Optional[str] = None) -> list[dict]:
#     """List all datasets. Enriches each with configuredBy and isRefreshable."""
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets"
#            if workspace_id else f"{BASE_URL}/datasets")
#     datasets = _get(url, token).get("value", [])
#     # Log all datasets to help user identify the correct one
#     print(f"[PBI] Datasets in workspace ({len(datasets)} found):")
#     for ds in datasets:
#         print(f"[PBI]   id={ds.get('id')} | name={repr(ds.get('name'))} | "
#               f"configuredBy={ds.get('configuredBy')} | "
#               f"isRefreshable={ds.get('isRefreshable')} | "
#               f"targetStorageMode={ds.get('targetStorageMode')}")
#     return datasets


# def get_datasources(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/datasources"
#            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/datasources")
#     try:
#         return _get(url, token).get("value", [])
#     except Exception:
#         return []


# def get_refresh_history(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
#     url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
#            if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/refreshes")
#     try:
#         return _get(url, token).get("value", [])
#     except Exception:
#         return []


# # Strategy 1: Admin Scanner API

# def _get_schema_via_scanner(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     tables, measures, relationships = [], [], []
#     try:
#         scan_resp = _post(
#             f"{BASE_URL}/admin/workspaces/getInfo"
#             "?lineage=true&datasourceDetails=true&datasetSchema=true&datasetExpressions=true",
#             token, {"workspaces": [workspace_id]}
#         )
#         scan_id = scan_resp.get("id")
#         if not scan_id:
#             return [], [], []
#         print(f"[PBI] Scanner ID: {scan_id} - polling...")
#         for i in range(8):
#             time.sleep(4)
#             status = _get(f"{BASE_URL}/admin/workspaces/scanStatus/{scan_id}", token).get("status", "")
#             print(f"[PBI] Scanner poll {i+1}: {status}")
#             if status == "Succeeded":
#                 break
#         else:
#             return [], [], []
#         result = _get(f"{BASE_URL}/admin/workspaces/scanResult/{scan_id}", token)
#         for ws in result.get("workspaces", []):
#             for ds in ws.get("datasets", []):
#                 if ds.get("id") != dataset_id:
#                     continue
#                 for t in ds.get("tables", []):
#                     tname = t.get("name", "")
#                     if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
#                         continue
#                     columns = [
#                         {"name": c.get("name",""), "dataType": c.get("dataType","unknown"),
#                          "isHidden": c.get("isHidden", False), "description": c.get("description","")}
#                         for c in t.get("columns", [])
#                         if c.get("name") and not c.get("name","").startswith("RowNumber")
#                     ]
#                     for m in t.get("measures", []):
#                         measures.append({"name": m.get("name",""), "table": tname,
#                                          "expression": m.get("expression",""),
#                                          "formatString": m.get("formatString",""),
#                                          "description": m.get("description","")})
#                     tables.append({"name": tname, "columns": columns,
#                                    "isHidden": t.get("isHidden", False),
#                                    "description": t.get("description","")})
#                 for r in ds.get("relationships", []):
#                     relationships.append({"fromTable": r.get("fromTable","?"),
#                                           "fromColumn": r.get("fromColumn","?"),
#                                           "toTable": r.get("toTable","?"),
#                                           "toColumn": r.get("toColumn","?"),
#                                           "crossFilteringBehavior": r.get("crossFilteringBehavior","oneDirection")})
#         print(f"[PBI] Scanner: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
#     except Exception as e:
#         print(f"[PBI] Scanner failed: {e}")
#         return [], [], []
#     return tables, measures, relationships


# # Strategy 2: TMSCHEMA views

# def _get_schema_via_tmschema(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     tables, measures, relationships = [], [], []

#     tbl_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_TABLES")
#     print(f"[PBI] TMSCHEMA_TABLES -> {len(tbl_rows)} rows")

#     table_id_map = {}
#     for t in tbl_rows:
#         tid   = t.get("ID")
#         tname = t.get("Name", "")
#         if tname.startswith(("DateTableTemplate", "LocalDateTable")):
#             continue
#         table_id_map[tid] = tname
#         tables.append({"name": tname, "columns": [], "isHidden": t.get("IsHidden", False),
#                        "description": t.get("Description", "")})

#     print(f"[PBI] TMSCHEMA tables: {len(tables)} -> {[t['name'] for t in tables]}")
#     if not tables:
#         return [], [], []

#     dtype_map = {"2":"string","6":"integer","8":"float","9":"decimal",
#                  "10":"datetime","11":"boolean","17":"binary","19":"variant"}

#     col_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_COLUMNS")
#     print(f"[PBI] TMSCHEMA_COLUMNS -> {len(col_rows)} rows")
#     col_id_map = {}
#     for c in col_rows:
#         cname = c.get("ExplicitName") or c.get("Name", "")
#         if not cname or cname.startswith("RowNumber") or c.get("Type") == 3:
#             continue
#         col_id_map[c.get("ID")] = cname
#         tname = table_id_map.get(c.get("TableID"))
#         if not tname:
#             continue
#         dtype = dtype_map.get(str(c.get("ExplicitDataType") or c.get("DataType") or ""), "unknown")
#         for tbl in tables:
#             if tbl["name"] == tname:
#                 tbl["columns"].append({"name": cname, "dataType": dtype,
#                                        "isHidden": c.get("IsHidden", False),
#                                        "description": c.get("Description", "")})
#                 break

#     meas_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_MEASURES")
#     print(f"[PBI] TMSCHEMA_MEASURES -> {len(meas_rows)} rows")
#     for m in meas_rows:
#         mname = m.get("Name", "")
#         if not mname or mname.startswith("_"):
#             continue
#         measures.append({"name": mname, "table": table_id_map.get(m.get("TableID"), "Unknown"),
#                          "expression": m.get("Expression", ""), "formatString": m.get("FormatString", ""),
#                          "description": m.get("Description", "")})

#     rel_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS")
#     print(f"[PBI] TMSCHEMA_RELATIONSHIPS -> {len(rel_rows)} rows")
#     for r in rel_rows:
#         relationships.append({
#             "fromTable":  table_id_map.get(r.get("FromTableID"), str(r.get("FromTableID"))),
#             "fromColumn": col_id_map.get(r.get("FromColumnID"), str(r.get("FromColumnID"))),
#             "toTable":    table_id_map.get(r.get("ToTableID"), str(r.get("ToTableID"))),
#             "toColumn":   col_id_map.get(r.get("ToColumnID"), str(r.get("ToColumnID"))),
#             "crossFilteringBehavior": r.get("CrossFilteringBehavior", "oneDirection"),
#         })

#     print(f"[PBI] TMSCHEMA final: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
#     return tables, measures, relationships


# # Strategy 3: DBSCHEMA with correct SYSTEM TABLE filter + all-columns query

# def _get_schema_via_dbschema(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     """
#     In Power BI DMV, TABLE_TYPE='SYSTEM TABLE' = actual user tables (counterintuitive).
#     Fetches ALL columns in one query (no WHERE) to avoid per-table row-limit issues.
#     """
#     tables, measures, relationships = [], [], []

#     table_rows = _query(token, workspace_id, dataset_id,
#                         "SELECT [TABLE_NAME], [TABLE_TYPE] FROM $SYSTEM.DBSCHEMA_TABLES")

#     user_table_names = set()
#     for r in table_rows:
#         tname = r.get("TABLE_NAME", "")
#         ttype = r.get("TABLE_TYPE", "")
#         if ttype == "SYSTEM TABLE" and tname and not tname.startswith(("DateTableTemplate", "LocalDateTable")):
#             user_table_names.add(tname)
#             tables.append({"name": tname, "columns": [], "isHidden": False, "description": ""})

#     print(f"[PBI] DBSCHEMA user tables: {len(tables)} -> {[t['name'] for t in tables]}")
#     if not tables:
#         return [], [], []

#     # Fetch ALL columns at once - no WHERE clause to avoid row-limit truncation
#     # The executeQueries API truncates at ~100k rows total but a single
#     # table's columns will never hit that
#     all_col_rows = _query(token, workspace_id, dataset_id,
#                           "SELECT [TABLE_NAME], [COLUMN_NAME], [DATA_TYPE], [ORDINAL_POSITION] "
#                           "FROM $SYSTEM.DBSCHEMA_COLUMNS ORDER BY [TABLE_NAME], [ORDINAL_POSITION]")
#     print(f"[PBI] DBSCHEMA_COLUMNS total: {len(all_col_rows)} rows")

#     if len(all_col_rows) <= 1:
#         # Row limit hit - fall back to per-table queries
#         print(f"[PBI] Column query truncated to {len(all_col_rows)} rows - switching to per-table queries")
#         for tbl in tables:
#             safe_name = tbl["name"].replace("'", "''")
#             col_rows = _query(token, workspace_id, dataset_id,
#                               f"SELECT [COLUMN_NAME], [DATA_TYPE] FROM $SYSTEM.DBSCHEMA_COLUMNS "
#                               f"WHERE [TABLE_NAME] = '{safe_name}'")
#             print(f"[PBI]   {tbl['name']}: {len(col_rows)} columns from per-table query")
#             # Log raw response if still only 1 row
#             if len(col_rows) <= 1 and col_rows:
#                 print(f"[PBI]   Raw col row: {col_rows[0]}")
#             for c in col_rows:
#                 cname = c.get("COLUMN_NAME", "")
#                 if cname and not cname.startswith("RowNumber"):
#                     tbl["columns"].append({"name": cname,
#                                            "dataType": str(c.get("DATA_TYPE", "unknown")),
#                                            "isHidden": False})
#     else:
#         # Normal path - distribute columns to tables
#         tbl_map = {t["name"]: t for t in tables}
#         for c in all_col_rows:
#             tname = c.get("TABLE_NAME", "")
#             cname = c.get("COLUMN_NAME", "")
#             if tname in tbl_map and cname and not cname.startswith("RowNumber"):
#                 tbl_map[tname]["columns"].append({"name": cname,
#                                                    "dataType": str(c.get("DATA_TYPE", "unknown")),
#                                                    "isHidden": False})

#     total = sum(len(t["columns"]) for t in tables)
#     print(f"[PBI] DBSCHEMA total columns: {total}")
#     for t in tables:
#         print(f"[PBI]   {t['name']}: {len(t['columns'])} cols -> {[c['name'] for c in t['columns'][:6]]}")

#     return tables, [], []


# # Strategy 4: DAX INFO() functions (Premium/Fabric XMLA)

# def _get_schema_via_dax_info(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
#     tables, measures, relationships = [], [], []
#     dtype_map = {"2":"string","6":"integer","8":"float","9":"decimal","10":"datetime","11":"boolean"}

#     tables_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.TABLES()")
#     print(f"[PBI] INFO.TABLES() -> {len(tables_rows)} rows")
#     table_id_map = {}
#     for t in tables_rows:
#         tid = t.get("ID")
#         tname = t.get("Name", "")
#         if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
#             continue
#         table_id_map[tid] = tname
#         tables.append({"name": tname, "isHidden": t.get("IsHidden", False), "columns": [], "description": ""})

#     col_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.COLUMNS()")
#     col_id_map = {}
#     for c in col_rows:
#         cname = c.get("ExplicitName") or c.get("Name", "")
#         if not cname or cname.startswith("RowNumber"):
#             continue
#         col_id_map[c.get("ID")] = cname
#         tname = table_id_map.get(c.get("TableID"))
#         if not tname:
#             continue
#         for tbl in tables:
#             if tbl["name"] == tname:
#                 tbl["columns"].append({"name": cname,
#                                        "dataType": dtype_map.get(str(c.get("DataType","")), "unknown"),
#                                        "isHidden": c.get("IsHidden", False)})
#                 break

#     meas_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.MEASURES()")
#     for m in meas_rows:
#         measures.append({"name": m.get("Name",""), "table": table_id_map.get(m.get("TableID"),"Unknown"),
#                          "expression": m.get("Expression",""), "formatString": m.get("FormatString",""),
#                          "description": ""})

#     rel_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.RELATIONSHIPS()")
#     for r in rel_rows:
#         relationships.append({"fromTable": table_id_map.get(r.get("FromTableID"),"?"),
#                                "fromColumn": col_id_map.get(r.get("FromColumnID"),"?"),
#                                "toTable": table_id_map.get(r.get("ToTableID"),"?"),
#                                "toColumn": col_id_map.get(r.get("ToColumnID"),"?")})

#     print(f"[PBI] INFO(): {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
#     return tables, measures, relationships


# # Main entry point

# def pull_full_metadata(token: str, dataset_id: str, dataset_name: str,
#                        workspace_id: Optional[str] = None,
#                        workspace_name: str = "My Workspace") -> dict:
#     print(f"\n[PBI] === Pulling: {dataset_name} | {workspace_name} ===")
#     print(f"[PBI] dataset_id={dataset_id} workspace_id={workspace_id}")

#     # Log all available datasets so user can verify they're connecting to the right one
#     if workspace_id:
#         try:
#             list_datasets(token, workspace_id)
#         except Exception:
#             pass

#     tables, measures, relationships = [], [], []

#     if workspace_id:
#         print("[PBI] -> Strategy 1: Admin Scanner API")
#         tables, measures, relationships = _get_schema_via_scanner(token, workspace_id, dataset_id)

#     if not tables and workspace_id:
#         print("[PBI] -> Strategy 2: TMSCHEMA views")
#         tables, measures, relationships = _get_schema_via_tmschema(token, workspace_id, dataset_id)

#     if not tables and workspace_id:
#         print("[PBI] -> Strategy 3: DBSCHEMA (SYSTEM TABLE filter)")
#         tables, measures, relationships = _get_schema_via_dbschema(token, workspace_id, dataset_id)

#     if not tables and workspace_id:
#         print("[PBI] -> Strategy 4: DAX INFO() functions")
#         tables, measures, relationships = _get_schema_via_dax_info(token, workspace_id, dataset_id)

#     datasources = get_datasources(token, dataset_id, workspace_id)
#     refresh_history = get_refresh_history(token, dataset_id, workspace_id)

#     print(f"[PBI] === Final: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels ===\n")

#     if not tables:
#         raise Exception(
#             "Could not extract schema.\n\n"
#             "MOST LIKELY: You are connecting to the wrong dataset ID.\n"
#             "Check the logs above for '[PBI] Datasets in workspace' to see all available\n"
#             "datasets and their IDs, then use the correct dataset_id in your connect request.\n\n"
#             "OTHER FIXES:\n"
#             "  1. Fresh token from DevTools (expires ~1hr)\n"
#             "  2. Must be workspace Member or Admin\n"
#             "  3. Enable 'XMLA Endpoints' in PBI Admin Portal -> Tenant Settings\n\n"
#             "WORKAROUND: POST /connect/manual with your schema JSON."
#         )

#     return {
#         "dataset_id": dataset_id,
#         "dataset_name": dataset_name,
#         "workspace_id": workspace_id,
#         "workspace_name": workspace_name,
#         "tables": tables,
#         "measures": measures,
#         "relationships": relationships,
#         "datasources": [{"type": d.get("datasourceType"), "connection": d.get("connectionDetails", {})}
#                         for d in datasources],
#         "refresh_history": refresh_history[:5],
#         "table_count": len(tables),
#         "measure_count": len(measures),
#         "relationship_count": len(relationships),
#     }


# core/pbi_connector.py
# Power BI REST API connector - no MSAL, uses raw Bearer token
#
# KEY INSIGHT: Power BI DMV TABLE_TYPE is counterintuitive:
#   'SYSTEM TABLE' = actual user data tables
#   'TABLE'        = internal $-prefixed shadow copies
#   'SCHEMA'       = DMV catalog views

import os
import json
import time
import requests
from typing import Optional

BASE_URL = os.getenv("POWERBI_BASE_URL", "https://api.powerbi.com/v1.0/myorg")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get(url: str, token: str) -> dict:
    resp = requests.get(url, headers=_headers(token), timeout=30)
    print(f"[PBI] GET {resp.status_code} -> {url.split('myorg/')[-1]}")
    if not resp.ok:
        print(f"[PBI] Error: {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json()


def _post(url: str, token: str, payload: dict) -> dict:
    resp = requests.post(url, headers=_headers(token), json=payload, timeout=60)
    print(f"[PBI] POST {resp.status_code} -> {url.split('myorg/')[-1]}")
    if not resp.ok:
        print(f"[PBI] Error: {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json()


def _execute_query(token: str, workspace_id: str, dataset_id: str, dax: str) -> dict:
    url = f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
    payload = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    resp = requests.post(url, headers=_headers(token), json=payload, timeout=30)
    print(f"[PBI] DAX {resp.status_code} -> {dax[:80]}")
    if not resp.ok:
        print(f"[PBI] DAX Error: {resp.text[:300]}")
        return {}
    try:
        return resp.json()
    except Exception as e:
        print(f"[PBI] DAX JSON parse error: {e}")
        return {}


def _parse_query_response(raw: dict) -> list[dict]:
    """Parse executeQueries response, stripping key prefixes."""
    if not raw:
        return []
    try:
        result_tables = raw["results"][0]["tables"]
        if not result_tables:
            return []
        rows = result_tables[0].get("rows", [])
        cleaned = []
        for row in rows:
            clean_row = {}
            for k, v in row.items():
                if "].[" in k:
                    clean_key = k.split("].[")[-1].rstrip("]")
                elif k.startswith("[") and k.endswith("]"):
                    clean_key = k[1:-1]
                else:
                    clean_key = k
                clean_row[clean_key] = v
            cleaned.append(clean_row)
        return cleaned
    except (KeyError, IndexError, TypeError) as e:
        print(f"[PBI] Response parse error: {e}")
        try:
            print(f"[PBI] Raw: {json.dumps(raw, default=str)[:600]}")
        except Exception:
            pass
        return []


def _query(token: str, workspace_id: str, dataset_id: str, dax: str) -> list[dict]:
    return _parse_query_response(_execute_query(token, workspace_id, dataset_id, dax))


# Public helpers

def list_workspaces(token: str) -> list[dict]:
    return _get(f"{BASE_URL}/groups", token).get("value", [])


def list_datasets(token: str, workspace_id: Optional[str] = None) -> list[dict]:
    """List all datasets. Enriches each with configuredBy and isRefreshable."""
    url = (f"{BASE_URL}/groups/{workspace_id}/datasets"
           if workspace_id else f"{BASE_URL}/datasets")
    datasets = _get(url, token).get("value", [])
    # Log all datasets to help user identify the correct one
    print(f"[PBI] Datasets in workspace ({len(datasets)} found):")
    for ds in datasets:
        print(f"[PBI]   id={ds.get('id')} | name={repr(ds.get('name'))} | "
              f"configuredBy={ds.get('configuredBy')} | "
              f"isRefreshable={ds.get('isRefreshable')} | "
              f"targetStorageMode={ds.get('targetStorageMode')}")
    return datasets


def get_datasources(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
    url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/datasources"
           if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/datasources")
    try:
        return _get(url, token).get("value", [])
    except Exception:
        return []


def get_refresh_history(token: str, dataset_id: str, workspace_id: Optional[str] = None) -> list[dict]:
    url = (f"{BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
           if workspace_id else f"{BASE_URL}/datasets/{dataset_id}/refreshes")
    try:
        return _get(url, token).get("value", [])
    except Exception:
        return []


# Strategy 1: Admin Scanner API

def _get_schema_via_scanner(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
    tables, measures, relationships = [], [], []
    try:
        scan_resp = _post(
            f"{BASE_URL}/admin/workspaces/getInfo"
            "?lineage=true&datasourceDetails=true&datasetSchema=true&datasetExpressions=true",
            token, {"workspaces": [workspace_id]}
        )
        scan_id = scan_resp.get("id")
        if not scan_id:
            return [], [], []
        print(f"[PBI] Scanner ID: {scan_id} - polling...")
        for i in range(8):
            time.sleep(4)
            status = _get(f"{BASE_URL}/admin/workspaces/scanStatus/{scan_id}", token).get("status", "")
            print(f"[PBI] Scanner poll {i+1}: {status}")
            if status == "Succeeded":
                break
        else:
            return [], [], []
        result = _get(f"{BASE_URL}/admin/workspaces/scanResult/{scan_id}", token)
        for ws in result.get("workspaces", []):
            for ds in ws.get("datasets", []):
                if ds.get("id") != dataset_id:
                    continue
                for t in ds.get("tables", []):
                    tname = t.get("name", "")
                    if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
                        continue
                    columns = [
                        {"name": c.get("name",""), "dataType": c.get("dataType","unknown"),
                         "isHidden": c.get("isHidden", False), "description": c.get("description","")}
                        for c in t.get("columns", [])
                        if c.get("name") and not c.get("name","").startswith("RowNumber")
                    ]
                    for m in t.get("measures", []):
                        measures.append({"name": m.get("name",""), "table": tname,
                                         "expression": m.get("expression",""),
                                         "formatString": m.get("formatString",""),
                                         "description": m.get("description","")})
                    tables.append({"name": tname, "columns": columns,
                                   "isHidden": t.get("isHidden", False),
                                   "description": t.get("description","")})
                for r in ds.get("relationships", []):
                    relationships.append({"fromTable": r.get("fromTable","?"),
                                          "fromColumn": r.get("fromColumn","?"),
                                          "toTable": r.get("toTable","?"),
                                          "toColumn": r.get("toColumn","?"),
                                          "crossFilteringBehavior": r.get("crossFilteringBehavior","oneDirection")})
        print(f"[PBI] Scanner: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
    except Exception as e:
        print(f"[PBI] Scanner failed: {e}")
        return [], [], []
    return tables, measures, relationships


# Strategy 2: TMSCHEMA views

def _get_schema_via_tmschema(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
    tables, measures, relationships = [], [], []

    tbl_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_TABLES")
    print(f"[PBI] TMSCHEMA_TABLES -> {len(tbl_rows)} rows")

    table_id_map = {}
    for t in tbl_rows:
        tid   = t.get("ID")
        tname = t.get("Name", "")
        if tname.startswith(("DateTableTemplate", "LocalDateTable")):
            continue
        table_id_map[tid] = tname
        tables.append({"name": tname, "columns": [], "isHidden": t.get("IsHidden", False),
                       "description": t.get("Description", "")})

    print(f"[PBI] TMSCHEMA tables: {len(tables)} -> {[t['name'] for t in tables]}")
    if not tables:
        return [], [], []

    dtype_map = {"2":"string","6":"integer","8":"float","9":"decimal",
                 "10":"datetime","11":"boolean","17":"binary","19":"variant"}

    col_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_COLUMNS")
    print(f"[PBI] TMSCHEMA_COLUMNS -> {len(col_rows)} rows")
    col_id_map = {}
    for c in col_rows:
        cname = c.get("ExplicitName") or c.get("Name", "")
        if not cname or cname.startswith("RowNumber") or c.get("Type") == 3:
            continue
        col_id_map[c.get("ID")] = cname
        tname = table_id_map.get(c.get("TableID"))
        if not tname:
            continue
        dtype = dtype_map.get(str(c.get("ExplicitDataType") or c.get("DataType") or ""), "unknown")
        for tbl in tables:
            if tbl["name"] == tname:
                tbl["columns"].append({"name": cname, "dataType": dtype,
                                       "isHidden": c.get("IsHidden", False),
                                       "description": c.get("Description", "")})
                break

    meas_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_MEASURES")
    print(f"[PBI] TMSCHEMA_MEASURES -> {len(meas_rows)} rows")
    for m in meas_rows:
        mname = m.get("Name", "")
        if not mname or mname.startswith("_"):
            continue
        measures.append({"name": mname, "table": table_id_map.get(m.get("TableID"), "Unknown"),
                         "expression": m.get("Expression", ""), "formatString": m.get("FormatString", ""),
                         "description": m.get("Description", "")})

    rel_rows = _query(token, workspace_id, dataset_id, "SELECT * FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS")
    print(f"[PBI] TMSCHEMA_RELATIONSHIPS -> {len(rel_rows)} rows")
    for r in rel_rows:
        relationships.append({
            "fromTable":  table_id_map.get(r.get("FromTableID"), str(r.get("FromTableID"))),
            "fromColumn": col_id_map.get(r.get("FromColumnID"), str(r.get("FromColumnID"))),
            "toTable":    table_id_map.get(r.get("ToTableID"), str(r.get("ToTableID"))),
            "toColumn":   col_id_map.get(r.get("ToColumnID"), str(r.get("ToColumnID"))),
            "crossFilteringBehavior": r.get("CrossFilteringBehavior", "oneDirection"),
        })

    print(f"[PBI] TMSCHEMA final: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
    return tables, measures, relationships


# Strategy 3: DBSCHEMA with correct SYSTEM TABLE filter + all-columns query

def _get_schema_via_dbschema(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
    """
    In Power BI DMV, TABLE_TYPE='SYSTEM TABLE' = actual user tables (counterintuitive).
    Fetches ALL columns in one query (no WHERE) to avoid per-table row-limit issues.
    """
    tables, measures, relationships = [], [], []

    table_rows = _query(token, workspace_id, dataset_id,
                        "SELECT [TABLE_NAME], [TABLE_TYPE] FROM $SYSTEM.DBSCHEMA_TABLES")

    user_table_names = set()
    for r in table_rows:
        tname = r.get("TABLE_NAME", "")
        ttype = r.get("TABLE_TYPE", "")
        if ttype == "SYSTEM TABLE" and tname and not tname.startswith(("DateTableTemplate", "LocalDateTable")):
            user_table_names.add(tname)
            tables.append({"name": tname, "columns": [], "isHidden": False, "description": ""})

    print(f"[PBI] DBSCHEMA user tables: {len(tables)} -> {[t['name'] for t in tables]}")
    if not tables:
        return [], [], []

    # DBSCHEMA_COLUMNS is restricted on this tenant - only returns __Count aggregates.
    # Instead: query TOPN(1, Table) to get a real data row and read column names from keys.
    # This works because executeQueries CAN run DAX against the data, just not schema DMVs.
    print(f"[PBI] DBSCHEMA_COLUMNS blocked - inferring columns from TOPN(1) DAX queries")
    for tbl in tables:
        tname = tbl["name"]
        # Escape table name for DAX - wrap in single quotes
        safe_name = tname.replace("'", "''")
        raw = _execute_query(token, workspace_id, dataset_id,
                             f"EVALUATE TOPN(1, '{safe_name}')")
        if not raw:
            print(f"[PBI]   {tname}: DAX query failed")
            continue
        try:
            result_tables = raw["results"][0]["tables"]
            if not result_tables:
                print(f"[PBI]   {tname}: empty result")
                continue
            rows = result_tables[0].get("rows", [])
            if not rows:
                # Table exists but has 0 rows - get columns from the columns metadata
                # Try with no rows: TOPN(0,...) returns schema even for empty tables
                raw2 = _execute_query(token, workspace_id, dataset_id,
                                      f"EVALUATE TOPN(0, '{safe_name}')")
                if raw2:
                    try:
                        cols_meta = raw2["results"][0]["tables"][0].get("columns", [])
                        for col_meta in cols_meta:
                            cname = col_meta.get("name", "")
                            dtype = col_meta.get("dataType", "unknown")
                            if cname and not cname.startswith(("RowNumber", "__")):
                                tbl["columns"].append({"name": cname, "dataType": dtype, "isHidden": False})
                        print(f"[PBI]   {tname}: {len(tbl['columns'])} cols (from schema, 0 rows)")
                        continue
                    except Exception:
                        pass
                print(f"[PBI]   {tname}: 0 rows in table")
                continue
            # Read column names from row keys - format is "[TableName].[ColumnName]"
            sample_row = rows[0]
            for k in sample_row.keys():
                # Strip table prefix - TOPN returns keys as:
                #   "Table[Column]"      -> strip up to "["
                #   "[Table].[Column]"   -> take last segment
                #   "[Column]"           -> strip brackets
                if "][" in k:
                    # Format: "Table[Column]" or "[Table][Column]"
                    cname = k.split("[")[-1].rstrip("]")
                elif "].[" in k:
                    # Format: "[Table].[Column]"
                    cname = k.split("].[",-1)[-1].rstrip("]")
                elif k.startswith("[") and k.endswith("]"):
                    cname = k[1:-1]
                else:
                    cname = k
                if cname and not cname.startswith(("RowNumber", "__")):
                    # Infer datatype from value
                    val = sample_row[k]
                    if isinstance(val, bool):
                        dtype = "boolean"
                    elif isinstance(val, int):
                        dtype = "integer"
                    elif isinstance(val, float):
                        dtype = "decimal"
                    else:
                        dtype = "string"
                    tbl["columns"].append({"name": cname, "dataType": dtype, "isHidden": False})
            print(f"[PBI]   {tname}: {len(tbl['columns'])} cols -> {[c['name'] for c in tbl['columns'][:5]]}")
        except Exception as e:
            print(f"[PBI]   {tname}: parse error: {e}")

    total = sum(len(t["columns"]) for t in tables)
    print(f"[PBI] TOPN column inference total: {total} columns across {len(tables)} tables")

    return tables, [], []


# Strategy 4: DAX INFO() functions (Premium/Fabric XMLA)

def _get_schema_via_dax_info(token: str, workspace_id: str, dataset_id: str) -> tuple[list, list, list]:
    tables, measures, relationships = [], [], []
    dtype_map = {"2":"string","6":"integer","8":"float","9":"decimal","10":"datetime","11":"boolean"}

    tables_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.TABLES()")
    print(f"[PBI] INFO.TABLES() -> {len(tables_rows)} rows")
    table_id_map = {}
    for t in tables_rows:
        tid = t.get("ID")
        tname = t.get("Name", "")
        if tname.startswith(("DateTableTemplate", "LocalDateTable", "$")):
            continue
        table_id_map[tid] = tname
        tables.append({"name": tname, "isHidden": t.get("IsHidden", False), "columns": [], "description": ""})

    col_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.COLUMNS()")
    col_id_map = {}
    for c in col_rows:
        cname = c.get("ExplicitName") or c.get("Name", "")
        if not cname or cname.startswith("RowNumber"):
            continue
        col_id_map[c.get("ID")] = cname
        tname = table_id_map.get(c.get("TableID"))
        if not tname:
            continue
        for tbl in tables:
            if tbl["name"] == tname:
                tbl["columns"].append({"name": cname,
                                       "dataType": dtype_map.get(str(c.get("DataType","")), "unknown"),
                                       "isHidden": c.get("IsHidden", False)})
                break

    meas_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.MEASURES()")
    for m in meas_rows:
        measures.append({"name": m.get("Name",""), "table": table_id_map.get(m.get("TableID"),"Unknown"),
                         "expression": m.get("Expression",""), "formatString": m.get("FormatString",""),
                         "description": ""})

    rel_rows = _query(token, workspace_id, dataset_id, "EVALUATE INFO.RELATIONSHIPS()")
    for r in rel_rows:
        relationships.append({"fromTable": table_id_map.get(r.get("FromTableID"),"?"),
                               "fromColumn": col_id_map.get(r.get("FromColumnID"),"?"),
                               "toTable": table_id_map.get(r.get("ToTableID"),"?"),
                               "toColumn": col_id_map.get(r.get("ToColumnID"),"?")})

    print(f"[PBI] INFO(): {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels")
    return tables, measures, relationships


# Main entry point

def pull_full_metadata(token: str, dataset_id: str, dataset_name: str,
                       workspace_id: Optional[str] = None,
                       workspace_name: str = "My Workspace") -> dict:
    print(f"\n[PBI] === Pulling: {dataset_name} | {workspace_name} ===")
    print(f"[PBI] dataset_id={dataset_id} workspace_id={workspace_id}")

    # Log all available datasets so user can verify they're connecting to the right one
    if workspace_id:
        try:
            list_datasets(token, workspace_id)
        except Exception:
            pass

    tables, measures, relationships = [], [], []

    if workspace_id:
        print("[PBI] -> Strategy 1: Admin Scanner API")
        tables, measures, relationships = _get_schema_via_scanner(token, workspace_id, dataset_id)

    if not tables and workspace_id:
        print("[PBI] -> Strategy 2: TMSCHEMA views")
        tables, measures, relationships = _get_schema_via_tmschema(token, workspace_id, dataset_id)

    if not tables and workspace_id:
        print("[PBI] -> Strategy 3: DBSCHEMA (SYSTEM TABLE filter)")
        tables, measures, relationships = _get_schema_via_dbschema(token, workspace_id, dataset_id)

    if not tables and workspace_id:
        print("[PBI] -> Strategy 4: DAX INFO() functions")
        tables, measures, relationships = _get_schema_via_dax_info(token, workspace_id, dataset_id)

    datasources = get_datasources(token, dataset_id, workspace_id)
    refresh_history = get_refresh_history(token, dataset_id, workspace_id)

    print(f"[PBI] === Final: {len(tables)} tables, {len(measures)} measures, {len(relationships)} rels ===\n")

    if not tables:
        raise Exception(
            "Could not extract schema.\n\n"
            "MOST LIKELY: You are connecting to the wrong dataset ID.\n"
            "Check the logs above for '[PBI] Datasets in workspace' to see all available\n"
            "datasets and their IDs, then use the correct dataset_id in your connect request.\n\n"
            "OTHER FIXES:\n"
            "  1. Fresh token from DevTools (expires ~1hr)\n"
            "  2. Must be workspace Member or Admin\n"
            "  3. Enable 'XMLA Endpoints' in PBI Admin Portal -> Tenant Settings\n\n"
            "WORKAROUND: POST /connect/manual with your schema JSON."
        )

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "tables": tables,
        "measures": measures,
        "relationships": relationships,
        "datasources": [{"type": d.get("datasourceType"), "connection": d.get("connectionDetails", {})}
                        for d in datasources],
        "refresh_history": refresh_history[:5],
        "table_count": len(tables),
        "measure_count": len(measures),
        "relationship_count": len(relationships),
    }