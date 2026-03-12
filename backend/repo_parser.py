"""
repo_parser.py
--------------
RepoLens AI — Repository insight engine.

Analyses GitHub repository metadata and programming language data to surface
human-readable insights about a project:

  - Project type       (Web app, CLI tool, Library, etc.)
  - Frameworks         (Django, React, FastAPI, etc.)
  - Main modules       (inferred from languages and keywords)
  - Architecture       (MVC, microservices, serverless, etc.)
  - Tech stack         (flat, deduplicated list)
  - Complexity         (numeric score, difficulty label, dev-time estimate)
  - Architecture graph (nodes + directed edges for visual rendering)

Public API
----------
    analyse_repo(metadata, languages) -> dict
    generate_architecture_graph(modules, arch_hint, tech_stack) -> dict

All other functions are internal helpers prefixed with an underscore.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Metadata  = dict   # GitHub repo metadata as returned by github_fetcher.py
Languages = dict   # {"Python": 14321, "JavaScript": 3400, ...}


# ---------------------------------------------------------------------------
# Knowledge bases  (keyword → label)
# ---------------------------------------------------------------------------

_LANG_TYPE_RULES: list[tuple[frozenset, str]] = [
    (frozenset({"JavaScript", "TypeScript", "HTML", "CSS"}), "Web App"),
    (frozenset({"TypeScript", "HTML"}),                      "Web App"),
    (frozenset({"JavaScript", "HTML"}),                      "Web App"),
    (frozenset({"Kotlin", "Java"}),                          "Android App"),
    (frozenset({"Swift", "Objective-C"}),                    "iOS App"),
    (frozenset({"Dart"}),                                    "Mobile App"),
    (frozenset({"Dockerfile", "Shell"}),                     "DevOps / Infrastructure"),
    (frozenset({"HCL"}),                                     "Infrastructure as Code"),
]

_FRAMEWORK_KEYWORDS: dict[str, list[str]] = {
    # Python
    "django":       ["Django"],
    "flask":        ["Flask"],
    "fastapi":      ["FastAPI"],
    "tornado":      ["Tornado"],
    "aiohttp":      ["aiohttp"],
    "starlette":    ["Starlette"],
    "celery":       ["Celery"],
    "sqlalchemy":   ["SQLAlchemy"],
    "alembic":      ["Alembic"],
    "pydantic":     ["Pydantic"],
    "pytest":       ["pytest"],
    "click":        ["Click"],
    "typer":        ["Typer"],
    "scrapy":       ["Scrapy"],
    "huggingface":  ["Hugging Face"],
    "transformers": ["Hugging Face Transformers"],
    "langchain":    ["LangChain"],
    "openai":       ["OpenAI SDK"],
    "anthropic":    ["Anthropic SDK"],
    # JavaScript / TypeScript
    "react":        ["React"],
    "nextjs":       ["Next.js"],
    "next.js":      ["Next.js"],
    "nuxt":         ["Nuxt.js"],
    "vue":          ["Vue.js"],
    "angular":      ["Angular"],
    "svelte":       ["Svelte"],
    "express":      ["Express.js"],
    "nestjs":       ["NestJS"],
    "nest.js":      ["NestJS"],
    "gatsby":       ["Gatsby"],
    "vite":         ["Vite"],
    "webpack":      ["Webpack"],
    "graphql":      ["GraphQL"],
    "apollo":       ["Apollo"],
    "prisma":       ["Prisma"],
    # Mobile
    "flutter":      ["Flutter"],
    "react-native": ["React Native"],
    "expo":         ["Expo"],
    # Infrastructure / DevOps
    "terraform":    ["Terraform"],
    "ansible":      ["Ansible"],
    "kubernetes":   ["Kubernetes"],
    "k8s":          ["Kubernetes"],
    "helm":         ["Helm"],
    "docker":       ["Docker"],
    # Data / ML
    "tensorflow":   ["TensorFlow"],
    "pytorch":      ["PyTorch"],
    "torch":        ["PyTorch"],
    "sklearn":      ["scikit-learn"],
    "scikit":       ["scikit-learn"],
    "pandas":       ["pandas"],
    "spark":        ["Apache Spark"],
    "airflow":      ["Apache Airflow"],
    "dbt":          ["dbt"],
    # Java / JVM
    "spring":       ["Spring Boot"],
    "quarkus":      ["Quarkus"],
    "micronaut":    ["Micronaut"],
    # Ruby
    "rails":        ["Ruby on Rails"],
    "sinatra":      ["Sinatra"],
    # Go
    "gin":          ["Gin"],
    "fiber":        ["Fiber"],
    "echo":         ["Echo"],
    # Rust
    "actix":        ["Actix"],
    "axum":         ["Axum"],
    # PHP
    "laravel":      ["Laravel"],
    "symfony":      ["Symfony"],
}

_MODULE_KEYWORDS: dict[str, str] = {
    "api":          "REST API",
    "rest":         "REST API",
    "graphql":      "GraphQL API",
    "grpc":         "gRPC Service",
    "auth":         "Authentication",
    "oauth":        "OAuth / SSO",
    "jwt":          "JWT Auth",
    "db":           "Database Layer",
    "database":     "Database Layer",
    "orm":          "ORM / Database Layer",
    "migration":    "Database Migrations",
    "cache":        "Caching Layer",
    "redis":        "Redis Integration",
    "queue":        "Message Queue",
    "worker":       "Background Workers",
    "task":         "Task Scheduler",
    "scheduler":    "Task Scheduler",
    "cli":          "CLI Interface",
    "scraper":      "Web Scraper",
    "crawler":      "Web Crawler",
    "parser":       "Data Parser",
    "dashboard":    "Admin Dashboard",
    "admin":        "Admin Panel",
    "frontend":     "Frontend UI",
    "backend":      "Backend Service",
    "webhook":      "Webhook Handler",
    "notification": "Notification Service",
    "email":        "Email Service",
    "ml":           "ML Pipeline",
    "model":        "ML / AI Model",
    "train":        "Model Training",
    "inference":    "Model Inference",
    "pipeline":     "Data Pipeline",
    "etl":          "ETL Pipeline",
    "stream":       "Data Streaming",
    "logger":       "Logging Module",
    "monitor":      "Monitoring",
    "test":         "Test Suite",
    "deploy":       "Deployment Scripts",
    "docker":       "Containerisation",
    "k8s":          "Kubernetes Manifests",
    "terraform":    "IaC (Terraform)",
}

_ARCH_RULES: list[tuple[set[str], str]] = [
    ({"microservice", "service"},      "Microservices Architecture"),
    ({"serverless", "lambda"},         "Serverless Architecture"),
    ({"event", "driven"},              "Event-Driven Architecture"),
    ({"grpc", "proto"},                "gRPC / Protobuf Service"),
    ({"graphql"},                      "GraphQL API"),
    ({"monolith"},                     "Monolithic Architecture"),
    ({"mvc"},                          "MVC Pattern"),
    ({"mvvm"},                         "MVVM Pattern"),
    ({"clean", "architecture"},        "Clean Architecture"),
    ({"ddd", "domain"},                "Domain-Driven Design (DDD)"),
    ({"cqrs"},                         "CQRS Pattern"),
    ({"hexagonal"},                    "Hexagonal Architecture"),
    ({"pipeline"},                     "Pipeline / ETL Architecture"),
    ({"plugin"},                       "Plugin-Based Architecture"),
    ({"sdk", "library"},               "SDK / Library"),
    ({"cli"},                          "CLI Tool"),
]


# ---------------------------------------------------------------------------
# Tech-stack knowledge base
# ---------------------------------------------------------------------------

_DISPLAYABLE_LANGUAGES: set[str] = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Kotlin",
    "Swift", "Dart", "Ruby", "PHP", "C", "C++", "C#", "Scala", "Elixir",
    "Haskell", "Clojure", "R", "MATLAB", "Julia", "Lua", "Perl",
    "Jupyter Notebook", "Shell", "Dockerfile", "HCL",
}

_TECH_STACK_RULES: list[tuple[str, list[str]]] = [
    # ── Python web frameworks ────────────────────────────────────────────────
    ("fastapi",        ["FastAPI", "REST API"]),
    ("flask",          ["Flask", "REST API"]),
    ("django",         ["Django"]),
    ("tornado",        ["Tornado"]),
    ("aiohttp",        ["aiohttp"]),
    ("starlette",      ["Starlette"]),
    # ── Python data / ML ────────────────────────────────────────────────────
    ("tensorflow",     ["TensorFlow", "Machine Learning"]),
    ("pytorch",        ["PyTorch",    "Machine Learning"]),
    ("torch",          ["PyTorch",    "Machine Learning"]),
    ("sklearn",        ["scikit-learn","Machine Learning"]),
    ("scikit",         ["scikit-learn","Machine Learning"]),
    ("pandas",         ["pandas",     "Data Science"]),
    ("numpy",          ["NumPy",      "Data Science"]),
    ("keras",          ["Keras",      "Machine Learning"]),
    ("huggingface",    ["Hugging Face","Machine Learning", "NLP"]),
    ("transformers",   ["Hugging Face Transformers", "Machine Learning", "NLP"]),
    ("langchain",      ["LangChain",  "LLM / GenAI"]),
    ("openai",         ["OpenAI SDK", "LLM / GenAI"]),
    ("anthropic",      ["Anthropic SDK","LLM / GenAI"]),
    ("ml",             ["Machine Learning"]),
    ("machine learn",  ["Machine Learning"]),
    ("deep learn",     ["Machine Learning", "Deep Learning"]),
    ("llm",            ["LLM / GenAI"]),
    ("generative",     ["LLM / GenAI"]),
    ("diffusion",      ["Machine Learning", "Generative AI"]),
    # ── Python task / async ──────────────────────────────────────────────────
    ("celery",         ["Celery", "Task Queue"]),
    ("redis",          ["Redis"]),
    ("sqlalchemy",     ["SQLAlchemy", "ORM"]),
    ("pydantic",       ["Pydantic"]),
    ("scrapy",         ["Scrapy", "Web Scraping"]),
    # ── JavaScript / TypeScript ──────────────────────────────────────────────
    ("react",          ["React"]),
    ("next js",        ["Next.js", "React"]),
    ("nextjs",         ["Next.js", "React"]),
    ("nuxt",           ["Nuxt.js", "Vue.js"]),
    ("vue",            ["Vue.js"]),
    ("angular",        ["Angular"]),
    ("svelte",         ["Svelte"]),
    ("express",        ["Express.js", "Node.js"]),
    ("nestjs",         ["NestJS",     "Node.js"]),
    ("node",           ["Node.js"]),
    ("vite",           ["Vite"]),
    ("graphql",        ["GraphQL"]),
    ("apollo",         ["Apollo",    "GraphQL"]),
    ("prisma",         ["Prisma",    "ORM"]),
    # ── Mobile ───────────────────────────────────────────────────────────────
    ("flutter",        ["Flutter",       "Mobile App"]),
    ("react native",   ["React Native",  "Mobile App"]),
    ("expo",           ["Expo",          "Mobile App"]),
    ("swiftui",        ["SwiftUI",       "iOS"]),
    ("jetpack",        ["Jetpack Compose","Android"]),
    # ── Java / JVM ───────────────────────────────────────────────────────────
    ("spring",         ["Spring Boot"]),
    ("quarkus",        ["Quarkus"]),
    ("micronaut",      ["Micronaut"]),
    # ── Go ────────────────────────────────────────────────────────────────────
    ("gin",            ["Gin"]),
    ("fiber",          ["Fiber"]),
    # ── Rust ─────────────────────────────────────────────────────────────────
    ("actix",          ["Actix"]),
    ("axum",           ["Axum"]),
    # ── Ruby ─────────────────────────────────────────────────────────────────
    ("rails",          ["Ruby on Rails"]),
    ("sinatra",        ["Sinatra"]),
    # ── PHP ───────────────────────────────────────────────────────────────────
    ("laravel",        ["Laravel"]),
    ("symfony",        ["Symfony"]),
    # ── Infrastructure / DevOps ───────────────────────────────────────────────
    ("docker",         ["Docker"]),
    ("kubernetes",     ["Kubernetes"]),
    ("k8s",            ["Kubernetes"]),
    ("terraform",      ["Terraform",    "Infrastructure as Code"]),
    ("ansible",        ["Ansible"]),
    ("helm",           ["Helm",         "Kubernetes"]),
    ("ci cd",          ["CI/CD"]),
    ("github actions", ["GitHub Actions","CI/CD"]),
    # ── Data / Streaming ─────────────────────────────────────────────────────
    ("kafka",          ["Apache Kafka", "Data Streaming"]),
    ("spark",          ["Apache Spark", "Big Data"]),
    ("airflow",        ["Apache Airflow","Data Pipeline"]),
    ("dbt",            ["dbt",           "Data Pipeline"]),
    ("postgres",       ["PostgreSQL"]),
    ("postgresql",     ["PostgreSQL"]),
    ("mysql",          ["MySQL"]),
    ("mongodb",        ["MongoDB",       "NoSQL"]),
    ("elasticsearch",  ["Elasticsearch"]),
    # ── Paradigms / generic ───────────────────────────────────────────────────
    ("rest api",       ["REST API"]),
    ("api",            ["REST API"]),
    ("grpc",           ["gRPC"]),
    ("websocket",      ["WebSockets"]),
    ("cli",            ["CLI Tool"]),
    ("scraper",        ["Web Scraping"]),
    ("crawler",        ["Web Scraping"]),
]


# ---------------------------------------------------------------------------
# Architecture graph — node / edge classification tables
# ---------------------------------------------------------------------------

# Maps a normalised module label to a semantic category used when building
# the graph.  Categories determine node colour and edge direction heuristics.
_MODULE_CATEGORY: dict[str, str] = {
    "Frontend UI":              "frontend",
    "Frontend / Node.js Logic": "frontend",
    "Typed Frontend / Backend Logic": "frontend",
    "Admin Dashboard":          "frontend",
    "Admin Panel":              "frontend",
    "REST API":                 "api",
    "GraphQL API":              "api",
    "gRPC Service":             "api",
    "Backend Service":          "api",
    "Python Backend":           "api",
    "Go Service":               "api",
    "JVM Service":              "api",
    "Rust Core":                "api",
    "Authentication":           "auth",
    "OAuth / SSO":              "auth",
    "JWT Auth":                 "auth",
    "Database Layer":           "data",
    "ORM / Database Layer":     "data",
    "Database Migrations":      "data",
    "Caching Layer":            "data",
    "Redis Integration":        "data",
    "SQL Queries":              "data",
    "Message Queue":            "queue",
    "Background Workers":       "queue",
    "Task Scheduler":           "queue",
    "ML Pipeline":              "ml",
    "ML / AI Model":            "ml",
    "Model Training":           "ml",
    "Model Inference":          "ml",
    "Data Pipeline":            "ml",
    "ETL Pipeline":             "ml",
    "Data Streaming":           "ml",
    "Data Parser":              "ml",
    "Jupyter Notebooks":        "ml",
    "Containerisation":         "infra",
    "Kubernetes Manifests":     "infra",
    "IaC (Terraform)":          "infra",
    "Deployment Scripts":       "infra",
    "Shell / Bash Scripts":     "infra",
    "Terraform IaC":            "infra",
    "Webhook Handler":          "api",
    "Notification Service":     "queue",
    "Email Service":            "queue",
    "Logging Module":           "infra",
    "Monitoring":               "infra",
    "Test Suite":               "infra",
    "Styling / Theming":        "frontend",
    "CLI Interface":            "frontend",
    "Web Scraper":              "api",
    "Web Crawler":              "api",
}

# Category priority used to sort nodes into a natural left-to-right
# data-flow order: frontend → api → auth → data → queue → ml → infra
_CATEGORY_ORDER: dict[str, int] = {
    "frontend": 0,
    "api":      1,
    "auth":     2,
    "data":     3,
    "queue":    4,
    "ml":       5,
    "infra":    6,
}

# Natural edges: category A → category B if A communicates with B.
# Used to auto-wire edges between categories even if only one module of
# each category is present.
_CATEGORY_EDGES: list[tuple[str, str]] = [
    ("frontend", "api"),
    ("api",      "auth"),
    ("api",      "data"),
    ("api",      "queue"),
    ("api",      "ml"),
    ("queue",    "data"),
    ("queue",    "ml"),
    ("ml",       "data"),
    ("api",      "infra"),
    ("ml",       "infra"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_architecture_graph(
    modules: list[str],
    arch_hint: str = "",
    tech_stack: list[str] | None = None,
) -> dict:
    """
    Convert a list of detected module labels into a directed graph of nodes
    and edges suitable for rendering with React Flow (or any force-directed
    graph library).

    Algorithm
    ---------
    1.  Every module becomes a node.  Nodes carry an ``id``, ``label``,
        ``category``, and ``type`` field.  ``type`` is used by the frontend
        renderer to pick the node colour / icon.

    2.  Edges are generated from ``_CATEGORY_EDGES``:  for each
        (cat_A, cat_B) pair we look for one representative node from cat_A
        and one from cat_B; if both exist we add a directed edge
        ``cat_A_node → cat_B_node``.

    3.  If fewer than 2 modules are detected a minimal fallback graph is
        returned using the arch_hint string so the frontend always has
        something meaningful to render.

    4.  Nodes are positioned on a conceptual grid using their category order
        (``_CATEGORY_ORDER``).  The ``position`` dict (``{x, y}``) is
        included so React Flow can use it directly without a layout engine.

    Args:
        modules:    Module labels from ``_detect_main_modules``.
        arch_hint:  Architecture hint string (used in fallback graph).
        tech_stack: Tech stack tags (used to enrich fallback graph).

    Returns:
        A dict with keys:
          - ``nodes``:  list of node dicts
                        {id, label, category, type, position: {x, y}}
          - ``edges``:  list of edge dicts
                        {id, source, target}
    """
    tech_stack = tech_stack or []

    # ── 1. Build node list ────────────────────────────────────────────────────
    # Assign each module a category, de-duplicate by category so the graph
    # stays readable (at most ~2 nodes per category).
    category_nodes: dict[str, list[dict]] = {}

    for module in modules:
        cat = _MODULE_CATEGORY.get(module, "api")  # default to "api" tier
        slug = re.sub(r"[^a-z0-9]+", "_", module.lower())
        node: dict = {
            "id":       slug,
            "label":    module,
            "category": cat,
            "type":     cat,
        }
        category_nodes.setdefault(cat, []).append(node)

    # Keep at most 2 nodes per category to avoid a crowded graph
    all_nodes: list[dict] = []
    for cat in sorted(category_nodes, key=lambda c: _CATEGORY_ORDER.get(c, 99)):
        all_nodes.extend(category_nodes[cat][:2])

    # ── Fallback graph when no modules were detected ──────────────────────────
    if len(all_nodes) < 2:
        return _fallback_graph(arch_hint, tech_stack)

    # ── 2. Assign grid positions ──────────────────────────────────────────────
    # Horizontal position is determined by category order.
    # Within a column, nodes are stacked vertically 120 px apart.
    col_counters: dict[int, int] = {}
    for node in all_nodes:
        col = _CATEGORY_ORDER.get(node["category"], 6)
        row = col_counters.get(col, 0)
        node["position"] = {"x": col * 220, "y": row * 120}
        col_counters[col] = row + 1

    # ── 3. Build edges using category adjacency rules ─────────────────────────
    # Index nodes by category for fast lookup
    cat_to_nodes: dict[str, list[dict]] = {}
    for node in all_nodes:
        cat_to_nodes.setdefault(node["category"], []).append(node)

    edges: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for cat_a, cat_b in _CATEGORY_EDGES:
        sources = cat_to_nodes.get(cat_a, [])
        targets = cat_to_nodes.get(cat_b, [])
        if not sources or not targets:
            continue
        # Wire the first node of cat_a to the first node of cat_b
        src_id = sources[0]["id"]
        tgt_id = targets[0]["id"]
        if (src_id, tgt_id) not in seen_pairs:
            edges.append({
                "id":     f"{src_id}__{tgt_id}",
                "source": src_id,
                "target": tgt_id,
            })
            seen_pairs.add((src_id, tgt_id))

    # ── 4. Linear chain fallback ─────────────────────────────────────────────
    # If the category rules produced no edges (e.g. all modules are in the
    # same category), fall back to a simple sequential chain.
    if not edges:
        for i in range(len(all_nodes) - 1):
            src_id = all_nodes[i]["id"]
            tgt_id = all_nodes[i + 1]["id"]
            edges.append({
                "id":     f"{src_id}__{tgt_id}",
                "source": src_id,
                "target": tgt_id,
            })

    return {"nodes": all_nodes, "edges": edges}


def _fallback_graph(arch_hint: str, tech_stack: list[str]) -> dict:
    """
    Build a minimal 2-node graph when module detection returns too little data.
    Uses the architecture hint and tech stack to create meaningful labels.
    """
    label_a = tech_stack[0] if tech_stack else "Application"
    label_b = arch_hint or (tech_stack[1] if len(tech_stack) > 1 else "Service")

    slug_a = re.sub(r"[^a-z0-9]+", "_", label_a.lower())
    slug_b = re.sub(r"[^a-z0-9]+", "_", label_b.lower())

    # Avoid self-loops
    if slug_a == slug_b:
        slug_b = slug_b + "_2"
        label_b = label_b + " (2)"

    return {
        "nodes": [
            {"id": slug_a, "label": label_a, "category": "api",  "type": "api",  "position": {"x": 0,   "y": 0}},
            {"id": slug_b, "label": label_b, "category": "data", "type": "data", "position": {"x": 220, "y": 0}},
        ],
        "edges": [
            {"id": f"{slug_a}__{slug_b}", "source": slug_a, "target": slug_b},
        ],
    }


def analyse_repo(metadata: Metadata, languages: Languages) -> dict:
    """
    Analyse a GitHub repository and return structured insights.

    Args:
        metadata:  Repository metadata dict (from github_fetcher.fetch_repo_metadata).
        languages: Language breakdown dict   (from github_fetcher.fetch_repo_languages).

    Returns:
        A dict with keys:
          - project_type       (str)
          - frameworks         (list[str])
          - main_modules       (list[str])
          - architecture_hint  (str)
          - tech_stack         (list[str])
          - complexity         (dict)
          - architecture_graph (dict)  ← NEW: {nodes, edges}
    """
    name        = metadata.get("name", "") or ""
    description = metadata.get("description", "") or ""
    topics      = metadata.get("topics", []) or []
    size_kb     = metadata.get("size_kb", 0) or 0

    corpus = _build_corpus(name, description, topics)

    project_type      = _detect_project_type(corpus, languages, size_kb)
    frameworks        = _detect_frameworks(corpus)
    main_modules      = _detect_main_modules(corpus, languages)
    architecture_hint = _detect_architecture(corpus, languages, project_type)
    tech_stack        = _detect_tech_stack(corpus, languages, frameworks)
    complexity        = _calculate_complexity(languages, size_kb, main_modules, frameworks, tech_stack)
    architecture_graph = generate_architecture_graph(main_modules, architecture_hint, tech_stack)

    return {
        "project_type":       project_type,
        "frameworks":         frameworks,
        "main_modules":       main_modules,
        "architecture_hint":  architecture_hint,
        "tech_stack":         tech_stack,
        "complexity":         complexity,
        "architecture_graph": architecture_graph,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_corpus(name: str, description: str, topics: list[str]) -> str:
    parts = [name, description] + topics
    combined = " ".join(parts)
    combined = re.sub(r"[-_./]", " ", combined)
    return combined.lower()


def _detect_project_type(corpus: str, languages: Languages, size_kb: int) -> str:
    lang_set = set(languages.keys())

    keyword_type_map: list[tuple[str, str]] = [
        ("cli",          "CLI Tool"),
        ("command line", "CLI Tool"),
        ("bot",          "Bot / Automation"),
        ("plugin",       "Plugin / Extension"),
        ("extension",    "Plugin / Extension"),
        ("library",      "Library / SDK"),
        ("sdk",          "Library / SDK"),
        ("package",      "Library / SDK"),
        ("framework",    "Framework"),
        ("api",          "API Service"),
        ("microservice", "API Service"),
        ("scraper",      "Web Scraper"),
        ("crawler",      "Web Scraper"),
        ("dashboard",    "Dashboard / Admin Panel"),
        ("mobile",       "Mobile App"),
        ("notebook",     "Data Science / Notebook"),
        ("ml",           "ML / AI Project"),
        ("machine learn","ML / AI Project"),
        ("deep learn",   "ML / AI Project"),
        ("data pipeline","Data Pipeline"),
        ("etl",          "Data Pipeline"),
        ("infra",        "DevOps / Infrastructure"),
        ("terraform",    "Infrastructure as Code"),
        ("devops",       "DevOps / Infrastructure"),
    ]
    for kw, label in keyword_type_map:
        if kw in corpus:
            return label

    for required_langs, label in _LANG_TYPE_RULES:
        if required_langs.issubset(lang_set):
            return label

    if lang_set:
        dominant = _dominant_language(languages)
        single_lang_map: dict[str, str] = {
            "Python":     "Python Application",
            "JavaScript": "JavaScript Application",
            "TypeScript": "TypeScript Application",
            "Go":         "Go Application",
            "Rust":       "Rust Application",
            "Java":       "Java Application",
            "Kotlin":     "Kotlin Application",
            "Swift":      "iOS App",
            "Dart":       "Mobile App",
            "Ruby":       "Ruby Application",
            "PHP":        "PHP Application",
            "C":          "Systems / Embedded Software",
            "C++":        "Systems / Embedded Software",
            "Dockerfile": "Container / DevOps Project",
            "Shell":      "Shell Script Collection",
            "HCL":        "Infrastructure as Code",
            "Jupyter Notebook": "Data Science / Notebook",
        }
        if dominant in single_lang_map:
            return single_lang_map[dominant]

    if size_kb < 50:
        return "Script / Utility"

    return "General Software Project"


def _detect_frameworks(corpus: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for keyword, labels in _FRAMEWORK_KEYWORDS.items():
        if keyword in corpus:
            for label in labels:
                if label not in seen:
                    found.append(label)
                    seen.add(label)
    return found


def _detect_main_modules(corpus: str, languages: Languages) -> list[str]:
    modules: list[str] = []
    seen: set[str] = set()

    def _add(label: str) -> None:
        if label not in seen:
            modules.append(label)
            seen.add(label)

    for keyword, label in _MODULE_KEYWORDS.items():
        if keyword in corpus:
            _add(label)

    lang_module_map: dict[str, str] = {
        "HTML":             "Frontend UI",
        "CSS":              "Styling / Theming",
        "JavaScript":       "Frontend / Node.js Logic",
        "TypeScript":       "Typed Frontend / Backend Logic",
        "Python":           "Python Backend",
        "SQL":              "SQL Queries",
        "Dockerfile":       "Containerisation",
        "Shell":            "Shell / Bash Scripts",
        "HCL":              "Terraform IaC",
        "Jupyter Notebook": "Jupyter Notebooks",
        "Go":               "Go Service",
        "Rust":             "Rust Core",
        "Java":             "JVM Service",
    }
    for lang in languages:
        if lang in lang_module_map:
            _add(lang_module_map[lang])

    return modules


def _detect_architecture(corpus: str, languages: Languages, project_type: str) -> str:
    for keywords, hint in _ARCH_RULES:
        if all(kw in corpus for kw in keywords):
            return hint

    lang_set = set(languages.keys())
    has_frontend = bool(lang_set & {"JavaScript", "TypeScript", "HTML", "CSS"})
    has_backend  = bool(lang_set & {"Python", "Go", "Java", "Kotlin", "Rust", "Ruby", "PHP"})

    if has_frontend and has_backend:
        return "Full-Stack Web Application"
    if has_frontend:
        return "Frontend Single-Page Application (SPA)"
    if has_backend:
        return "Backend Service / API"

    pt_arch_map: dict[str, str] = {
        "CLI Tool":                "Single-Binary CLI Tool",
        "Library / SDK":           "Reusable Library / SDK",
        "Data Pipeline":           "Pipeline / ETL Architecture",
        "ML / AI Project":         "ML Training & Inference Pipeline",
        "DevOps / Infrastructure": "Infrastructure as Code",
        "Infrastructure as Code":  "Infrastructure as Code",
        "Data Science / Notebook": "Exploratory Data Analysis",
    }
    if project_type in pt_arch_map:
        return pt_arch_map[project_type]

    return "General / Undetermined Architecture"


def _calculate_complexity(
    languages: Languages,
    size_kb: int,
    main_modules: list[str],
    frameworks: list[str],
    tech_stack: list[str],
) -> dict:
    score = 1
    score += max(len(languages) - 1, 0)

    if size_kb > 1_000:
        score += 2
    elif size_kb > 100:
        score += 1

    if len(main_modules) > 2:
        score += 1
    if frameworks:
        score += 1
    if "Machine Learning" in tech_stack:
        score += 1

    if score <= 3:
        difficulty         = "Beginner"
        estimated_dev_time = "1–2 weeks"
    elif score <= 6:
        difficulty         = "Intermediate"
        estimated_dev_time = "2–4 weeks"
    else:
        difficulty         = "Advanced"
        estimated_dev_time = "1–3 months"

    return {
        "score":              score,
        "difficulty":         difficulty,
        "estimated_dev_time": estimated_dev_time,
    }


def _detect_tech_stack(corpus: str, languages: Languages, frameworks: list[str]) -> list[str]:
    stack: list[str] = []
    seen: set[str]   = set()

    def _add(tag: str) -> None:
        if tag not in seen:
            stack.append(tag)
            seen.add(tag)

    for lang in languages:
        if lang in _DISPLAYABLE_LANGUAGES:
            _add(lang)

    for keyword, tags in _TECH_STACK_RULES:
        if keyword in corpus:
            for tag in tags:
                _add(tag)

    for fw in frameworks:
        _add(fw)

    return stack


def _dominant_language(languages: Languages) -> str:
    if not languages:
        return ""
    return max(languages, key=lambda lang: languages[lang])