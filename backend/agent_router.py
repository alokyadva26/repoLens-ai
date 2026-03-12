"""
agent_router.py
---------------
RepoLens AI — Tool-Using Agent Router.

The router acts as the orchestration layer for the ``POST /agent/query``
and ``POST /agent/compare`` endpoints.  It analyses the user's question,
picks the most appropriate RepoLens tool, runs it, and returns a structured
response that includes both the tool name and the answer it produced.

Public API
----------
    detect_intent(question: str) -> str
    route_tool(intent: str, repo_data: dict, question: str) -> dict
    compare_repositories(repo_memory: dict[str, dict], question: str) -> str
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------
# Rules are evaluated in order — the first match wins.
# Compare/cross-repo questions are checked FIRST so they don't accidentally
# match architecture/security rules.
# ---------------------------------------------------------------------------

_INTENT_RULES: list[tuple[list[str], str]] = [
    # Cross-repository comparison — must be first so it wins over other rules
    (
        ["compare", "comparison", "difference", "which repo", "which is better",
         "better than", "vs ", "versus", "across repos", "all repos",
         "between repos", "repos have", "repositories"],
        "compare_repos",
    ),
    # Installation / running the project
    (
        ["run", "install", "setup", "start", "launch", "deploy",
         "get started", "how to use", "getting started", "build"],
        "documentation",
    ),
    # Architecture and structural design
    (
        ["architect", "structure", "design", "layer", "pattern",
         "how is it organised", "how is it organized", "folder",
         "module", "component", "layout"],
        "architecture",
    ),
    # Security and vulnerability analysis
    (
        ["security", "risk", "vulnerability", "vulnerabilities", "exploit", "safe",
         "threat", "credentials", "injection", "attack", "cve"],
        "code_review",
    ),
    # Tech stack, frameworks and languages
    (
        ["framework", "tech stack", "library", "language", "built with",
         "technology", "dependencies", "package", "tools", "stack"],
        "insights",
    ),
    # Project purpose and overview
    (
        ["what does", "what is", "purpose", "overview", "about",
         "describe", "explain", "summary", "goal", "objective"],
        "summary",
    ),
    # Performance and quality
    (
        ["performance", "speed", "optimis", "optimiz", "slow", "fast",
         "quality", "score", "best practice", "improve", "memory"],
        "code_review",
    ),
    # Complexity and development effort
    (
        ["complex", "difficult", "hard", "effort", "how long",
         "estimate", "time to build", "dev time"],
        "insights",
    ),
]


def detect_intent(question: str) -> str:
    """
    Classify the user's question into one of the available tool intents.

    Uses ordered keyword matching against ``_INTENT_RULES``.  The first rule
    whose trigger keywords contain a substring match against the lower-cased
    question wins.  If no rule matches, the intent falls back to ``"rag"``
    which triggers the full semantic-retrieval pipeline.

    Args:
        question: The user's plain-English question string.

    Returns:
        One of: ``"compare_repos"``, ``"documentation"``, ``"architecture"``,
        ``"code_review"``, ``"insights"``, ``"summary"``, or ``"rag"``.
    """
    if not question or not question.strip():
        return "rag"

    q_lower = question.lower()

    for trigger_keywords, intent in _INTENT_RULES:
        if any(kw in q_lower for kw in trigger_keywords):
            return intent

    return "rag"   # semantic fallback


# ---------------------------------------------------------------------------
# Safe nested accessors
# ---------------------------------------------------------------------------

def _safe(data: dict, *keys, default=""):
    """Safely traverse nested dicts; return default on any missing key."""
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur if cur is not None else default


def _safe_list(data: dict, *keys) -> list:
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return []
        cur = cur.get(k, [])
    return cur if isinstance(cur, list) else []


def _fmt_list(items: list, bullet: str = "• ") -> str:
    """Format a list of strings as a readable bulleted block."""
    if not items:
        return "No information available."
    return "\n" + "\n".join(f"{bullet}{item}" for item in items)


# ---------------------------------------------------------------------------
# Single-repo tool implementations
# ---------------------------------------------------------------------------

def _tool_summary(repo_data: dict) -> str:
    summary = _safe(repo_data, "summary")
    purpose = _safe(repo_data, "readme_analysis", "purpose")
    if summary and summary != "Summary not available.":
        return summary
    if purpose:
        return purpose
    return "No project summary is available for this repository."


def _tool_documentation(repo_data: dict) -> str:
    steps = _safe_list(repo_data, "documentation", "installation_steps")
    usage = _safe_list(repo_data, "documentation", "usage_guide")
    parts: list[str] = []
    if steps:
        parts.append("Installation steps:" + _fmt_list(steps))
    if usage:
        parts.append("Usage guide:" + _fmt_list(usage))
    if parts:
        return "\n\n".join(parts)
    setup = _safe(repo_data, "readme_analysis", "setup")
    return setup or "No installation or usage information found in this repository."


def _tool_architecture(repo_data: dict) -> str:
    explanation = _safe(repo_data, "architecture", "explanation")
    layers      = _safe_list(repo_data, "architecture", "layers")
    structure   = _safe_list(repo_data, "architecture", "structure")
    parts: list[str] = []
    if explanation:
        parts.append(explanation)
    if layers:
        parts.append("Architectural layers:" + _fmt_list(layers))
    if structure:
        parts.append("Top-level structure:" + _fmt_list(structure))
    if parts:
        return "\n\n".join(parts)
    hint = _safe(repo_data, "insights", "architecture_hint")
    return hint or "No architecture information is available for this repository."


def _tool_code_review(repo_data: dict) -> str:
    risks    = _safe_list(repo_data, "code_review", "security_risks")
    perf     = _safe_list(repo_data, "code_review", "performance_notes")
    practice = _safe_list(repo_data, "code_review", "best_practices")
    score    = (repo_data.get("code_review") or {}).get("quality_score")
    parts: list[str] = []
    if score is not None:
        parts.append(f"Code quality score: {score}/10")
    if risks:
        parts.append("Security risks:" + _fmt_list(risks))
    if perf:
        parts.append("Performance notes:" + _fmt_list(perf))
    if practice:
        parts.append("Best practices:" + _fmt_list(practice))
    return "\n\n".join(parts) if parts else "No code review information is available."


def _tool_insights(repo_data: dict) -> str:
    project_type = _safe(repo_data, "insights", "project_type")
    tech_stack   = _safe_list(repo_data, "insights", "tech_stack")
    frameworks   = _safe_list(repo_data, "insights", "frameworks")
    difficulty   = _safe(repo_data, "insights", "complexity", "difficulty")
    dev_time     = _safe(repo_data, "insights", "complexity", "estimated_dev_time")
    parts: list[str] = []
    if project_type:
        parts.append(f"Project type: {project_type}")
    if tech_stack:
        parts.append("Tech stack:" + _fmt_list(tech_stack))
    if frameworks:
        parts.append("Frameworks / libraries:" + _fmt_list(frameworks))
    if difficulty:
        parts.append(f"Complexity: {difficulty}" + (f" — estimated dev time: {dev_time}" if dev_time else ""))
    return "\n\n".join(parts) if parts else "No insight information is available."


def _tool_rag(question: str, repo_data: dict) -> str:
    """
    Run the full RAG pipeline — build chunks → embed → index → retrieve → answer.
    Imported locally to avoid circular imports at module level.
    """
    try:
        from ai_engine import (
            build_repo_knowledge,
            generate_embeddings,
            build_vector_index,
            retrieve_context,
            generate_rag_answer,
            _TFIDFEmbedder,
        )
        chunks     = build_repo_knowledge(repo_data)
        embeddings = generate_embeddings(chunks)
        index      = build_vector_index(embeddings)
        embedder   = embeddings if isinstance(embeddings, _TFIDFEmbedder) else None
        context    = retrieve_context(question, chunks, index, embedder=embedder, top_k=3)
        result     = generate_rag_answer(question, context)
        return result.get("answer", "No answer could be generated.")
    except Exception as exc:
        return f"The RAG agent encountered an error: {exc}"


# ---------------------------------------------------------------------------
# Cross-repository comparison tool
# ---------------------------------------------------------------------------

def compare_repositories(repo_memory: dict[str, dict], question: str = "") -> str:
    """
    Generate a structured comparison of all repositories currently in memory.

    Compares across five dimensions:
    - Project type and purpose
    - Tech stack and frameworks
    - Architecture pattern
    - Code quality score and security risks
    - Complexity and estimated development time

    Then synthesises a plain-English narrative that directly addresses the
    user's question (if provided).

    Args:
        repo_memory: The global ``repo_memory`` dict from main.py.
                     Keys are "owner/repo" strings; values are full analysis dicts.
        question:    The user's original comparison question (used to add a
                     targeted conclusion paragraph). Optional.

    Returns:
        A multi-paragraph plain-text comparison string.  Never raises.
    """
    if not repo_memory:
        return "No repositories have been analysed yet. Analyse at least two repos first."

    if len(repo_memory) == 1:
        name = next(iter(repo_memory))
        return (
            f"Only one repository is in memory ({name}). "
            "Analyse another repository to enable comparison."
        )

    repo_names = list(repo_memory.keys())
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append(f"Comparing {len(repo_names)} repositories: {', '.join(repo_names)}\n")

    # ── Per-repo summaries ────────────────────────────────────────────────────
    lines.append("── Individual Overviews ──")
    for name, data in repo_memory.items():
        project_type = _safe(data, "insights", "project_type") or "Unknown type"
        tech_stack   = _safe_list(data, "insights", "tech_stack")
        frameworks   = _safe_list(data, "insights", "frameworks")
        arch_hint    = (
            _safe(data, "architecture", "explanation")
            or _safe(data, "insights", "architecture_hint")
            or "Unknown architecture"
        )
        summary      = _safe(data, "summary") or _safe(data, "readme_analysis", "purpose") or "No summary."
        score        = (data.get("code_review") or {}).get("quality_score", "N/A")
        difficulty   = _safe(data, "insights", "complexity", "difficulty") or "Unknown"
        dev_time     = _safe(data, "insights", "complexity", "estimated_dev_time") or "Unknown"

        ts_str = ", ".join(tech_stack[:6]) if tech_stack else "not detected"
        fw_str = ", ".join(frameworks[:5]) if frameworks else "none"

        lines.append(
            f"\n{name}\n"
            f"  Type       : {project_type}\n"
            f"  Summary    : {summary[:120]}{'...' if len(summary) > 120 else ''}\n"
            f"  Tech stack : {ts_str}\n"
            f"  Frameworks : {fw_str}\n"
            f"  Architecture: {arch_hint[:120]}{'...' if len(arch_hint) > 120 else ''}\n"
            f"  Quality    : {score}/10\n"
            f"  Complexity : {difficulty} ({dev_time})"
        )

    # ── Tech stack comparison ─────────────────────────────────────────────────
    lines.append("\n── Tech Stack Comparison ──")
    all_stacks: dict[str, list[str]] = {}
    for name, data in repo_memory.items():
        stack = _safe_list(data, "insights", "tech_stack")
        all_stacks[name] = [t.lower() for t in stack]

    # Find technologies shared across ALL repos
    if len(all_stacks) >= 2:
        stacks_as_sets = [set(v) for v in all_stacks.values()]
        shared = stacks_as_sets[0].intersection(*stacks_as_sets[1:])
        if shared:
            lines.append(f"  Shared across all repos: {', '.join(sorted(shared))}")
        else:
            lines.append("  No technologies are shared across all repositories.")

        # Find unique technologies per repo
        for name, stack in all_stacks.items():
            others = set()
            for other_name, other_stack in all_stacks.items():
                if other_name != name:
                    others.update(other_stack)
            unique = set(stack) - others
            if unique:
                lines.append(f"  Unique to {name}: {', '.join(sorted(unique))}")

    # ── Security comparison ───────────────────────────────────────────────────
    lines.append("\n── Security Risks ──")
    for name, data in repo_memory.items():
        risks = _safe_list(data, "code_review", "security_risks")
        score = (data.get("code_review") or {}).get("quality_score", "N/A")
        risk_str = f"{len(risks)} risk(s) identified" if risks else "No risks flagged"
        lines.append(f"  {name}: quality score {score}/10 — {risk_str}")

    # ── Architecture comparison ───────────────────────────────────────────────
    lines.append("\n── Architecture Patterns ──")
    for name, data in repo_memory.items():
        arch  = _safe(data, "architecture", "explanation") or _safe(data, "insights", "architecture_hint")
        layers = _safe_list(data, "architecture", "layers")
        layer_str = ", ".join(layers[:4]) if layers else "not detected"
        arch_short = (arch[:100] + "...") if len(arch) > 100 else arch
        lines.append(f"  {name}: {arch_short} [layers: {layer_str}]")

    # ── Complexity comparison ─────────────────────────────────────────────────
    lines.append("\n── Complexity ──")
    scores: list[tuple[str, int]] = []
    for name, data in repo_memory.items():
        raw_score = (data.get("insights") or {}).get("complexity", {}).get("score")
        if isinstance(raw_score, int):
            scores.append((name, raw_score))
        difficulty = _safe(data, "insights", "complexity", "difficulty") or "Unknown"
        dev_time   = _safe(data, "insights", "complexity", "estimated_dev_time") or "Unknown"
        lines.append(f"  {name}: {difficulty} (score {raw_score}/10, ~{dev_time})")

    if scores:
        most_complex   = max(scores, key=lambda x: x[1])
        least_complex  = min(scores, key=lambda x: x[1])
        if most_complex[0] != least_complex[0]:
            lines.append(
                f"\n  Most complex : {most_complex[0]} (score {most_complex[1]}/10)\n"
                f"  Least complex: {least_complex[0]} (score {least_complex[1]}/10)"
            )

    # ── Relationship narrative ────────────────────────────────────────────────
    lines.append("\n── How These Repos Relate ──")
    project_types = {n: _safe(d, "insights", "project_type").lower() for n, d in repo_memory.items()}

    # Detect common full-stack patterns
    has_backend  = [n for n, t in project_types.items() if any(kw in t for kw in ("api", "backend", "server", "service", "fastapi", "django", "flask", "express"))]
    has_frontend = [n for n, t in project_types.items() if any(kw in t for kw in ("frontend", "web app", "react", "vue", "angular", "ui", "dashboard"))]
    has_ml       = [n for n, t in project_types.items() if any(kw in t for kw in ("ml", "machine learning", "ai", "model", "data", "notebook"))]
    has_mobile   = [n for n, t in project_types.items() if any(kw in t for kw in ("mobile", "android", "ios", "flutter", "react native"))]

    narrative_parts: list[str] = []
    if has_backend and has_frontend:
        narrative_parts.append(
            f"{' and '.join(has_backend)} provide the backend API layer while "
            f"{' and '.join(has_frontend)} handle the frontend UI — together they form a full-stack architecture."
        )
    if has_ml:
        narrative_parts.append(
            f"{' and '.join(has_ml)} contain machine learning or data science components."
        )
    if has_mobile:
        narrative_parts.append(
            f"{' and '.join(has_mobile)} target mobile platforms."
        )
    if not narrative_parts:
        narrative_parts.append(
            "These repositories appear to be independent projects with distinct purposes."
        )

    lines.extend(f"  {p}" for p in narrative_parts)

    # ── Question-specific conclusion ──────────────────────────────────────────
    q_lower = (question or "").lower()
    if q_lower:
        lines.append("\n── Direct Answer to Your Question ──")
        if any(kw in q_lower for kw in ("better", "best", "worst", "recommend")):
            if scores:
                best = max(scores, key=lambda x: x[1])
                lines.append(
                    f"  Based on code quality scores, {best[0]} scores highest at {best[1]}/10."
                )
        elif "security" in q_lower or "risk" in q_lower:
            safest = min(
                repo_memory.items(),
                key=lambda kv: len(_safe_list(kv[1], "code_review", "security_risks")),
            )
            lines.append(
                f"  {safest[0]} has the fewest security risks "
                f"({len(_safe_list(safest[1], 'code_review', 'security_risks'))})."
            )
        elif "architect" in q_lower:
            lines.append(
                "  See the Architecture Patterns section above for a side-by-side view."
            )
        elif "stack" in q_lower or "framework" in q_lower or "language" in q_lower:
            lines.append(
                "  See the Tech Stack Comparison section above for a detailed breakdown."
            )
        else:
            lines.append(
                "  See the sections above for a full side-by-side breakdown of all repositories."
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool dispatch table
# ---------------------------------------------------------------------------

_TOOL_MAP: dict[str, callable] = {
    "summary":       lambda q, d: _tool_summary(d),
    "documentation": lambda q, d: _tool_documentation(d),
    "architecture":  lambda q, d: _tool_architecture(d),
    "code_review":   lambda q, d: _tool_code_review(d),
    "insights":      lambda q, d: _tool_insights(d),
    "rag":           lambda q, d: _tool_rag(q, d),
    # compare_repos is NOT in the single-repo tool map — it requires repo_memory
    # and is handled directly by the /agent/compare endpoint in main.py.
}

_TOOL_LABELS: dict[str, str] = {
    "summary":       "Project Summary",
    "documentation": "Documentation",
    "architecture":  "Architecture",
    "code_review":   "Code Review",
    "insights":      "Insights & Tech Stack",
    "rag":           "Semantic RAG Search",
    "compare_repos": "Repository Comparison",
}


# ---------------------------------------------------------------------------
# Public routing function
# ---------------------------------------------------------------------------

def route_tool(intent: str, repo_data: dict, question: str) -> dict:
    """
    Dispatch the detected intent to the appropriate RepoLens tool and return
    a structured response.

    Args:
        intent:    The intent string returned by ``detect_intent``.
        repo_data: The full JSON dict from ``GET /analyse``.
        question:  The original user question (needed by the RAG tool).

    Returns:
        A dict with keys:
        - ``"tool_used"``  — machine identifier (e.g. ``"documentation"``)
        - ``"tool_label"`` — human-readable label (e.g. ``"Documentation"``)
        - ``"answer"``     — the tool's plain-text response
    """
    repo_data = repo_data or {}

    # compare_repos needs repo_memory — caller should use /agent/compare instead
    if intent == "compare_repos":
        intent = "rag"   # graceful fallback for single-repo calls

    intent = intent if intent in _TOOL_MAP else "rag"

    try:
        tool_fn = _TOOL_MAP[intent]
        answer  = tool_fn(question, repo_data)
    except Exception as exc:
        answer = f"An error occurred while running the {intent} tool: {exc}"

    return {
        "tool_used":  intent,
        "tool_label": _TOOL_LABELS.get(intent, intent),
        "answer":     answer or "No information found.",
    }