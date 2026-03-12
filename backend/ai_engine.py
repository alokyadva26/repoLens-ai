"""
ai_engine.py
------------
RepoLens AI — README analysis engine.

Parses a repository README using keyword-based heuristics to extract:
  - purpose       : one-sentence description of what the project does
  - key_features  : bulleted list of notable capabilities
  - setup         : installation / getting-started instructions

Public API
----------
    generate_readme_analysis(readme_text: str) -> dict
    generate_ai_summary(metadata: dict, insights: dict) -> str
    generate_architecture_analysis(structure: list[str], insights: dict) -> dict
    generate_code_review(metadata: dict, languages: dict, insights: dict, structure: list[str]) -> dict
    generate_repo_documentation(metadata: dict, insights: dict, readme_analysis: dict, architecture: dict) -> dict
    generate_agent_answer(question: str, repo_data: dict) -> dict
    build_repo_knowledge(repo_data: dict) -> list[str]
    generate_embeddings(chunks: list[str]) -> object
    build_vector_index(embeddings: object) -> object
    retrieve_context(question: str, chunks: list[str], index: object, top_k: int) -> str
    generate_rag_answer(question: str, context: str) -> dict

All other functions are internal helpers prefixed with an underscore.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Section-heading patterns
# ---------------------------------------------------------------------------
# These patterns are matched (case-insensitively) against Markdown headings
# and plain-text section titles to locate relevant README regions.

# Headings that typically introduce the project purpose / overview
_PURPOSE_HEADINGS: list[str] = [
    "about", "overview", "introduction", "what is", "description",
    "summary", "background", "motivation", "why",
]

# Headings that list features, highlights, or capabilities
_FEATURES_HEADINGS: list[str] = [
    "feature", "highlight", "capabilit", "what it does",
    "what does", "key point", "benefit",
]

# Headings that describe installation, setup, or getting started
_SETUP_HEADINGS: list[str] = [
    "install", "setup", "getting started", "quick start", "quickstart",
    "usage", "how to use", "requirement", "prerequisite", "build",
    "run", "deploy", "configuration",
]

# Regex that matches any Markdown heading (# … ######) or an all-caps line
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$|^([A-Z][A-Z\s]{3,})$", re.MULTILINE)

# Regex that matches Markdown bullet points (-, *, +) and numbered lists
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$|^\s*\d+\.\s+(.+)$", re.MULTILINE)

# Markdown code fence  (``` or ~~~)
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~")

# Maximum characters to consider from any single README section
_MAX_SECTION_CHARS = 1_200


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_readme_analysis(readme_text: str) -> dict:
    """
    Parse a README and return a structured analysis dict.

    The function splits the README into labelled sections, then searches for
    sections whose headings suggest purpose, features, or setup content.
    Fallback heuristics apply when the README has no headings.

    Args:
        readme_text: Raw decoded README content (plain text or Markdown).

    Returns:
        A dict with keys:
          - purpose       (str)        — what the project does
          - key_features  (list[str])  — notable capabilities / highlights
          - setup         (str)        — installation / usage instructions
    """
    if not readme_text or not readme_text.strip():
        return _empty_analysis()

    # Strip code blocks early — they add noise to text matching
    cleaned = _CODE_FENCE_RE.sub("", readme_text)

    sections = _split_into_sections(cleaned)

    purpose      = _extract_purpose(sections, cleaned)
    key_features = _extract_features(sections, cleaned)
    setup        = _extract_setup(sections, cleaned)

    return {
        "purpose":      purpose,
        "key_features": key_features,
        "setup":        setup,
    }


# ---------------------------------------------------------------------------
# Internal helpers — section splitting
# ---------------------------------------------------------------------------

def _split_into_sections(text: str) -> list[dict]:
    """
    Divide the README into a list of named sections.

    Each section is a dict with:
      - ``heading`` (str, lowercase)  — the heading text
      - ``body``    (str)             — the content that follows the heading

    The implicit first block (content before any heading) is stored with
    the heading ``"__intro__"``.

    Args:
        text: README text with code fences already stripped.

    Returns:
        List of section dicts in document order.
    """
    matches = list(_HEADING_RE.finditer(text))
    sections: list[dict] = []

    # Content that precedes the very first heading
    intro_end = matches[0].start() if matches else len(text)
    intro_body = text[:intro_end].strip()
    if intro_body:
        sections.append({"heading": "__intro__", "body": intro_body})

    for i, match in enumerate(matches):
        heading_raw = (match.group(1) or match.group(2) or "").strip()
        heading = heading_raw.lower()

        body_start = match.end()
        body_end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body       = text[body_start:body_end].strip()

        sections.append({"heading": heading, "body": body})

    return sections


def _section_matches(heading: str, keywords: list[str]) -> bool:
    """Return True if *any* keyword appears in the heading string."""
    return any(kw in heading for kw in keywords)


# ---------------------------------------------------------------------------
# Internal helpers — purpose extraction
# ---------------------------------------------------------------------------

def _extract_purpose(sections: list[dict], full_text: str) -> str:
    """
    Extract a one-sentence project purpose statement.

    Search order:
    1. A section whose heading matches _PURPOSE_HEADINGS.
    2. The intro block (text before the first heading).
    3. The first non-empty paragraph anywhere in the README.
    4. Hard fallback.

    Args:
        sections:  Parsed section list.
        full_text: Full README text (code fences stripped).

    Returns:
        A single sentence (or short paragraph) describing the project.
    """
    # 1. Dedicated purpose/overview section
    for sec in sections:
        if _section_matches(sec["heading"], _PURPOSE_HEADINGS):
            sentence = _first_meaningful_sentence(sec["body"])
            if sentence:
                return sentence

    # 2. Intro block — often the best single-sentence description
    for sec in sections:
        if sec["heading"] == "__intro__":
            sentence = _first_meaningful_sentence(sec["body"])
            if sentence:
                return sentence

    # 3. First meaningful sentence anywhere
    sentence = _first_meaningful_sentence(full_text)
    if sentence:
        return sentence

    return "No project description found in README."


def _first_meaningful_sentence(text: str) -> str:
    """
    Extract the first sentence that is at least 20 characters long and
    does not look like a badge line, heading, or code snippet.

    Args:
        text: Arbitrary text block.

    Returns:
        The first qualifying sentence, or an empty string if none found.
    """
    # Remove Markdown badges  [![...](...)], inline images, and links
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    cleaned = re.sub(r"\[.*?\]\(.*?\)", "", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)          # HTML tags
    cleaned = re.sub(r"`[^`]+`", "", cleaned)           # inline code
    cleaned = re.sub(r"^\s*[#\-*>|]+\s*", "", cleaned, flags=re.MULTILINE)

    for line in cleaned.splitlines():
        line = line.strip()
        if len(line) >= 20 and not line.startswith("http"):
            # Return the first sentence within the line if possible
            sentences = re.split(r"(?<=[.!?])\s+", line)
            if sentences and len(sentences[0]) >= 20:
                return sentences[0][:500]
            if len(line) >= 20:
                return line[:500]

    return ""


# ---------------------------------------------------------------------------
# Internal helpers — feature extraction
# ---------------------------------------------------------------------------

def _extract_features(sections: list[dict], full_text: str) -> list[str]:
    """
    Extract a list of key feature strings.

    Search order:
    1. A section whose heading matches _FEATURES_HEADINGS — collect bullets.
    2. Any section with bullet points that look feature-like.
    3. Heuristic: pull all bullets from the intro block.
    4. Fallback: return an empty list.

    Args:
        sections:  Parsed section list.
        full_text: Full README text (code fences stripped).

    Returns:
        A list of feature strings (max 10 items, each ≤ 200 chars).
    """
    # 1. Dedicated features section
    for sec in sections:
        if _section_matches(sec["heading"], _FEATURES_HEADINGS):
            bullets = _extract_bullets(sec["body"])
            if bullets:
                return bullets[:10]

    # 2. Any section containing bullets (skip setup-only sections)
    for sec in sections:
        if sec["heading"] in ("__intro__",):
            continue
        if _section_matches(sec["heading"], _SETUP_HEADINGS):
            continue
        bullets = _extract_bullets(sec["body"])
        if len(bullets) >= 2:
            return bullets[:10]

    # 3. Bullets from the intro
    for sec in sections:
        if sec["heading"] == "__intro__":
            bullets = _extract_bullets(sec["body"])
            if bullets:
                return bullets[:10]

    return []


def _extract_bullets(text: str) -> list[str]:
    """
    Pull all bullet-point or numbered-list items from *text*.

    Cleans Markdown formatting (bold, italic, inline code, links) from
    each item before returning.

    Args:
        text: A block of Markdown or plain text.

    Returns:
        A list of cleaned, non-empty bullet strings.
    """
    items: list[str] = []
    for match in _BULLET_RE.finditer(text):
        raw = (match.group(1) or match.group(2) or "").strip()
        clean = _strip_markdown_inline(raw)
        if clean and len(clean) >= 5:
            items.append(clean[:200])
    return items


def _strip_markdown_inline(text: str) -> str:
    """Remove common Markdown inline formatting tokens from *text*."""
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)   # bold / italic
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)     # underscore emphasis
    text = re.sub(r"`([^`]+)`", r"\1", text)                # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # links
    text = re.sub(r"<[^>]+>", "", text)                     # HTML tags
    return text.strip()


# ---------------------------------------------------------------------------
# Internal helpers — setup extraction
# ---------------------------------------------------------------------------

def _extract_setup(sections: list[dict], full_text: str) -> str:
    """
    Extract installation / getting-started instructions.

    Search order:
    1. A section whose heading matches _SETUP_HEADINGS — return its body.
    2. Heuristic scan for lines that look like shell commands (pip, npm,
       git clone, docker, make, etc.) across the full text.
    3. Hard fallback.

    Args:
        sections:  Parsed section list.
        full_text: Full README text (code fences stripped).

    Returns:
        A string containing setup instructions (truncated at
        _MAX_SECTION_CHARS characters).
    """
    # 1. Dedicated setup section
    for sec in sections:
        if _section_matches(sec["heading"], _SETUP_HEADINGS):
            body = sec["body"].strip()
            if len(body) >= 20:
                return body[:_MAX_SECTION_CHARS]

    # 2. Heuristic: find lines with common setup commands
    command_patterns = re.compile(
        r"^\s*(pip install|pip3 install|npm install|yarn (add|install)|"
        r"git clone|docker (build|run|compose)|make |"
        r"python (setup\.py|main\.py|-m )|uvicorn|poetry install|"
        r"cargo build|go (build|run)|bundle install)",
        re.IGNORECASE | re.MULTILINE,
    )
    command_lines: list[str] = []
    for line in full_text.splitlines():
        if command_patterns.match(line):
            command_lines.append(line.strip())

    if command_lines:
        return "\n".join(command_lines)[:_MAX_SECTION_CHARS]

    return "No setup instructions found in README."


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _empty_analysis() -> dict:
    """Return a blank analysis dict for repos with no README."""
    return {
        "purpose":      "No README found for this repository.",
        "key_features": [],
        "setup":        "No setup instructions available.",
    }


# ---------------------------------------------------------------------------
# AI Summary
# ---------------------------------------------------------------------------

def generate_ai_summary(metadata: dict, insights: dict) -> str:
    """
    Generate a concise, human-readable summary of a GitHub repository.

    Combines repository metadata (name, description, stars, language size)
    with structured insights (project type, frameworks, architecture, complexity)
    to produce a 2–3 sentence plain-English summary.

    The summary is assembled from discrete sentence templates so that every
    field contributes naturally without awkward empty-value gaps. Only
    sentences whose data is actually present are included.

    Args:
        metadata: Repository metadata dict as returned by
                  ``github_fetcher.fetch_repo_metadata``.
        insights: Insights dict as returned by ``repo_parser.analyse_repo``,
                  including the nested ``complexity`` sub-dict.

    Returns:
        A non-empty string summary.  Never raises — any unexpected error
        causes a graceful fallback sentence to be returned instead.
    """
    try:
        # ── Pull fields with safe defaults ────────────────────────────────────
        name        = metadata.get("name") or "This repository"
        description = (metadata.get("description") or "").strip()
        stars       = metadata.get("stars") or 0
        forks       = metadata.get("forks") or 0
        topics      = metadata.get("topics") or []

        project_type      = insights.get("project_type") or "software project"
        frameworks        = insights.get("frameworks") or []
        architecture_hint = insights.get("architecture_hint") or ""
        tech_stack        = insights.get("tech_stack") or []

        complexity    = insights.get("complexity") or {}
        difficulty    = complexity.get("difficulty") or ""
        dev_time      = complexity.get("estimated_dev_time") or ""
        complexity_score = complexity.get("score")

        # ── Sentence 1: identity + description ───────────────────────────────
        # Use the repo description when it exists; fall back to project type.
        if description:
            sentence1 = f"{name} is a {project_type} — {description}."
        else:
            sentence1 = f"{name} is a {project_type}."

        # ── Sentence 2: tech stack + frameworks ───────────────────────────────
        parts: list[str] = []

        # Primary languages (first 3 from tech_stack that look like languages)
        lang_tags = [
            t for t in tech_stack
            if t not in frameworks and "/" not in t and len(t) <= 20
        ][:3]
        if lang_tags:
            parts.append(f"built with {', '.join(lang_tags)}")

        if frameworks:
            fw_str = ", ".join(frameworks[:3])
            label  = "framework" if len(frameworks) == 1 else "frameworks"
            parts.append(f"using the {fw_str} {label}")

        if architecture_hint:
            parts.append(f"following a {architecture_hint} approach")

        sentence2 = ("It is " + " ".join(parts) + ".").capitalize() if parts else ""

        # ── Sentence 3: community + complexity ───────────────────────────────
        social_parts: list[str] = []
        if stars >= 1000:
            social_parts.append(f"{stars:,} stars")
        if forks >= 100:
            social_parts.append(f"{forks:,} forks")

        complexity_parts: list[str] = []
        if difficulty:
            complexity_parts.append(f"{difficulty.lower()}-level complexity")
        if dev_time:
            complexity_parts.append(f"an estimated development time of {dev_time}")

        sentence3_chunks: list[str] = []
        if social_parts:
            sentence3_chunks.append(f"The project has {' and '.join(social_parts)} on GitHub")
        if complexity_parts:
            sentence3_chunks.append(
                ("and carries " if sentence3_chunks else "It carries ")
                + " and ".join(complexity_parts)
            )

        sentence3 = " ".join(sentence3_chunks).strip()
        if sentence3 and not sentence3.endswith("."):
            sentence3 += "."

        # ── Topics rider (optional) ───────────────────────────────────────────
        sentence4 = ""
        if topics:
            topic_str = ", ".join(f"#{t}" for t in topics[:5])
            sentence4 = f"Key topics include {topic_str}."

        # ── Assemble final summary ────────────────────────────────────────────
        sentences = [s for s in [sentence1, sentence2, sentence3, sentence4] if s]
        return " ".join(sentences)

    except Exception:
        # Never let summary generation crash the API
        try:
            name = (metadata or {}).get("name") or "This repository"
        except Exception:
            name = "This repository"
        return f"{name} is a software project hosted on GitHub."


# ---------------------------------------------------------------------------
# Architecture Analysis
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Architecture layer detection rules
# ---------------------------------------------------------------------------
# Each rule is a tuple of:
#   (folder/file names that trigger the rule,  layer label to emit)
#
# The names are matched case-insensitively against the top-level structure
# returned by github_fetcher.fetch_repo_structure.  A layer is added at most
# once regardless of how many names match.
# ---------------------------------------------------------------------------
_LAYER_RULES: list[tuple[list[str], str]] = [
    # Backend / server
    (["backend", "server", "app", "api", "src/api", "routes",
      "controllers", "handlers", "endpoints"],           "Backend API"),
    # Frontend / client
    (["frontend", "client", "ui", "web", "public",
      "static", "pages", "views", "templates"],          "Frontend UI"),
    # Service / business logic
    (["services", "service", "usecases", "use_cases",
      "business", "domain", "core"],                     "Service Layer"),
    # Data / persistence
    (["models", "model", "db", "database", "migrations",
      "schemas", "entities", "repositories", "data"],    "Data Layer"),
    # ML / AI
    (["ml", "ai", "models", "notebooks", "training",
      "inference", "experiments", "pipelines",
      "checkpoints"],                                    "ML / AI Layer"),
    # Infrastructure / DevOps
    (["infra", "infrastructure", "terraform", "k8s",
      "kubernetes", "helm", "ansible", "deploy",
      "deployment", "devops", ".github"],                "Infrastructure / DevOps"),
    # Testing
    (["tests", "test", "spec", "specs", "__tests__",
      "e2e", "integration"],                             "Testing Layer"),
    # Documentation
    (["docs", "doc", "documentation", "wiki"],           "Documentation"),
    # Configuration
    (["config", "configs", "configuration", "settings",
      "env", ".env"],                                    "Configuration"),
    # Shared / common utilities
    (["shared", "common", "utils", "utilities", "lib",
      "helpers", "packages"],                            "Shared / Utils"),
    # Scripts
    (["scripts", "script", "bin", "tools"],              "Scripts / Tooling"),
]

# Folder keywords → structure type classification
_STRUCTURE_PATTERNS: list[tuple[list[str], str]] = [
    (["frontend", "client", "ui", "web",
      "backend", "server", "api"],                       "Full-Stack Monorepo"),
    (["services", "service"],                            "Microservices / Service-Oriented"),
    (["frontend", "client", "ui", "web"],                "Frontend Application"),
    (["backend", "server", "api", "app"],                "Backend Application"),
    (["notebooks", "notebook", "experiments"],           "Data Science / Notebook Repository"),
    (["infra", "infrastructure", "terraform",
      "k8s", "helm"],                                    "Infrastructure Repository"),
    (["packages", "libs", "modules"],                    "Monorepo / Multi-Package"),
]

# Known config / metadata filenames that appear at root level
_CONFIG_FILES: set[str] = {
    "docker-compose.yml", "docker-compose.yaml",
    "dockerfile",
    "makefile",
    ".github",
    "kubernetes", "k8s",
    "terraform",
    ".env", ".env.example",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "yarn.lock", "pnpm-lock.yaml",
    "cargo.toml",
    "go.mod",
    "pom.xml", "build.gradle",
    "requirements.txt", "pipfile",
    "gemfile",
    "composer.json",
}


def generate_architecture_analysis(
    structure: list[str],
    insights: dict,
) -> dict:
    """
    Derive a high-level architecture description from the repository's
    top-level file/folder structure and existing insights.

    The analysis has three output fields:

    ``layers``
        Ordered list of architectural layer labels detected in the repo
        (e.g. "Backend API", "Frontend UI", "Testing Layer").

    ``structure``
        Flat list of all top-level entry names from the repository root
        (files and folders), exactly as returned by
        ``github_fetcher.fetch_repo_structure``.

    ``explanation``
        A one-paragraph plain-English description of the inferred
        architecture, synthesised from the layers, tech stack, and
        architecture hint already present in ``insights``.

    Args:
        structure: Top-level repo entry names (from fetch_repo_structure).
        insights:  Insights dict from repo_parser.analyse_repo, including
                   ``architecture_hint``, ``tech_stack``, ``project_type``,
                   and nested ``complexity``.

    Returns:
        A dict with keys: ``layers`` (list[str]), ``structure`` (list[str]),
        ``explanation`` (str).
    """
    structure = structure or []
    insights  = insights  or {}

    # Normalise structure entries to lowercase for matching; keep originals
    # for the ``structure`` output field.
    lower_structure: set[str] = {name.lower() for name in structure}

    # ── 1. Detect layers ─────────────────────────────────────────────────────
    layers: list[str] = []
    seen_layers: set[str] = set()

    for trigger_names, label in _LAYER_RULES:
        if label in seen_layers:
            continue
        if any(t in lower_structure for t in trigger_names):
            layers.append(label)
            seen_layers.add(label)

    # Supplement layers from insights.tech_stack when folder signals are absent
    tech_stack = insights.get("tech_stack") or []
    ts_lower   = {t.lower() for t in tech_stack}

    if "Backend API" not in seen_layers and any(
        kw in ts_lower for kw in ("rest api", "fastapi", "flask", "django",
                                   "express.js", "nestjs", "gin", "spring boot")
    ):
        layers.append("Backend API")
        seen_layers.add("Backend API")

    if "Frontend UI" not in seen_layers and any(
        kw in ts_lower for kw in ("react", "vue.js", "angular", "svelte",
                                   "next.js", "nuxt.js")
    ):
        layers.append("Frontend UI")
        seen_layers.add("Frontend UI")

    if "ML / AI Layer" not in seen_layers and "Machine Learning" in tech_stack:
        layers.append("ML / AI Layer")
        seen_layers.add("ML / AI Layer")

    # ── 2. Classify overall structure type ───────────────────────────────────
    structure_type: str = _classify_structure(lower_structure, insights)

    # ── 3. Synthesise plain-English explanation ───────────────────────────────
    explanation = _build_explanation(layers, structure_type, insights)

    return {
        "layers":      layers,
        "structure":   structure,          # original casing preserved
        "explanation": explanation,
    }


def _classify_structure(lower_structure: set[str], insights: dict) -> str:
    """
    Return a short label for the overall repository structure type.

    Evaluated in priority order; first matching pattern wins.

    Args:
        lower_structure: Set of lowercased top-level entry names.
        insights:        Insights dict from repo_parser.

    Returns:
        A human-readable structure label string.
    """
    for trigger_names, label in _STRUCTURE_PATTERNS:
        # Require at least one trigger name to be present.
        if any(t in lower_structure for t in trigger_names):
            # For "Full-Stack", require BOTH a frontend AND a backend signal.
            if label == "Full-Stack Monorepo":
                has_fe = any(t in lower_structure for t in
                             ["frontend", "client", "ui", "web"])
                has_be = any(t in lower_structure for t in
                             ["backend", "server", "api"])
                if has_fe and has_be:
                    return label
                continue
            return label

    # Fall back to the architecture hint already computed by repo_parser
    return insights.get("architecture_hint") or "General Repository"


def _build_explanation(
    layers: list[str],
    structure_type: str,
    insights: dict,
) -> str:
    """
    Compose a concise architecture explanation paragraph.

    Args:
        layers:         Detected architectural layers.
        structure_type: Overall structure classification label.
        insights:       Insights dict from repo_parser.

    Returns:
        A non-empty plain-English explanation string.
    """
    project_type  = insights.get("project_type")  or "software project"
    arch_hint     = insights.get("architecture_hint") or ""
    tech_stack    = insights.get("tech_stack")    or []
    complexity    = insights.get("complexity")    or {}
    difficulty    = complexity.get("difficulty")  or ""

    # Opening sentence
    parts: list[str] = [
        f"This is a {structure_type.lower()} organised as a {project_type.lower()}."
    ]

    # Layer summary
    if layers:
        layer_str = ", ".join(layers[:-1])
        if len(layers) > 1:
            layer_str += f" and {layers[-1]}"
        else:
            layer_str = layers[0]
        parts.append(f"The codebase is divided into the following architectural layers: {layer_str}.")

    # Architecture hint from repo_parser (only if different from structure_type)
    if arch_hint and arch_hint.lower() not in structure_type.lower():
        parts.append(f"The overall architectural pattern follows a {arch_hint} approach.")

    # Key technologies
    if tech_stack:
        ts_display = ", ".join(tech_stack[:5])
        parts.append(f"Key technologies detected include {ts_display}.")

    # Complexity note
    if difficulty:
        parts.append(
            f"Based on the structure and tech stack, this project has "
            f"{difficulty.lower()}-level complexity."
        )

    return " ".join(parts)


# ===========================================================================
# Code Review Engine
# ===========================================================================

# ---------------------------------------------------------------------------
# Code-review knowledge bases
# ---------------------------------------------------------------------------

# Language → security risks that apply to that ecosystem
_LANG_SECURITY_RISKS: dict[str, list[str]] = {
    "Python": [
        "Avoid hardcoded credentials — use environment variables or a secrets manager",
        "Pin dependency versions in requirements.txt to prevent supply-chain attacks",
        "Use bandit or semgrep for static security analysis",
    ],
    "JavaScript": [
        "Audit npm dependencies regularly with `npm audit`",
        "Avoid eval() and dynamic code execution",
        "Sanitise all user-supplied input to prevent XSS",
    ],
    "TypeScript": [
        "Audit npm dependencies regularly with `npm audit`",
        "Avoid `any` casts that bypass type safety checks",
        "Sanitise all user-supplied input to prevent XSS",
    ],
    "Java": [
        "Prefer parameterised queries to prevent SQL injection",
        "Keep third-party JAR versions pinned and updated",
        "Validate and sanitise all external input",
    ],
    "Go": [
        "Avoid using unsafe package unless strictly necessary",
        "Validate external input to prevent injection attacks",
        "Keep Go module dependencies at known-good versions",
    ],
    "Rust": [
        "Minimise use of `unsafe` blocks and document every instance",
        "Audit crates.io dependencies with `cargo audit`",
    ],
    "PHP": [
        "Use prepared statements to prevent SQL injection",
        "Escape all output to prevent XSS attacks",
        "Keep Composer dependencies up-to-date",
    ],
    "Ruby": [
        "Keep Gemfile.lock committed to lock dependency versions",
        "Escape all view output to prevent XSS",
        "Run Brakeman for Rails-specific security scanning",
    ],
    "Shell": [
        "Quote all variables to prevent word splitting and glob expansion",
        "Avoid storing secrets in shell scripts",
        "Use `set -euo pipefail` to catch errors early",
    ],
    "Dockerfile": [
        "Use specific image tags instead of `latest` to ensure reproducibility",
        "Run containers as a non-root user where possible",
        "Minimise image layers and remove build tools in production images",
    ],
}

# Project-type → performance notes
_PROJECT_PERF_NOTES: dict[str, list[str]] = {
    "Web App": [
        "Enable HTTP caching headers (ETag, Cache-Control) for static assets",
        "Use a CDN for static file delivery in production",
        "Lazy-load routes and large components to improve initial load time",
    ],
    "API Service": [
        "Add pagination to all list endpoints to limit response size",
        "Cache frequently-read data in Redis or an in-memory store",
        "Use async endpoints (async def) for I/O-bound operations",
    ],
    "ML / AI Project": [
        "Batch inference requests rather than processing one-by-one",
        "Profile memory usage — large models can cause OOM errors in production",
        "Cache model artefacts and avoid reloading on every request",
    ],
    "Data Pipeline": [
        "Partition large datasets to enable parallel processing",
        "Use streaming reads for large files instead of loading into memory",
        "Profile bottlenecks with cProfile or py-spy before optimising",
    ],
    "CLI Tool": [
        "Defer expensive imports to reduce startup latency",
        "Stream large outputs instead of buffering them in memory",
    ],
    "Library / SDK": [
        "Minimise hard dependencies to reduce the install footprint",
        "Profile hot code paths and add benchmarks to the test suite",
    ],
}

# Architecture hint → performance notes
_ARCH_PERF_NOTES: dict[str, list[str]] = {
    "Microservices Architecture": [
        "Implement circuit-breakers to prevent cascading failures between services",
        "Use asynchronous messaging (e.g. Kafka, RabbitMQ) for non-critical paths",
    ],
    "Full-Stack Web Application": [
        "Minimise round-trips between client and API — batch related requests",
        "Use server-side rendering or static generation for SEO-critical pages",
    ],
    "Backend Service / API": [
        "Add a connection pool for database access",
        "Profile slow queries and add appropriate indices",
    ],
}

# Structure-file → best-practice recommendations
_STRUCTURE_BEST_PRACTICES: dict[str, str] = {
    "requirements.txt":  "Pin all versions in requirements.txt (use pip-compile or pip freeze)",
    "package.json":      "Commit package-lock.json or yarn.lock to lock dependency versions",
    "dockerfile":        "Add a .dockerignore file to keep images lean",
    "docker-compose":    "Store sensitive values in .env files, not docker-compose.yml",
    ".github":           "Add branch-protection rules and require PR reviews before merging",
    "tests":             "Measure test coverage and set a minimum threshold in CI",
    "test":              "Measure test coverage and set a minimum threshold in CI",
    "makefile":          "Document all Makefile targets with a `help` target",
    ".env":              "Never commit .env files — add them to .gitignore",
    "terraform":         "Store Terraform state remotely (e.g. S3 + DynamoDB locking)",
    "k8s":               "Define resource requests and limits for all Kubernetes workloads",
    "kubernetes":        "Define resource requests and limits for all Kubernetes workloads",
    "notebooks":         "Convert production-ready notebook code to importable Python modules",
}

# Universal best practices that apply to every repository
_UNIVERSAL_BEST_PRACTICES: list[str] = [
    "Add a CONTRIBUTING.md to guide external contributors",
    "Enforce a consistent code style with a linter (e.g. flake8, eslint, golangci-lint)",
    "Set up CI to run tests and linting on every pull request",
    "Keep a CHANGELOG to communicate breaking changes to consumers",
    "Ensure sensitive data is excluded via a well-maintained .gitignore",
]

# Quality-score penalty rules: (condition_description, points_to_deduct)
# Applied after computing the base score; each rule is a callable.
_SCORE_BONUSES: list[tuple[str, int]] = [
    # Structure signals that raise quality
    ("has_tests",         +1),   # tests/ or test/ folder present
    ("has_ci",            +1),   # .github folder present
    ("has_docs",          +1),   # docs/ folder present
    ("has_dockerfile",    +1),   # Dockerfile signals deployment readiness
]

_SCORE_PENALTIES: list[tuple[str, int]] = [
    # Absence of good practices
    ("no_tests",          -2),
    ("no_readme",         -1),
    ("no_ci",             -1),
    ("many_languages",    -1),   # > 5 languages → harder to maintain
    ("advanced_complex",  -1),   # Advanced complexity without test coverage
]


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def generate_code_review(
    metadata: dict,
    languages: dict,
    insights: dict,
    structure: list[str],
) -> dict:
    """
    Perform a rule-based code review of a GitHub repository.

    The review covers four dimensions:

    ``quality_score``
        An integer 1–10 representing overall code-health confidence.
        Starts at a neutral baseline and is adjusted by presence / absence
        of tests, CI, documentation, and other structural signals.

    ``security_risks``
        Language-specific and ecosystem-specific security warnings.

    ``performance_notes``
        Recommendations based on project type and detected architecture.

    ``best_practices``
        Actionable improvement suggestions derived from the repository
        structure plus a core set of universal recommendations.

    Args:
        metadata:  Repository metadata dict (name, description, stars, …).
        languages: Language → byte-count dict.
        insights:  Insights dict from repo_parser.analyse_repo, including
                   project_type, architecture_hint, tech_stack, complexity.
        structure: Top-level repository entry names (from fetch_repo_structure).

    Returns:
        A dict with keys:
          - quality_score     (int, 1–10)
          - security_risks    (list[str])
          - performance_notes (list[str])
          - best_practices    (list[str])
    """
    # Safe defaults — nothing should raise here
    metadata  = metadata  or {}
    languages = languages or {}
    insights  = insights  or {}
    structure = structure or []

    lower_structure: set[str] = {e.lower() for e in structure}
    project_type    = (insights.get("project_type")      or "").strip()
    arch_hint       = (insights.get("architecture_hint") or "").strip()
    complexity      = insights.get("complexity") or {}
    difficulty      = (complexity.get("difficulty") or "").strip()

    # ── Security risks ────────────────────────────────────────────────────────
    security_risks = _build_security_risks(languages, lower_structure)

    # ── Performance notes ─────────────────────────────────────────────────────
    performance_notes = _build_performance_notes(project_type, arch_hint, languages)

    # ── Best practices ────────────────────────────────────────────────────────
    best_practices = _build_best_practices(lower_structure, languages, insights)

    # ── Quality score ─────────────────────────────────────────────────────────
    quality_score = _calculate_quality_score(
        lower_structure, languages, difficulty, len(security_risks)
    )

    return {
        "quality_score":     quality_score,
        "security_risks":    security_risks,
        "performance_notes": performance_notes,
        "best_practices":    best_practices,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_security_risks(
    languages: dict,
    lower_structure: set[str],
) -> list[str]:
    """
    Collect applicable security risk messages.

    Picks at most 2 risks per language (to avoid noise) and adds a
    generic .env warning if a .env file is detected at the root.

    Args:
        languages:       Language → byte-count dict.
        lower_structure: Lowercased set of top-level entry names.

    Returns:
        A deduplicated list of security-risk strings.
    """
    risks: list[str] = []
    seen: set[str]   = set()

    def _add(msg: str) -> None:
        if msg not in seen:
            risks.append(msg)
            seen.add(msg)

    for lang, messages in _LANG_SECURITY_RISKS.items():
        if lang in languages:
            for msg in messages[:2]:   # cap at 2 per language
                _add(msg)

    # Generic structural warnings
    if ".env" in lower_structure:
        _add("A .env file was found at the repository root — ensure it is in .gitignore and never committed")

    if not any(t in lower_structure for t in ("tests", "test", "__tests__", "spec", "specs")):
        _add("No test directory detected — untested code is harder to refactor safely")

    return risks


def _build_performance_notes(
    project_type: str,
    arch_hint: str,
    languages: dict,
) -> list[str]:
    """
    Produce performance recommendations for the detected project type
    and architecture pattern.

    Args:
        project_type: Project-type label from repo_parser.
        arch_hint:    Architecture hint label from repo_parser.
        languages:    Language → byte-count dict.

    Returns:
        A deduplicated list of performance note strings.
    """
    notes: list[str] = []
    seen: set[str]   = set()

    def _add(msg: str) -> None:
        if msg not in seen:
            notes.append(msg)
            seen.add(msg)

    # Project-type specific notes (cap at 2 per type)
    for pt, messages in _PROJECT_PERF_NOTES.items():
        if pt.lower() in project_type.lower():
            for msg in messages[:2]:
                _add(msg)

    # Architecture-specific notes (cap at 1 per pattern)
    for arch, messages in _ARCH_PERF_NOTES.items():
        if arch.lower() in arch_hint.lower():
            _add(messages[0])

    # Language-specific performance reminders
    if "Python" in languages and "Jupyter Notebook" in languages:
        _add("Consider extracting reusable code from notebooks into importable Python modules")

    if "JavaScript" in languages and "TypeScript" not in languages:
        _add("Migrating to TypeScript can surface type errors early and improve IDE support")

    return notes


def _build_best_practices(
    lower_structure: set[str],
    languages: dict,
    insights: dict,
) -> list[str]:
    """
    Generate best-practice recommendations from structural signals.

    Always includes a curated subset of universal practices, supplemented
    by structure-specific and language-specific recommendations.

    Args:
        lower_structure: Lowercased set of top-level entry names.
        languages:       Language → byte-count dict.
        insights:        Insights dict from repo_parser.

    Returns:
        A deduplicated list of best-practice strings (max 8 items).
    """
    practices: list[str] = []
    seen: set[str]       = set()

    def _add(msg: str) -> None:
        if msg not in seen and len(practices) < 8:
            practices.append(msg)
            seen.add(msg)

    # Structure-driven recommendations
    for entry_fragment, recommendation in _STRUCTURE_BEST_PRACTICES.items():
        if any(entry_fragment in e for e in lower_structure):
            _add(recommendation)

    # Missing-structure recommendations
    if not any(t in lower_structure for t in ("tests", "test", "__tests__", "spec")):
        _add("Add a test suite — even minimal coverage improves confidence during refactoring")

    if not any(ci in lower_structure for ci in (".github", ".circleci", ".travis.yml", "jenkinsfile")):
        _add("Set up CI (GitHub Actions, CircleCI, etc.) to automate tests and linting on every push")

    if "readme.md" not in lower_structure and "readme" not in lower_structure:
        _add("Add a README.md with project overview, installation steps, and usage examples")

    # Language-specific practices
    if "Python" in languages:
        _add("Use a virtual environment (venv, poetry, or conda) to isolate dependencies")
        _add("Add type annotations and run mypy for static type checking")

    if "TypeScript" in languages or "JavaScript" in languages:
        _add("Use ESLint and Prettier to enforce consistent code style")

    if "Dockerfile" in languages or "dockerfile" in lower_structure:
        _add("Use multi-stage Docker builds to separate build and runtime environments")

    # Universal practices — always appended last (deduplicated)
    for practice in _UNIVERSAL_BEST_PRACTICES:
        _add(practice)

    return practices


def _calculate_quality_score(
    lower_structure: set[str],
    languages: dict,
    difficulty: str,
    security_risk_count: int,
) -> int:
    """
    Compute a quality score between 1 and 10.

    Starts at a neutral baseline of 6 and applies bonuses and penalties
    based on structural signals.

    Scoring adjustments:
      +1  tests directory present
      +1  CI configuration present (.github, .circleci, etc.)
      +1  docs directory present
      +1  Dockerfile present (deployment readiness)
      -1  no tests directory
      -1  no CI configuration
      -1  more than 5 languages (harder to maintain)
      -1  Advanced difficulty without a test suite
      -1  per 3 security risks (rounded down), capped at -2

    Args:
        lower_structure:     Lowercased set of top-level entry names.
        languages:           Language → byte-count dict.
        difficulty:          "Beginner" | "Intermediate" | "Advanced"
        security_risk_count: Number of detected security risks.

    Returns:
        An integer score clamped to [1, 10].
    """
    score = 6  # neutral baseline

    has_tests = any(t in lower_structure for t in ("tests", "test", "__tests__", "spec", "specs"))
    has_ci    = any(ci in lower_structure for ci in (".github", ".circleci", "jenkinsfile"))
    has_docs  = any(d in lower_structure for d in ("docs", "doc", "documentation"))
    has_docker = any(d in lower_structure for d in ("dockerfile", "docker-compose.yml", "docker-compose.yaml"))

    # Bonuses
    if has_tests:  score += 1
    if has_ci:     score += 1
    if has_docs:   score += 1
    if has_docker: score += 1

    # Penalties
    if not has_tests: score -= 1
    if not has_ci:    score -= 1
    if len(languages) > 5: score -= 1
    if difficulty.lower() == "advanced" and not has_tests: score -= 1

    # Security risk penalty: -1 for every 3 risks, max -2
    score -= min(security_risk_count // 3, 2)

    return max(1, min(10, score))


# ===========================================================================
# AI Repo Documentation Generator
# ===========================================================================

# ---------------------------------------------------------------------------
# Usage-guide templates by project type
# ---------------------------------------------------------------------------
# Each entry maps a lowercased project-type keyword to a list of plain-English
# steps that describe how to use a project of that kind.  The first matching
# template wins; a generic fallback is used when nothing matches.
# ---------------------------------------------------------------------------
_USAGE_GUIDE_TEMPLATES: list[tuple[str, list[str]]] = [
    ("api", [
        "Start the backend server (see installation steps above)",
        "Send HTTP requests to the available API endpoints",
        "Refer to the API documentation (e.g. /docs on FastAPI) for endpoint details",
        "Use tools such as curl, Postman, or a frontend client to interact with the API",
    ]),
    ("web app", [
        "Install dependencies and start the development server",
        "Open the application in your browser at the address shown in the terminal",
        "Use the UI to interact with the application features",
        "Build for production when ready to deploy",
    ]),
    ("cli", [
        "Install the tool (see installation steps above)",
        "Run the CLI command with `--help` to see available options",
        "Pass the required arguments and flags to execute the desired operation",
        "Check the output in your terminal",
    ]),
    ("library", [
        "Install the package via your language's package manager",
        "Import the library in your project",
        "Refer to the API reference or examples for usage details",
        "Run the provided tests to verify correct integration",
    ]),
    ("ml", [
        "Prepare your dataset according to the data format described in the README",
        "Run the training script to train the model",
        "Evaluate the trained model using the provided evaluation script",
        "Use the inference script or API endpoint to generate predictions",
    ]),
    ("data", [
        "Configure the data sources and output paths",
        "Run the pipeline entrypoint to process data",
        "Inspect the output files or database tables",
        "Schedule the pipeline for recurring runs if needed",
    ]),
    ("mobile", [
        "Open the project in your mobile IDE (Android Studio / Xcode)",
        "Connect a device or start an emulator",
        "Build and run the application on the target device",
        "Follow on-screen prompts to explore app features",
    ]),
]

_GENERIC_USAGE_GUIDE: list[str] = [
    "Clone the repository and follow the installation steps",
    "Read the project README for detailed usage instructions",
    "Explore the source code to understand available features",
    "Run any provided example scripts to see the project in action",
]


def generate_repo_documentation(
    metadata: dict,
    insights: dict,
    readme_analysis: dict,
    architecture: dict,
) -> dict:
    """
    Build structured, human-readable documentation for a repository.

    Synthesises information already gathered during the analysis pipeline
    (metadata, insights, README analysis, and architecture) into a coherent
    documentation object that can be rendered directly in the frontend or
    exported as Markdown.

    Output fields
    -------------
    ``project_overview``
        A concise description of the project.  Priority order:
        1. ``metadata.description`` (the GitHub repo description)
        2. ``readme_analysis.purpose`` (extracted from the README)
        3. Generic fallback mentioning the repo name.

    ``tech_stack``
        The deduplicated technology list from ``insights.tech_stack``.
        Falls back to an empty list when not available.

    ``architecture_summary``
        The plain-English explanation from ``architecture.explanation``.
        Falls back to the ``insights.architecture_hint`` if the explanation
        is absent, then to a generic sentence.

    ``installation_steps``
        Derived from ``readme_analysis.setup``:
        - If the setup string contains multiple lines, each non-empty line
          becomes a step.
        - Otherwise the whole string is wrapped in a single-item list.
        Falls back to a minimal generic sequence when setup is empty.

    ``usage_guide``
        Selected from ``_USAGE_GUIDE_TEMPLATES`` by matching the
        ``insights.project_type`` against the template keys.  Falls back
        to ``_GENERIC_USAGE_GUIDE``.

    Args:
        metadata:        Repository metadata dict (name, description, …).
        insights:        Insights dict from repo_parser.analyse_repo.
        readme_analysis: README analysis dict from ai_engine.generate_readme_analysis.
        architecture:    Architecture dict from ai_engine.generate_architecture_analysis.

    Returns:
        A dict with keys: ``project_overview`` (str), ``tech_stack`` (list[str]),
        ``architecture_summary`` (str), ``installation_steps`` (list[str]),
        ``usage_guide`` (list[str]).
    """
    metadata        = metadata        or {}
    insights        = insights        or {}
    readme_analysis = readme_analysis or {}
    architecture    = architecture    or {}

    # ── Project overview ──────────────────────────────────────────────────────
    project_overview: str = (
        (metadata.get("description") or "").strip()
        or (readme_analysis.get("purpose") or "").strip()
        or f"{metadata.get('name') or 'This project'} is a software project hosted on GitHub."
    )

    # ── Tech stack ────────────────────────────────────────────────────────────
    tech_stack: list[str] = list(insights.get("tech_stack") or [])

    # ── Architecture summary ──────────────────────────────────────────────────
    architecture_summary: str = (
        (architecture.get("explanation") or "").strip()
        or (insights.get("architecture_hint") or "").strip()
        or "No architecture information is available for this repository."
    )

    # ── Installation steps ────────────────────────────────────────────────────
    setup_text: str = (readme_analysis.get("setup") or "").strip()
    if setup_text:
        # Split on newlines; each non-empty line becomes one numbered step
        raw_lines = [ln.strip() for ln in setup_text.splitlines() if ln.strip()]
        installation_steps: list[str] = raw_lines if raw_lines else [setup_text]
    else:
        installation_steps = [
            "Clone the repository: git clone <repo-url>",
            "Navigate into the project directory",
            "Install dependencies using your package manager",
            "Follow the README for any additional configuration",
            "Start the application",
        ]

    # ── Usage guide ───────────────────────────────────────────────────────────
    project_type_lower = (insights.get("project_type") or "").lower()
    usage_guide: list[str] = _GENERIC_USAGE_GUIDE  # default

    for keyword, template in _USAGE_GUIDE_TEMPLATES:
        if keyword in project_type_lower:
            usage_guide = template
            break

    return {
        "project_overview":    project_overview,
        "tech_stack":          tech_stack,
        "architecture_summary": architecture_summary,
        "installation_steps":  installation_steps,
        "usage_guide":         usage_guide,
    }


# ===========================================================================
# RepoLens AI Agent
# ===========================================================================

# ---------------------------------------------------------------------------
# Intent routing rules
# ---------------------------------------------------------------------------
# Each rule is a tuple of (trigger_keywords, answer_builder).
# The answer_builder receives repo_data and returns a plain-English string.
# Rules are evaluated in order; the first match wins.
# ---------------------------------------------------------------------------

def _fmt_list(items: list, separator: str = "\n• ") -> str:
    """Format a list of strings as a bulleted plain-text block."""
    if not items:
        return "No information available."
    return separator + separator.join(str(i) for i in items)


def _safe_get(data: dict, *keys, default=""):
    """Safely traverse nested dicts; return default on any missing key."""
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur if cur is not None else default


_AGENT_RULES: list[tuple[list[str], callable]] = [
    # Purpose / overview
    (
        ["what does", "purpose", "overview", "about", "what is", "describe"],
        lambda d: (
            _safe_get(d, "summary")
            or _safe_get(d, "documentation", "project_overview")
            or "No summary available for this repository."
        ),
    ),
    # Tech stack / frameworks / languages
    (
        ["tech stack", "framework", "library", "language", "built with", "technology", "dependencies"],
        lambda d: (
            "This repository uses the following technologies:"
            + _fmt_list(_safe_get(d, "insights", "tech_stack", default=[]))
        ),
    ),
    # Architecture
    (
        ["architect", "design", "structure", "layer", "pattern", "how is it organised", "how is it organized"],
        lambda d: (
            _safe_get(d, "architecture", "explanation")
            or _safe_get(d, "insights", "architecture_hint")
            or "No architecture information is available."
        ),
    ),
    # Installation / running
    (
        ["run", "install", "setup", "start", "launch", "deploy", "get started", "how to use"],
        lambda d: (
            "Here are the installation steps:"
            + _fmt_list(_safe_get(d, "documentation", "installation_steps", default=[]))
        ),
    ),
    # Usage guide
    (
        ["usage", "use", "how do i", "guide", "tutorial", "example", "demo"],
        lambda d: (
            "Here is the usage guide:"
            + _fmt_list(_safe_get(d, "documentation", "usage_guide", default=[]))
        ),
    ),
    # Security
    (
        ["security", "vulnerability", "risk", "exploit", "safe", "threat", "credentials"],
        lambda d: (
            "Here are the detected security risks:"
            + _fmt_list(_safe_get(d, "code_review", "security_risks", default=[]))
        ),
    ),
    # Performance
    (
        ["performance", "speed", "optimis", "optimiz", "slow", "fast", "latency", "memory"],
        lambda d: (
            "Here are the performance notes:"
            + _fmt_list(_safe_get(d, "code_review", "performance_notes", default=[]))
        ),
    ),
    # Code quality / score  ← must appear BEFORE the best-practices rule
    # because "quality" is a trigger word in both; the specific score query
    # should win over the generic best-practices query.
    (
        ["quality score", "how good", "code score", "repo score", "rating", "grade"],
        lambda d: (
            f"The code quality score for this repository is "
            f"{_safe_get(d, 'code_review', 'quality_score', default='N/A')} / 10."
        ),
    ),
    # Best practices
    (
        ["best practice", "improve", "recommendation", "suggestion", "quality"],
        lambda d: (
            "Here are the best-practice recommendations:"
            + _fmt_list(_safe_get(d, "code_review", "best_practices", default=[]))
        ),
    ),
    # Code quality / score
    (
        ["quality", "score", "rating", "grade", "how good"],
        lambda d: (
            f"The code quality score for this repository is "
            f"{_safe_get(d, 'code_review', 'quality_score', default='N/A')} / 10."
        ),
    ),
    # Project type
    (
        ["project type", "what kind", "what type", "category", "genre"],
        lambda d: (
            f"This is a {_safe_get(d, 'insights', 'project_type', default='software project')}."
        ),
    ),
    # README
    (
        ["readme", "documentation", "docs", "document"],
        lambda d: (
            _safe_get(d, "readme_analysis", "purpose")
            or _safe_get(d, "documentation", "project_overview")
            or "No README information is available."
        ),
    ),
    # Complexity
    (
        ["complex", "difficult", "hard", "effort", "time", "how long"],
        lambda d: (
            f"This project has {_safe_get(d, 'insights', 'complexity', 'difficulty', default='unknown').lower()}-level "
            f"complexity (score {_safe_get(d, 'insights', 'complexity', 'score', default='N/A')} / 10). "
            f"Estimated development time: {_safe_get(d, 'insights', 'complexity', 'estimated_dev_time', default='unknown')}."
        ),
    ),
]


def generate_agent_answer(question: str, repo_data: dict) -> dict:
    """
    Answer a natural-language question about a repository using rule-based intent routing.

    The function lowercases the question and checks it against each entry in
    ``_AGENT_RULES`` in order.  The first rule whose trigger keywords contain
    a substring match against the question wins; its answer-builder is called
    with ``repo_data`` to produce the response.

    If no rule matches, a fallback response is returned that includes the
    project summary so the user always receives something useful.

    Args:
        question:  The user's plain-English question string.
        repo_data: The full JSON dict returned by the ``/analyse`` endpoint.

    Returns:
        A dict ``{"answer": str}`` — always non-empty, never raises.
    """
    question  = (question  or "").strip()
    repo_data = repo_data  or {}

    if not question:
        return {"answer": "Please ask a question about the repository."}

    q_lower = question.lower()

    try:
        for trigger_keywords, answer_builder in _AGENT_RULES:
            if any(kw in q_lower for kw in trigger_keywords):
                answer = answer_builder(repo_data)
                if answer and str(answer).strip():
                    return {"answer": str(answer).strip()}

        # ── Fallback ─────────────────────────────────────────────────────────
        fallback_summary = (
            _safe_get(repo_data, "summary")
            or _safe_get(repo_data, "documentation", "project_overview")
            or "No information is available for this repository."
        )
        return {
            "answer": (
                f"I couldn't find an exact answer to that question, "
                f"but here is the project summary: {fallback_summary}"
            )
        }

    except Exception:
        return {
            "answer": (
                "I encountered an error while processing your question. "
                "Please try rephrasing it."
            )
        }


# ===========================================================================
# RAG-Based AI Repository Agent
# ===========================================================================
#
# Architecture
# ------------
# The RAG pipeline has five stages:
#
#   build_repo_knowledge  → converts repo_data into plain-text chunks
#   generate_embeddings   → encodes chunks into dense vectors
#   build_vector_index    → stores vectors in a FAISS index (or NumPy fallback)
#   retrieve_context      → embeds the question, finds top-k nearest chunks
#   generate_rag_answer   → synthesises a grounded answer from retrieved chunks
#
# Embedding back-end selection (automatic, no configuration required)
# -------------------------------------------------------------------
# Priority 1 — sentence-transformers + faiss-cpu   (best quality)
#              Install:  pip install sentence-transformers faiss-cpu
# Priority 2 — scikit-learn TF-IDF + NumPy cosine  (always available)
#
# The correct back-end is chosen at import time and is completely transparent
# to callers — the public API is identical regardless of which is active.
# ---------------------------------------------------------------------------

import math
import numpy as np

# ── Back-end detection ────────────────────────────────────────────────────────
# sentence-transformers availability is probed at import time WITHOUT loading
# the model weights — we only check that the package can be imported.
# The model itself is loaded lazily on first use via get_embedding_model().

_SENTENCE_TRANSFORMERS_AVAILABLE = False
_FAISS_AVAILABLE = False

try:
    import sentence_transformers as _sentence_transformers_pkg  # noqa: F401 — probe only
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    pass

try:
    import faiss as _faiss
    _FAISS_AVAILABLE = True
except Exception:
    _faiss = None  # type: ignore

# TF-IDF fallback (always available via scikit-learn)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer as _TfidfVectorizer
    _SKLEARN_AVAILABLE = True
except Exception:
    _SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Lazy model loader — the SentenceTransformer weights are NOT loaded at import
# time.  They are downloaded / read from disk on the first RAG request and then
# cached in this module-level variable for the lifetime of the process.
# ---------------------------------------------------------------------------
_st_model = None   # populated on first call to get_embedding_model()


def get_embedding_model():
    """
    Return the cached SentenceTransformer model, loading it on first call.

    The model is loaded lazily so that FastAPI starts instantly and the
    ``/docs`` page is available immediately.  Subsequent calls return the
    already-loaded instance with zero overhead.

    Returns:
        A ``SentenceTransformer`` instance, or ``None`` if the package is
        not installed (callers fall back to the TF-IDF backend automatically).
    """
    global _st_model
    if _st_model is not None:
        return _st_model          # already loaded — return immediately

    if not _SENTENCE_TRANSFORMERS_AVAILABLE:
        return None               # package not installed — use TF-IDF fallback

    try:
        from sentence_transformers import SentenceTransformer as _SentenceTransformer
        _st_model = _SentenceTransformer("all-MiniLM-L6-v2")
        return _st_model
    except Exception:
        # Model download failed or weights are corrupt — degrade gracefully
        return None


# ── Knowledge-base builder ────────────────────────────────────────────────────

def build_repo_knowledge(repo_data: dict) -> list[str]:
    """
    Convert a repository analysis dict into a list of plain-text knowledge chunks.

    Each chunk is a self-contained paragraph that can be independently embedded
    and retrieved.  Chunks are labelled with a short topic prefix so that the
    language model can easily identify the source of each passage.

    Args:
        repo_data: Full JSON dict returned by ``GET /analyse``.

    Returns:
        A list of non-empty plain-text strings.  Always returns at least one
        chunk even when ``repo_data`` is empty or ``None``.
    """
    repo_data = repo_data or {}
    chunks: list[str] = []

    def _safe(data: dict, *keys, default: str = "") -> str:
        cur = data
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k, default)
        return str(cur).strip() if cur else default

    def _safe_list(data: dict, *keys) -> list:
        cur = data
        for k in keys:
            if not isinstance(cur, dict):
                return []
            cur = cur.get(k, [])
        return cur if isinstance(cur, list) else []

    # 1 — Repository identity
    name        = _safe(repo_data, "metadata", "full_name") or _safe(repo_data, "repo")
    description = _safe(repo_data, "metadata", "description")
    if name or description:
        chunks.append(
            f"Repository: {name}. "
            + (f"Description: {description}" if description else "")
        )

    # 2 — AI summary
    summary = _safe(repo_data, "summary")
    if summary and summary != "Summary not available.":
        chunks.append(f"Project summary: {summary}")

    # 3 — README purpose
    purpose = _safe(repo_data, "readme_analysis", "purpose")
    if purpose:
        chunks.append(f"README purpose: {purpose}")

    # 4 — README key features
    features = _safe_list(repo_data, "readme_analysis", "key_features")
    if features:
        chunks.append("Key features: " + " | ".join(str(f) for f in features[:8]))

    # 5 — README setup instructions
    setup = _safe(repo_data, "readme_analysis", "setup")
    if setup:
        chunks.append(f"README setup / installation instructions: {setup}")

    # 6 — Project type and tech stack
    project_type = _safe(repo_data, "insights", "project_type")
    tech_stack   = _safe_list(repo_data, "insights", "tech_stack")
    frameworks   = _safe_list(repo_data, "insights", "frameworks")
    if project_type or tech_stack:
        ts = ", ".join(tech_stack[:10]) if tech_stack else "not detected"
        fw = ", ".join(frameworks[:8])  if frameworks  else "none"
        chunks.append(
            f"Project type: {project_type or 'unknown'}. "
            f"Tech stack: {ts}. "
            f"Frameworks: {fw}."
        )

    # 7 — Architecture
    arch_hint   = _safe(repo_data, "insights", "architecture_hint")
    arch_layers = _safe_list(repo_data, "architecture", "layers")
    arch_exp    = _safe(repo_data, "architecture", "explanation")
    arch_struct = _safe_list(repo_data, "architecture", "structure")
    if arch_exp or arch_hint:
        layer_str  = ", ".join(arch_layers[:8]) if arch_layers  else "not detected"
        struct_str = ", ".join(arch_struct[:10]) if arch_struct else ""
        chunks.append(
            f"Architecture: {arch_exp or arch_hint}. "
            f"Layers: {layer_str}. "
            + (f"Top-level structure: {struct_str}." if struct_str else "")
        )

    # 8 — Complexity
    difficulty = _safe(repo_data, "insights", "complexity", "difficulty")
    dev_time   = _safe(repo_data, "insights", "complexity", "estimated_dev_time")
    score_raw  = (repo_data.get("insights") or {}).get("complexity", {}).get("score")
    if difficulty:
        chunks.append(
            f"Project complexity: {difficulty} "
            + (f"(score {score_raw}/10)" if score_raw is not None else "")
            + (f". Estimated development time: {dev_time}." if dev_time else ".")
        )

    # 9 — Code quality score
    quality_score = (repo_data.get("code_review") or {}).get("quality_score")
    if quality_score is not None:
        chunks.append(f"Code quality score: {quality_score}/10.")

    # 10 — Security risks
    security_risks = _safe_list(repo_data, "code_review", "security_risks")
    if security_risks:
        chunks.append(
            "Security risks identified: "
            + " | ".join(str(r) for r in security_risks[:6])
        )

    # 11 — Performance notes
    perf_notes = _safe_list(repo_data, "code_review", "performance_notes")
    if perf_notes:
        chunks.append(
            "Performance recommendations: "
            + " | ".join(str(p) for p in perf_notes[:5])
        )

    # 12 — Best practices
    best_practices = _safe_list(repo_data, "code_review", "best_practices")
    if best_practices:
        chunks.append(
            "Best practices: "
            + " | ".join(str(b) for b in best_practices[:6])
        )

    # 13 — Documentation overview
    doc_overview = _safe(repo_data, "documentation", "project_overview")
    if doc_overview and doc_overview != description:
        chunks.append(f"Documentation overview: {doc_overview}")

    # 14 — Installation steps (from documentation)
    install_steps = _safe_list(repo_data, "documentation", "installation_steps")
    if install_steps:
        chunks.append(
            "Installation steps: "
            + " → ".join(str(s) for s in install_steps[:8])
        )

    # 15 — Usage guide
    usage_guide = _safe_list(repo_data, "documentation", "usage_guide")
    if usage_guide:
        chunks.append(
            "Usage guide: "
            + " → ".join(str(u) for u in usage_guide[:6])
        )

    # 16 — Language breakdown
    languages = repo_data.get("languages") or {}
    if languages:
        total = sum(languages.values()) or 1
        lang_str = ", ".join(
            f"{lang} ({round(bytes_/total*100)}%)"
            for lang, bytes_ in sorted(languages.items(), key=lambda x: -x[1])[:6]
        )
        chunks.append(f"Programming languages used: {lang_str}.")

    # Guarantee at least one chunk
    if not chunks:
        chunks.append("No detailed repository information is available.")

    return chunks


# ── Embedding layer ───────────────────────────────────────────────────────────

class _TFIDFEmbedder:
    """
    Lightweight TF-IDF embedding backend using scikit-learn.

    Produces L2-normalised dense float32 vectors that can be used for cosine
    similarity search via NumPy.  Used automatically when sentence-transformers
    is not installed.
    """

    def __init__(self) -> None:
        self._vectorizer: "_TfidfVectorizer | None" = None
        self._corpus_matrix = None   # shape: (n_chunks, n_features)

    def fit_transform(self, texts: list[str]):
        """Fit vocabulary on corpus and return normalised dense matrix."""
        if not _SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is required for TF-IDF embeddings")
        self._vectorizer = _TfidfVectorizer(
            strip_accents="unicode",
            lowercase=True,
            ngram_range=(1, 2),
            max_features=8192,
            sublinear_tf=True,
        )
        sparse = self._vectorizer.fit_transform(texts)
        dense  = sparse.toarray().astype(np.float32)
        # L2 normalise each row
        norms  = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._corpus_matrix = dense / norms
        return self._corpus_matrix

    def transform(self, texts: list[str]):
        """Transform new texts using the fitted vocabulary."""
        if self._vectorizer is None:
            raise RuntimeError("Call fit_transform first")
        sparse = self._vectorizer.transform(texts)
        dense  = sparse.toarray().astype(np.float32)
        norms  = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return dense / norms


def generate_embeddings(chunks: list[str]):
    """
    Encode a list of text chunks into dense embedding vectors.

    Automatically selects the best available backend:
    - sentence-transformers ``all-MiniLM-L6-v2`` when installed (384-dim).
      The model is loaded lazily on the first call via ``get_embedding_model()``
      and cached for the lifetime of the process.
    - scikit-learn TF-IDF with L2 normalisation otherwise (up to 8192-dim).

    Args:
        chunks: List of plain-text strings produced by ``build_repo_knowledge``.

    Returns:
        Either a numpy ndarray (shape ``[n, dim]``) for the sentence-transformers
        backend, or a fitted ``_TFIDFEmbedder`` instance for the TF-IDF backend.
        The return value is opaque to callers — pass it directly to
        ``build_vector_index``.
    """
    if not chunks:
        raise ValueError("chunks must not be empty")

    model = get_embedding_model()
    if model is not None:
        embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.astype(np.float32)
    else:
        embedder = _TFIDFEmbedder()
        embedder.fit_transform(chunks)
        return embedder   # caller passes this to build_vector_index + retrieve_context


# ── Vector index ──────────────────────────────────────────────────────────────

class _NumpyIndex:
    """
    Minimal L2-cosine vector index backed by NumPy.

    Used as a drop-in replacement for FAISS when faiss-cpu is not installed.
    Stores the normalised corpus matrix and answers nearest-neighbour queries
    with a single matrix–vector dot product.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        # matrix rows are already L2-normalised; dot product == cosine similarity
        self._matrix = matrix

    def search(self, query_vec: np.ndarray, k: int):
        """Return (distances, indices) for the top-k most similar chunks."""
        query_vec = query_vec.flatten().astype(np.float32)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm
        scores  = self._matrix @ query_vec          # cosine similarities
        k       = min(k, len(scores))
        top_idx = np.argsort(scores)[::-1][:k]
        return scores[top_idx], top_idx


def build_vector_index(embeddings):
    """
    Store embedding vectors in a searchable index.

    Automatically selects the best available backend:
    - FAISS ``IndexFlatIP`` (inner-product / cosine on normalised vectors)
    - ``_NumpyIndex`` cosine-similarity index otherwise

    Args:
        embeddings: The return value of ``generate_embeddings`` — either a
                    numpy ndarray or a fitted ``_TFIDFEmbedder`` instance.

    Returns:
        An opaque index object accepted by ``retrieve_context``.
    """
    # sentence-transformers path → numpy array → FAISS or NumpyIndex
    if isinstance(embeddings, np.ndarray):
        matrix = embeddings.astype(np.float32)
        # L2-normalise so inner product == cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        matrix = matrix / norms

        if _FAISS_AVAILABLE and _faiss is not None:
            dim   = matrix.shape[1]
            index = _faiss.IndexFlatIP(dim)
            index.add(matrix)
            return index
        else:
            return _NumpyIndex(matrix)

    # TF-IDF path → _TFIDFEmbedder already holds its own corpus matrix
    if isinstance(embeddings, _TFIDFEmbedder):
        return _NumpyIndex(embeddings._corpus_matrix)

    raise TypeError(f"Unsupported embeddings type: {type(embeddings)}")


# ── Context retrieval ─────────────────────────────────────────────────────────

