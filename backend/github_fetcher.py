"""
github_fetcher.py
-----------------
Handles all GitHub API interactions for RepoLens AI.
Responsible for:
  - Parsing GitHub repository URLs
  - Fetching repository metadata
  - Fetching programming languages used in a repository
  - Fetching and decoding the repository README
  - Fetching the top-level repository file/folder structure
"""

import base64
import re
import requests
from typing import Optional

# Base URL for the GitHub REST API
GITHUB_API_BASE = "https://api.github.com"


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract the owner and repository name from a GitHub URL.

    Supports formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - http://github.com/owner/repo

    Args:
        url: The full GitHub repository URL.

    Returns:
        A tuple of (owner, repo_name).

    Raises:
        ValueError: If the URL does not match a valid GitHub repository pattern.
    """
    pattern = r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$"
    match = re.match(pattern, url.strip())

    if not match:
        raise ValueError(
            f"Invalid GitHub URL: '{url}'. "
            "Expected format: https://github.com/owner/repo"
        )

    owner = match.group(1)
    repo = match.group(2)
    return owner, repo


def fetch_repo_metadata(
    owner: str,
    repo: str,
    token: Optional[str] = None
) -> dict:
    """
    Fetch repository metadata from the GitHub API.

    Retrieves details such as description, stars, forks, open issues,
    default branch, license, and timestamps.

    Args:
        owner: The GitHub username or organisation name.
        repo:  The repository name.
        token: Optional GitHub personal access token for authenticated requests
               (higher rate limits).

    Returns:
        A dictionary containing repository metadata fields.

    Raises:
        requests.HTTPError: If the GitHub API returns a non-2xx status code.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    headers = _build_headers(token)

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    raw = response.json()

    # Return a clean, focused subset of the full API response
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "full_name": raw.get("full_name"),
        "description": raw.get("description"),
        "url": raw.get("html_url"),
        "homepage": raw.get("homepage"),
        "visibility": raw.get("visibility"),
        "default_branch": raw.get("default_branch"),
        "stars": raw.get("stargazers_count"),
        "watchers": raw.get("watchers_count"),
        "forks": raw.get("forks_count"),
        "open_issues": raw.get("open_issues_count"),
        "license": raw.get("license", {}).get("name") if raw.get("license") else None,
        "topics": raw.get("topics", []),
        "is_fork": raw.get("fork"),
        "is_archived": raw.get("archived"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "pushed_at": raw.get("pushed_at"),
        "size_kb": raw.get("size"),
    }


def fetch_repo_languages(
    owner: str,
    repo: str,
    token: Optional[str] = None
) -> dict:
    """
    Fetch the programming languages breakdown for a repository.

    GitHub returns language names mapped to the number of bytes of code
    written in that language.

    Args:
        owner: The GitHub username or organisation name.
        repo:  The repository name.
        token: Optional GitHub personal access token.

    Returns:
        A dictionary mapping language names to byte counts,
        e.g. {"Python": 14321, "Shell": 512}.

    Raises:
        requests.HTTPError: If the GitHub API returns a non-2xx status code.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
    headers = _build_headers(token)

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def fetch_repo_readme(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> str:
    """
    Fetch and decode the default README file for a repository.

    GitHub returns README content as a base64-encoded string.  This function
    decodes it and returns the raw text so callers never have to deal with
    the encoding themselves.

    The API automatically resolves the default branch and the most common
    README filenames (README.md, README.rst, README.txt, README, etc.).

    Args:
        owner: The GitHub username or organisation name.
        repo:  The repository name.
        token: Optional GitHub personal access token.

    Returns:
        The decoded plain-text README content, or an empty string if the
        repository has no README (HTTP 404 is handled gracefully).

    Raises:
        requests.HTTPError: For non-404 HTTP errors from the GitHub API.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    headers = _build_headers(token)

    response = requests.get(url, headers=headers, timeout=10)

    # A missing README is not an error — treat it as empty content.
    if response.status_code == 404:
        return ""

    response.raise_for_status()

    raw = response.json()

    # GitHub always returns the content as base64; encoding field confirms it.
    encoded_content = raw.get("content", "")
    if not encoded_content:
        return ""

    # base64 content may contain line-break characters — strip them first.
    decoded_bytes = base64.b64decode(encoded_content.replace("\n", ""))
    return decoded_bytes.decode("utf-8", errors="replace")


def fetch_repo_structure(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> list[str]:
    """
    Fetch the top-level file and folder names of a repository.

    Uses the GitHub Contents API to list all entries at the root of the
    default branch.  Only the ``name`` of each entry is returned — the
    caller receives a flat list of strings suitable for pattern-matching.

    Args:
        owner: The GitHub username or organisation name.
        repo:  The repository name.
        token: Optional GitHub personal access token.

    Returns:
        A sorted list of top-level entry names, e.g.:
            ["README.md", "backend", "frontend", "tests"]
        Returns an empty list if the contents endpoint is unavailable or
        the repository is empty (HTTP 404 / 409 handled gracefully).

    Raises:
        requests.HTTPError: For non-404/409 HTTP errors from the GitHub API.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
    headers = _build_headers(token)

    response = requests.get(url, headers=headers, timeout=10)

    # 404 = repo not found or no default branch yet; 409 = empty repository.
    # Both are treated as "no structure available" rather than hard errors.
    if response.status_code in (404, 409):
        return []

    response.raise_for_status()

    entries = response.json()

    # The API returns a list of content objects; each has a "name" key.
    if not isinstance(entries, list):
        return []

    return sorted(entry["name"] for entry in entries if "name" in entry)


def _build_headers(token: Optional[str]) -> dict:
    """
    Construct HTTP headers for GitHub API requests.

    Args:
        token: Optional personal access token.

    Returns:
        A headers dictionary with Accept and, if provided, Authorization fields.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers