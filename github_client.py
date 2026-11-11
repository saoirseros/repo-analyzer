"""Read-only access to GitHub repository metadata and contents."""

from __future__ import annotations

import base64
import binascii
import os
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

import requests
from dotenv import load_dotenv

_OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+\Z")
_API_BASE_URL = "https://api.github.com"
_API_VERSION = "2022-11-28"
_DEFAULT_MAX_BYTES = 200_000


class GitHubAPIError(RuntimeError):
    """Raised when a GitHub API request fails or returns unusable data."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RepositoryMetadata:
    """The repository details used by the analyzer."""

    owner: str
    name: str
    full_name: str
    description: str | None
    html_url: str
    stars: int
    forks: int
    default_branch: str
    languages: dict[str, int]
    latest_commit_date: str | None


def parse_repo_url(url: str) -> tuple[str, str]:
    """Validate a GitHub repository URL and return its owner and repository."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Enter a GitHub repository URL.")

    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid GitHub repository URL.") from exc

    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ValueError("URL must use https://github.com.")

    parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
    if len(parts) != 2:
        raise ValueError("URL must point to a repository, such as https://github.com/owner/repo.")

    owner, repository = parts
    if repository.lower().endswith(".git"):
        repository = repository[:-4]

    if (
        not _OWNER_PATTERN.fullmatch(owner)
        or not _REPOSITORY_PATTERN.fullmatch(repository)
        or repository in {".", ".."}
        or len(repository) > 100
    ):
        raise ValueError("The URL contains an invalid owner or repository name.")

    return owner, repository


class GitHubClient:
    """Fetch repository metadata and text files without executing repository code."""

    def __init__(
        self,
        repo_url: str,
        token: str | None = None,
        timeout: float = 15,
        session: requests.Session | None = None,
    ) -> None:
        self.owner, self.repo = parse_repo_url(repo_url)
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        if token is None:
            load_dotenv()
            token = os.getenv("GITHUB_TOKEN")

        self.timeout = timeout
        self._session = session or requests.Session()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
            "User-Agent": "github-repository-analyzer",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        self._repository_data: dict[str, object] | None = None

    def _get_json(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> object:
        try:
            response = self._session.get(
                f"{_API_BASE_URL}/{endpoint}",
                headers=self._headers,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise GitHubAPIError(f"GitHub API request failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {}
            detail = error_data.get("message") if isinstance(error_data, dict) else None
            if not isinstance(detail, str) or not detail:
                detail = response.text.strip()[:500] or "Unknown GitHub API error."
            raise GitHubAPIError(
                f"GitHub API request failed ({response.status_code}): {detail}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError("GitHub API returned invalid JSON.") from exc

    def _get_repository_data(self) -> dict[str, object]:
        if self._repository_data is None:
            data = self._get_json(f"repos/{self.owner}/{self.repo}")
            if not isinstance(data, dict):
                raise GitHubAPIError("GitHub returned an invalid repository response.")
            self._repository_data = data
        return self._repository_data

    @staticmethod
    def _decode_content(data: object, label: str, max_bytes: int) -> str:
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            raise GitHubAPIError(f"GitHub did not return {label} as base64 content.")

        content = data.get("content")
        if not isinstance(content, str):
            raise GitHubAPIError(f"GitHub returned no content for {label}.")

        try:
            decoded = base64.b64decode("".join(content.split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GitHubAPIError(f"GitHub returned invalid base64 content for {label}.") from exc

        return decoded[:max_bytes].decode("utf-8", errors="replace")

    def get_repo_metadata(self) -> RepositoryMetadata:
        """Return basic repository details, language byte counts, and latest commit date."""
        data = self._get_repository_data()
        required_strings = ("full_name", "html_url", "default_branch")
        if any(not isinstance(data.get(field), str) for field in required_strings):
            raise GitHubAPIError("GitHub returned incomplete repository metadata.")

        languages_data = self._get_json(f"repos/{self.owner}/{self.repo}/languages")
        if not isinstance(languages_data, dict) or any(
            not isinstance(name, str) or not isinstance(size, int)
            for name, size in languages_data.items()
        ):
            raise GitHubAPIError("GitHub returned invalid repository language data.")

        commits_data = self._get_json(
            f"repos/{self.owner}/{self.repo}/commits",
            params={"per_page": "1"},
        )
        if not isinstance(commits_data, list):
            raise GitHubAPIError("GitHub returned invalid commit data.")

        latest_commit_date = None
        if commits_data:
            latest = commits_data[0]
            commit = latest.get("commit") if isinstance(latest, dict) else None
            committer = commit.get("committer") if isinstance(commit, dict) else None
            author = commit.get("author") if isinstance(commit, dict) else None
            commit_date = committer.get("date") if isinstance(committer, dict) else None
            if not isinstance(commit_date, str) and isinstance(author, dict):
                commit_date = author.get("date")
            if isinstance(commit_date, str):
                latest_commit_date = commit_date

        description = data.get("description")
        return RepositoryMetadata(
            owner=self.owner,
            name=self.repo,
            full_name=data["full_name"],
            description=description if isinstance(description, str) else None,
            html_url=data["html_url"],
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            default_branch=data["default_branch"],
            languages=languages_data,
            latest_commit_date=latest_commit_date,
        )

    def get_readme(self, max_bytes: int = _DEFAULT_MAX_BYTES) -> str:
        """Fetch and decode the repository README, truncating it to ``max_bytes``."""
        if max_bytes <= 0:
            raise ValueError("max_bytes must be greater than zero.")
        data = self._get_json(f"repos/{self.owner}/{self.repo}/readme")
        return self._decode_content(data, "README", max_bytes)

    def get_file_tree(self) -> list[dict[str, object]]:
        """Return the recursive file tree for the repository's default branch."""
        repository_data = self._get_repository_data()
        branch = repository_data.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise GitHubAPIError("GitHub did not provide a default branch.")

        data = self._get_json(
            f"repos/{self.owner}/{self.repo}/git/trees/{quote(branch, safe='')}",
            params={"recursive": "1"},
        )
        if not isinstance(data, dict) or not isinstance(data.get("tree"), list):
            raise GitHubAPIError("GitHub returned an invalid repository tree.")
        if data.get("truncated") is True:
            raise GitHubAPIError("GitHub truncated the repository tree; a complete listing is unavailable.")
        return data["tree"]

    def get_file_content(self, path: str, max_bytes: int = _DEFAULT_MAX_BYTES) -> str:
        """Fetch a text file from the repository, truncating it to ``max_bytes``."""
        if max_bytes <= 0:
            raise ValueError("max_bytes must be greater than zero.")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
        ):
            raise ValueError("path must be a non-empty repository-relative file path.")

        encoded_path = quote(path, safe="/")
        data = self._get_json(f"repos/{self.owner}/{self.repo}/contents/{encoded_path}")
        return self._decode_content(data, f"file '{path}'", max_bytes)
