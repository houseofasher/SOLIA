"""Push learning exports to GitHub repos via the Contents API (Railway-safe)."""

from __future__ import annotations

import base64
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any

import requests

from app.learning_export import build_export_files

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_REPOS = "ZorakCorp/Aureon-LLM,shep95/Aureon_Elion-LLM"
DEFAULT_BRANCH = "learning-data"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def github_token() -> str:
    return (
        os.environ.get("AUREON_GITHUB_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip()
        or os.environ.get("GH_TOKEN", "").strip()
    )


def github_repos() -> list[str]:
    raw = os.environ.get("AUREON_GITHUB_REPOS", DEFAULT_REPOS).strip()
    return [part.strip() for part in raw.split(",") if part.strip()]


def is_github_sync_enabled() -> bool:
    return _env_bool("AUREON_GITHUB_SYNC", default=False) and bool(github_token())


@dataclass
class GitHubSyncConfig:
    enabled: bool = False
    repos: list[str] = field(default_factory=list)
    branch: str = DEFAULT_BRANCH
    on_cycle: bool = True

    @classmethod
    def from_env(cls) -> GitHubSyncConfig:
        return cls(
            enabled=is_github_sync_enabled(),
            repos=github_repos(),
            branch=os.environ.get("AUREON_GITHUB_SYNC_BRANCH", DEFAULT_BRANCH).strip()
            or DEFAULT_BRANCH,
            on_cycle=_env_bool("AUREON_GITHUB_SYNC_ON_CYCLE", default=True),
        )


@dataclass
class GitHubSyncState:
    last_sync_at: str | None = None
    last_error: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)
    syncing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": is_github_sync_enabled(),
            "config": GitHubSyncConfig.from_env().__dict__,
            "last_sync_at": self.last_sync_at,
            "last_error": self.last_error,
            "last_result": self.last_result,
            "syncing": self.syncing,
        }


_state = GitHubSyncState()
_lock = threading.Lock()


def get_github_sync_state() -> GitHubSyncState:
    with _lock:
        return _state


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _default_branch(owner: str, repo: str, token: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    response = requests.get(url, headers=_headers(token), timeout=30)
    response.raise_for_status()
    return response.json().get("default_branch", "main")


def _ensure_branch(owner: str, repo: str, branch: str, token: str) -> None:
    ref_url = f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{branch}"
    response = requests.get(ref_url, headers=_headers(token), timeout=30)
    if response.status_code == 200:
        return
    if response.status_code != 404:
        response.raise_for_status()

    base = _default_branch(owner, repo, token)
    base_ref = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{base}",
        headers=_headers(token),
        timeout=30,
    )
    base_ref.raise_for_status()
    sha = base_ref.json()["object"]["sha"]

    create = requests.post(
        f"{GITHUB_API}/repos/{owner}/{repo}/git/refs",
        headers=_headers(token),
        json={"ref": f"refs/heads/{branch}", "sha": sha},
        timeout=30,
    )
    if create.status_code not in (201, 422):
        create.raise_for_status()


def _upsert_file(
    owner: str,
    repo: str,
    branch: str,
    path: str,
    content: bytes,
    message: str,
    token: str,
) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    headers = _headers(token)
    existing = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": branch,
    }
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]
    elif existing.status_code != 404:
        existing.raise_for_status()

    put = requests.put(url, headers=headers, json=payload, timeout=90)
    put.raise_for_status()


def sync_repo(owner: str, repo: str, *, branch: str, token: str, files: dict[str, bytes]) -> dict[str, Any]:
    _ensure_branch(owner, repo, branch, token)
    uploaded: list[str] = []
    for path, content in files.items():
        _upsert_file(
            owner,
            repo,
            branch,
            path,
            content,
            f"chore(learning): sync Aureon corpus — {path}",
            token,
        )
        uploaded.append(path)
    return {
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "files_uploaded": len(uploaded),
        "paths": uploaded,
        "view_url": f"https://github.com/{owner}/{repo}/tree/{branch}/learning-corpus",
    }


def run_github_sync(*, reason: str = "manual") -> dict[str, Any]:
    """Export learning data and push to all configured GitHub repos."""
    from datetime import datetime, timezone

    from app.activity_log import log_ai_activity

    config = GitHubSyncConfig.from_env()
    token = github_token()
    if not config.enabled or not token:
        return {"ok": False, "error": "GitHub sync disabled or token missing"}

    with _lock:
        if _state.syncing:
            return {"ok": False, "error": "sync already in progress"}
        _state.syncing = True
        _state.last_error = None

    try:
        files = build_export_files()
        results: list[dict[str, Any]] = []
        for spec in config.repos:
            if "/" not in spec:
                continue
            owner, repo = spec.split("/", 1)
            results.append(sync_repo(owner, repo.strip(), branch=config.branch, token=token, files=files))

        payload = {
            "ok": True,
            "reason": reason,
            "repos": results,
            "file_count": len(files),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        with _lock:
            _state.last_sync_at = payload["synced_at"]
            _state.last_result = payload
        log_ai_activity("github_learning_sync_complete", **payload)
        logger.info("GitHub learning sync complete: %s", payload)
        return payload
    except Exception as exc:
        err = str(exc)[:500]
        with _lock:
            _state.last_error = err
        log_ai_activity("github_learning_sync_failed", error=err, reason=reason)
        logger.exception("GitHub learning sync failed")
        return {"ok": False, "error": err}
    finally:
        with _lock:
            _state.syncing = False


def run_github_sync_background(*, reason: str = "auto_learn_cycle") -> None:
    if not is_github_sync_enabled():
        return
    if not GitHubSyncConfig.from_env().on_cycle:
        return

    def _job() -> None:
        run_github_sync(reason=reason)

    threading.Thread(target=_job, name="aureon-github-sync", daemon=True).start()