def retrieve_context(
    question: str,
    chunks: list[str],
    index,
    embedder=None,
    top_k: int = 3,
) -> str:
    """
    Embed the user's question and return the top-k most relevant knowledge chunks.

    The question is encoded with the same backend used during indexing (detected
    automatically from the type of ``index``), and the nearest neighbours are
    retrieved via inner-product search.

    Args:
        question: The user's plain-English question.
        chunks:   The list returned by ``build_repo_knowledge``.
        index:    The index returned by ``build_vector_index``.
        embedder: Required when using the TF-IDF backend — pass the same
                  ``_TFIDFEmbedder`` instance returned by ``generate_embeddings``.
        top_k:    Number of chunks to retrieve (default: 3).

    Returns:
        A single string containing the top-k chunks joined by double newlines.
    """
    if not chunks or not question:
        return " ".join(chunks) if chunks else ""

    top_k = min(top_k, len(chunks))

    try:
        # Encode the question using whichever backend was used for the chunks.
        # get_embedding_model() returns the cached model (no reload penalty).
        model = get_embedding_model()
        if model is not None and not isinstance(embedder, _TFIDFEmbedder):
            q_vec = model.encode([question], convert_to_numpy=True, show_progress_bar=False)
            q_vec = q_vec.astype(np.float32)
        elif isinstance(embedder, _TFIDFEmbedder):
            q_vec = embedder.transform([question])
        else:
            # Plain fallback: keyword overlap scoring (no vector model needed)
            q_lower = question.lower()
            scores  = [
                sum(1 for word in q_lower.split() if word in chunk.lower())
                for chunk in chunks
            ]
            top_idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
            return "\n\n".join(chunks[i] for i in top_idx)

        # Query the index
        if isinstance(index, _NumpyIndex):
            _, top_idx = index.search(q_vec[0], top_k)
        else:
            # FAISS returns (distances, indices) arrays; indices shape is (1, k)
            _, raw_idx = index.search(q_vec, top_k)
            top_idx = raw_idx[0]

        return "\n\n".join(chunks[int(i)] for i in top_idx if 0 <= int(i) < len(chunks))

    except Exception:
        # Fallback: return the first top_k chunks verbatim
        return "\n\n".join(chunks[:top_k])


