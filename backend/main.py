"""
main.py
-------
RepoLens AI — FastAPI entry point.

Endpoints:
  GET    /                      — Health check
  GET    /repos                 — List all repositories in memory
  DELETE /repos/{repo_name}     — Remove a repository from memory
  GET    /analyse               — Full repository analysis (stores in memory)
  POST   /agent/query           — AI agent router (single repo)
  POST   /agent/compare         — AI agent cross-repository comparison

Run locally with:
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from github_fetcher import (
    parse_github_url,
    fetch_repo_metadata,
    fetch_repo_languages,
    fetch_repo_readme,
    fetch_repo_structure,
)
from repo_parser import analyse_repo
from ai_engine import (
    generate_readme_analysis,
    generate_ai_summary,
    generate_architecture_analysis,
    generate_code_review,
    generate_repo_documentation,
)
from agent_router import detect_intent, route_tool, compare_repositories


# ---------------------------------------------------------------------------
# Global repository memory
# ---------------------------------------------------------------------------

repo_memory: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RepoLens AI",
    description=(
        "Analyse public GitHub repositories, store them in memory, "
        "and interact with a unified AI agent that can answer questions "
        "about individual repos or compare selected repositories."
    ),
    version="12.0.0",
)


# ---------------------------------------------------------------------------
# CORS — keep untouched
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas — /analyse
# ---------------------------------------------------------------------------

class ComplexityModel(BaseModel):
    score: int
    difficulty: str
    estimated_dev_time: str


class InsightsModel(BaseModel):
    project_type: str
    frameworks: list[str]
    main_modules: list[str]
    architecture_hint: str
    tech_stack: list[str]
    complexity: ComplexityModel
    architecture_graph: dict


class ReadmeAnalysisModel(BaseModel):
    purpose: str
    key_features: list[str]
    setup: str


class ArchitectureModel(BaseModel):
    layers: list[str]
    structure: list[str]
    explanation: str


class CodeReviewModel(BaseModel):
    quality_score: int
    security_risks: list[str]
    performance_notes: list[str]
    best_practices: list[str]


class RepoDocumentationModel(BaseModel):
    project_overview: str
    tech_stack: list[str]
    architecture_summary: str
    installation_steps: list[str]
    usage_guide: list[str]


class RepoAnalysisResponse(BaseModel):
    owner: str
    repo: str
    metadata: dict
    languages: dict
    insights: InsightsModel
    summary: str
    readme_analysis: ReadmeAnalysisModel
    architecture: ArchitectureModel
    code_review: CodeReviewModel
    documentation: RepoDocumentationModel


# ---------------------------------------------------------------------------
# Pydantic schemas — /agent/query
# ---------------------------------------------------------------------------

class AgentQueryRequest(BaseModel):
    """Request body for the unified AI agent router (single repo)."""
    question: str
    repo_data: dict


class AgentQueryResponse(BaseModel):
    """Structured response from the unified AI agent router."""
    tool_used: str
    tool_label: str
    answer: str


# ---------------------------------------------------------------------------
# Pydantic schemas — /agent/compare
# ---------------------------------------------------------------------------

class AgentCompareRequest(BaseModel):
    """
    Request body for cross-repository comparison.

    Fields:
        question      — The comparison question.
        selected_repos — Optional list of repo keys to compare.
                         If omitted or empty, all repos in memory are compared.
    """
    question: str
    selected_repos: list[str] = []


class AgentCompareResponse(BaseModel):
    """Response from the cross-repository comparison agent."""
    repos_compared: list[str]
    answer: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    return {
        "status": "ok",
        "service": "RepoLens AI",
        "version": "12.0.0",
        "repos_in_memory": len(repo_memory),
    }


@app.get(
    "/repos",
    summary="List repositories in memory",
    response_description="List of full_name keys stored in repo_memory",
)
def list_repos() -> list[str]:
    """Return the names of all repositories currently in the in-memory store."""
    return list(repo_memory.keys())


@app.delete(
    "/repos/{repo_name:path}",
    summary="Remove a repository from memory",
    status_code=200,
)
def delete_repo(repo_name: str):
    """
    Remove a single repository from the in-memory store by its full name
    (e.g. ``owner/repo``).  Returns 404 if the key is not found.

    The ``{repo_name:path}`` path parameter type allows forward-slashes in
    the key so that ``owner/repo`` works as a URL segment.
    """
    if repo_name not in repo_memory:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_name}' is not in memory.",
        )
    del repo_memory[repo_name]
    return {"deleted": repo_name, "repos_in_memory": len(repo_memory)}


@app.get(
    "/analyse",
    response_model=RepoAnalysisResponse,
    summary="Analyse a GitHub repository",
)
def analyse_repository(
    url: str = Query(
        ...,
        description="Full GitHub repository URL, e.g. https://github.com/owner/repo",
        example="https://github.com/tiangolo/fastapi",
    ),
    token: str = Query(
        default=None,
        description="Optional GitHub personal access token (raises rate limit to 5 000 req/hour).",
    ),
):
    """Full repository analysis — metadata, languages, insights, summary, README,
    architecture, code review, and AI-generated documentation.

    The result is automatically stored in ``repo_memory`` so the AI agent can
    answer questions about it and compare it with other repos.
    """

    try:
        owner, repo = parse_github_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        metadata  = fetch_repo_metadata(owner, repo, token=token)
        languages = fetch_repo_languages(owner, repo, token=token)
        readme    = fetch_repo_readme(owner, repo, token=token)
        structure = fetch_repo_structure(owner, repo, token=token)
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 404:
            raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found or is private.")
        if status_code == 403:
            raise HTTPException(status_code=429, detail="GitHub API rate limit reached. Supply a token.")
        raise HTTPException(status_code=502, detail=f"GitHub API error ({status_code}): {exc}")
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach GitHub API: {exc}")

    try:
        insights = analyse_repo(metadata, languages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {exc}")

    try:
        summary = generate_ai_summary(metadata, insights)
        if not isinstance(summary, str) or not summary.strip():
            summary = "Summary not available."
    except Exception:
        summary = "Summary not available."

    try:
        readme_analysis = generate_readme_analysis(readme)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"README analysis failed: {exc}")

    try:
        architecture = generate_architecture_analysis(structure, insights)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Architecture analysis failed: {exc}")

    try:
        code_review = generate_code_review(metadata, languages, insights, structure)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Code review generation failed: {exc}")

    try:
        documentation = generate_repo_documentation(metadata, insights, readme_analysis, architecture)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Documentation generation failed: {exc}")

    response = RepoAnalysisResponse(
        owner=owner,
        repo=repo,
        metadata=metadata,
        languages=languages,
        insights=InsightsModel(
            **{k: v for k, v in insights.items() if k not in ("complexity", "architecture_graph")},
            complexity=ComplexityModel(**insights["complexity"]),
            architecture_graph=insights.get("architecture_graph", {"nodes": [], "edges": []}),
        ),
        summary=summary,
        readme_analysis=ReadmeAnalysisModel(**readme_analysis),
        architecture=ArchitectureModel(**architecture),
        code_review=CodeReviewModel(**code_review),
        documentation=RepoDocumentationModel(**documentation),
    )

    # Store in global memory
    repo_key = metadata.get("full_name") or f"{owner}/{repo}"
    repo_memory[repo_key] = response.model_dump()

    return response


@app.post(
    "/agent/query",
    response_model=AgentQueryResponse,
    summary="Unified AI Agent — single repository",
)
def agent_query(body: AgentQueryRequest):
    """Answer any question about a single repository using the RepoLens AI Agent."""
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")
    if not body.repo_data:
        raise HTTPException(status_code=400, detail="repo_data must not be empty.")

    try:
        intent = detect_intent(body.question)
        result = route_tool(intent, body.repo_data, body.question)
        return AgentQueryResponse(
            tool_used=result["tool_used"],
            tool_label=result["tool_label"],
            answer=result["answer"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent router error: {exc}")


@app.post(
    "/agent/compare",
    response_model=AgentCompareResponse,
    summary="Unified AI Agent — compare selected repositories",
)
def agent_compare(body: AgentCompareRequest):
    """
    Answer a cross-repository comparison question.

    If ``selected_repos`` is provided and non-empty, only those repositories
    are compared.  Otherwise all repositories in ``repo_memory`` are used.

    Requires at least two repositories to be available for comparison.
    """
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")

    # Resolve which repos to compare
    if body.selected_repos:
        # Validate that all requested keys exist in memory
        missing = [r for r in body.selected_repos if r not in repo_memory]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"These repositories are not in memory: {', '.join(missing)}",
            )
        target_memory = {k: repo_memory[k] for k in body.selected_repos}
    else:
        target_memory = repo_memory

    if len(target_memory) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"At least 2 repositories are required for comparison. "
                f"Currently available: {len(target_memory)}."
            ),
        )

    try:
        answer = compare_repositories(target_memory, body.question)
        return AgentCompareResponse(
            repos_compared=list(target_memory.keys()),
            answer=answer,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison error: {exc}")