# prompts/templates.py
# ─────────────────────────────────────────────────────────────────────────────
# ALL GPT-4o prompt templates for AutoDocAI
# Each function returns a (system_prompt, user_prompt) tuple
# ─────────────────────────────────────────────────────────────────────────────

def brd_prompt(metadata: dict) -> tuple[str, str]:
    system = """You are a senior business analyst writing a Business Requirements Document (BRD).
Write in clear, professional business language — avoid technical jargon.
Audience: Project Managers, Business Stakeholders, Product Owners.
Structure your response with these exact sections:
1. Executive Summary
2. Business Objectives
3. Scope & Boundaries
4. Key Data Entities (describe in business terms)
5. Business Rules & KPIs
6. Stakeholders & Users
7. Assumptions & Constraints
Use full sentences and paragraphs. Do not use bullet-only sections."""

    user = f"""Generate a complete Business Requirements Document based on this Power BI semantic model metadata:

PROJECT NAME: {metadata.get('dataset_name', 'Unnamed Dataset')}
WORKSPACE: {metadata.get('workspace_name', 'Unknown Workspace')}

TABLES & COLUMNS:
{_format_tables(metadata.get('tables', []))}

MEASURES & KPIs:
{_format_measures(metadata.get('measures', []))}

RELATIONSHIPS:
{_format_relationships(metadata.get('relationships', []))}

Write the full BRD now."""
    return system, user


def tdd_prompt(metadata: dict) -> tuple[str, str]:
    system = """You are a senior data engineer writing a Technical Design Document (TDD).
Write in precise technical language with full detail.
Audience: Data Engineers, BI Developers, Database Architects.
Structure your response with these exact sections:
1. Technical Overview & Architecture
2. Data Model Design (tables, columns, data types, keys)
3. DAX Measures — Logic Explained (explain each measure's calculation in plain English)
4. Relationships & Cardinality
5. Data Flow & Lineage
6. Performance Considerations
7. Technical Constraints & Dependencies
Include code snippets for DAX where relevant."""

    user = f"""Generate a complete Technical Design Document for this Power BI semantic model:

DATASET: {metadata.get('dataset_name', 'Unnamed')}
WORKSPACE: {metadata.get('workspace_name', 'Unknown')}

TABLES WITH FULL SCHEMA:
{_format_tables_detailed(metadata.get('tables', []))}

DAX MEASURES:
{_format_measures_detailed(metadata.get('measures', []))}

RELATIONSHIPS:
{_format_relationships(metadata.get('relationships', []))}

Write the complete TDD now."""
    return system, user


def fdd_prompt(metadata: dict) -> tuple[str, str]:
    system = """You are a business analyst writing a Functional Design Document (FDD).
Bridge the gap between business requirements and technical implementation.
Audience: Business Analysts, QA Teams, Project Managers.
Structure your response with these exact sections:
1. Functional Overview
2. Data Sources & Inputs
3. Transformations & Business Logic
4. Calculated Metrics — Functional Description
5. Report & Dashboard Functional Specs
6. Data Validation Rules
7. User Interaction & Functional Flows"""

    user = f"""Generate a Functional Design Document for this Power BI model:

DATASET: {metadata.get('dataset_name', 'Unnamed')}

TABLES: {_format_tables(metadata.get('tables', []))}
MEASURES: {_format_measures(metadata.get('measures', []))}
RELATIONSHIPS: {_format_relationships(metadata.get('relationships', []))}

Write the complete FDD now."""
    return system, user