# ── Answer generation ─────────────────────────────────────────────────────────

def generate_rag_answer(question: str, context: str) -> dict:
    """
    Synthesise a grounded natural-language answer from retrieved context chunks.

    The answer is composed by matching the question intent against the context
    text, then constructing a coherent response that cites specific passages.
    Because we are running without an LLM API call, the synthesis is done via
    structured template selection — the answer always clearly attributes its
    content to the retrieved repository information.

    Args:
        question: The user's plain-English question.
        context:  The concatenated context string from ``retrieve_context``.

    Returns:
        A dict ``{"answer": str}`` — always non-empty, never raises.
    """
    question = (question or "").strip()
    context  = (context  or "").strip()

    if not context:
        return {"answer": "No relevant repository information was found to answer this question."}

    if not question:
        return {"answer": f"Based on the repository information:\n\n{context}"}

    q_lower = question.lower()

    try:
        # ── Template selection based on question intent ───────────────────────
        INTRO = "Based on the repository information:\n\n"

        # Security questions — lead with the relevant context chunk
        if any(kw in q_lower for kw in ("security", "vulnerability", "risk", "safe", "credentials")):
            sec_lines = [ln for ln in context.splitlines() if "security" in ln.lower() or "risk" in ln.lower()]
            body = "\n".join(sec_lines) if sec_lines else context
            return {"answer": f"{INTRO}{body}\n\nReview these risks and address them before deploying to production."}

        # Installation / setup
        if any(kw in q_lower for kw in ("install", "run", "setup", "start", "deploy", "get started")):
            install_lines = [ln for ln in context.splitlines() if any(k in ln.lower() for k in ("install", "step", "clone", "run", "→"))]
            body = "\n".join(install_lines) if install_lines else context
            return {"answer": f"{INTRO}{body}"}

        # Architecture / structure
        if any(kw in q_lower for kw in ("architect", "structure", "design", "layer", "pattern")):
            arch_lines = [ln for ln in context.splitlines() if any(k in ln.lower() for k in ("architect", "layer", "structure", "pattern"))]
            body = "\n".join(arch_lines) if arch_lines else context
            return {"answer": f"{INTRO}{body}"}

        # Tech stack / frameworks
        if any(kw in q_lower for kw in ("tech", "framework", "language", "stack", "built with", "technology")):
            tech_lines = [ln for ln in context.splitlines() if any(k in ln.lower() for k in ("tech", "framework", "language", "stack"))]
            body = "\n".join(tech_lines) if tech_lines else context
            return {"answer": f"{INTRO}{body}"}

        # Performance
        if any(kw in q_lower for kw in ("performance", "speed", "optim", "slow", "fast", "memory")):
            perf_lines = [ln for ln in context.splitlines() if "performance" in ln.lower() or "optim" in ln.lower()]
            body = "\n".join(perf_lines) if perf_lines else context
            return {"answer": f"{INTRO}{body}"}

        # Quality / score
        if any(kw in q_lower for kw in ("quality", "score", "rating", "grade")):
            quality_lines = [ln for ln in context.splitlines() if "quality" in ln.lower() or "score" in ln.lower()]
            body = "\n".join(quality_lines) if quality_lines else context
            return {"answer": f"{INTRO}{body}"}

        # Default: return all retrieved context with a grounding prefix
        return {"answer": f"{INTRO}{context}"}

    except Exception:
        return {"answer": f"Based on the repository information:\n\n{context}"}