def s2t_prompt(metadata: dict) -> tuple[str, str]:
    system = """You are a data integration specialist creating a Source-to-Target (S2T) mapping document.
Be precise and structured. Output a detailed mapping table.
Format each mapping as:
SOURCE TABLE | SOURCE COLUMN | DATA TYPE | TARGET TABLE | TARGET COLUMN | TRANSFORMATION RULE | BUSINESS DESCRIPTION
If transformation rule is unknown, write 'Direct mapping' or infer from column name/DAX logic.
After the table, write a brief narrative explaining the overall data lineage."""

    user = f"""Create a complete Source-to-Target mapping document for this Power BI semantic model.
Infer source systems from table/column names and relationships.

DATASET: {metadata.get('dataset_name', 'Unnamed')}

TABLES & COLUMNS:
{_format_tables_detailed(metadata.get('tables', []))}

MEASURES (may derive from source columns):
{_format_measures(metadata.get('measures', []))}

RELATIONSHIPS (shows how tables connect):
{_format_relationships(metadata.get('relationships', []))}

Generate the complete S2T mapping now."""
    return system, user


def qa_report_prompt(metadata: dict, validation_results: dict | None = None) -> tuple[str, str]:
    system = """You are a QA lead writing a Data Validation Report.
Be thorough and flag potential data quality issues.
Structure your response with:
1. QA Executive Summary
2. Data Completeness Check (tables, columns, measures coverage)
3. Relationship Integrity Analysis
4. DAX Logic Validation (flag complex or potentially incorrect measures)
5. Naming Convention Compliance
6. Potential Data Quality Risks
7. Recommendations
Rate overall data quality: HIGH / MEDIUM / LOW with justification."""

    validation_str = ""
    if validation_results:
        validation_str = f"\nVALIDATION TEST RESULTS:\n{validation_results}\n"

    user = f"""Generate a QA Validation Report for this Power BI semantic model:

DATASET: {metadata.get('dataset_name', 'Unnamed')}
{validation_str}
TABLES: {_format_tables_detailed(metadata.get('tables', []))}
MEASURES: {_format_measures_detailed(metadata.get('measures', []))}
RELATIONSHIPS: {_format_relationships(metadata.get('relationships', []))}

Write the complete QA report with findings and recommendations."""
    return system, user


def audit_score_prompt(metadata: dict, generated_docs: dict) -> tuple[str, str]:
    system = """You are a data governance auditor scoring documentation completeness.
Be critical and objective. Score each category out of 100.
Return your response as valid JSON matching this exact schema:
{
  "overall_score": <int 0-100>,
  "grade": "<A/B/C/D/F>",
  "categories": {
    "data_model_documentation": {"score": <int>, "findings": "<string>", "gaps": ["<string>"]},
    "business_context": {"score": <int>, "findings": "<string>", "gaps": ["<string>"]},
    "technical_completeness": {"score": <int>, "findings": "<string>", "gaps": ["<string>"]},
    "naming_conventions": {"score": <int>, "findings": "<string>", "gaps": ["<string>"]},
    "relationship_documentation": {"score": <int>, "findings": "<string>", "gaps": ["<string>"]},
    "measure_documentation": {"score": <int>, "findings": "<string>", "gaps": ["<string>"}
  },
  "top_risks": ["<string>", "<string>", "<string>"],
  "recommendations": ["<string>", "<string>", "<string>"]
}
Return ONLY valid JSON, no markdown, no preamble."""

    docs_summary = {k: "generated" if v else "missing" for k, v in generated_docs.items()}

    user = f"""Score the audit-readiness of this Power BI project documentation:

DATASET: {metadata.get('dataset_name', 'Unnamed')}
TABLE COUNT: {len(metadata.get('tables', []))}
MEASURE COUNT: {len(metadata.get('measures', []))}
RELATIONSHIP COUNT: {len(metadata.get('relationships', []))}

DOCUMENTS GENERATED: {docs_summary}

TABLES (check for undescribed columns):
{_format_tables(metadata.get('tables', []))}

MEASURES (check for undocumented logic):
{_format_measures(metadata.get('measures', []))}

Score the documentation now. Return JSON only."""
    return system, user


def chat_prompt(metadata: dict, conversation_history: list[dict], user_question: str) -> tuple[str, str]:
    system = f"""You are AutoDocAI Assistant — an expert on this specific Power BI project.
You have complete knowledge of the data model below. Answer questions accurately and concisely.
If asked about something not in the metadata, say so clearly.

=== PROJECT METADATA ===
DATASET: {metadata.get('dataset_name', 'Unnamed')}
WORKSPACE: {metadata.get('workspace_name', 'Unknown')}

TABLES:
{_format_tables_detailed(metadata.get('tables', []))}

MEASURES:
{_format_measures_detailed(metadata.get('measures', []))}

RELATIONSHIPS:
{_format_relationships(metadata.get('relationships', []))}
=== END METADATA ===

Be specific. Reference actual table/column/measure names in your answers."""

    return system, user_question


def diff_narrative_prompt(old_metadata: dict, new_metadata: dict, diff_summary: dict) -> tuple[str, str]:
    system = """You are a technical writer explaining what changed in a Power BI model between two versions.
Write a clear, concise change summary in 3 sections:
1. Summary of Changes (1-2 sentences, high level)
2. Detailed Changes (what was added, modified, or removed)
3. Impact Assessment (what documentation needs to be updated and why)
Be specific about table names, column names, and measure names."""

    user = f"""Explain the changes between these two versions of a Power BI model:

DATASET: {old_metadata.get('dataset_name', 'Unnamed')}

CHANGES DETECTED:
{diff_summary}

OLD VERSION SUMMARY: {len(old_metadata.get('tables', []))} tables, {len(old_metadata.get('measures', []))} measures
NEW VERSION SUMMARY: {len(new_metadata.get('tables', []))} tables, {len(new_metadata.get('measures', []))} measures

Write the change narrative now."""
    return system, user


# ─── Private formatting helpers ─────────────────────────────────────────────

def _format_tables(tables: list) -> str:
    if not tables:
        return "No tables found."
    lines = []
    for t in tables:
        col_names = [c.get('name', '') for c in t.get('columns', [])]
        lines.append(f"  • {t.get('name', 'Unknown')}: [{', '.join(col_names[:10])}{'...' if len(col_names) > 10 else ''}]")
    return "\n".join(lines)


def _format_tables_detailed(tables: list) -> str:
    if not tables:
        return "No tables found."
    lines = []
    for t in tables:
        lines.append(f"\nTABLE: {t.get('name', 'Unknown')}")
        for col in t.get('columns', []):
            dtype = col.get('dataType', 'unknown')
            lines.append(f"    - {col.get('name', '?')} [{dtype}]")
    return "\n".join(lines)


def _format_measures(measures: list) -> str:
    if not measures:
        return "No measures found."
    lines = []
    for m in measures[:30]:  # cap to avoid token overflow
        lines.append(f"  • {m.get('name', '?')}: {m.get('expression', 'N/A')[:120]}")
    if len(measures) > 30:
        lines.append(f"  ... and {len(measures) - 30} more measures")
    return "\n".join(lines)


def _format_measures_detailed(measures: list) -> str:
    if not measures:
        return "No measures found."
    lines = []
    for m in measures[:25]:
        lines.append(f"\nMEASURE: {m.get('name', '?')}")
        lines.append(f"  Table: {m.get('table', 'Unknown')}")
        lines.append(f"  DAX: {m.get('expression', 'N/A')[:200]}")
    if len(measures) > 25:
        lines.append(f"\n... and {len(measures) - 25} more measures")
    return "\n".join(lines)


def _format_relationships(relationships: list) -> str:
    if not relationships:
        return "No relationships found."
    lines = []
    for r in relationships:
        lines.append(
            f"  • {r.get('fromTable', '?')}[{r.get('fromColumn', '?')}] → "
            f"{r.get('toTable', '?')}[{r.get('toColumn', '?')}] "
            f"({r.get('crossFilteringBehavior', 'single')})"
        )
    return "\n".join(lines)
