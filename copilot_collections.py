"""
Utilities for suggesting GitHub Copilot collections and installing their assets.

The functions here read manifests from the github/awesome-copilot repository,
score them against the current repository context plus recent chat history,
and optionally download the referenced assets (agents, prompts, instructions)
into a local destination folder.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Union

import requests
import yaml

# GitHub sources for awesome-copilot collections
COLLECTIONS_INDEX_URL = (
    "https://api.github.com/repos/github/awesome-copilot/contents/collections"
)
RAW_BASE_URL = "https://raw.githubusercontent.com/github/awesome-copilot/main/"
HTTP_TIMEOUT = 10

# Lightweight extension -> keyword mapping to understand repository context
EXTENSION_KEYWORDS: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".cpp": "c++",
    ".c": "c",
    ".rb": "ruby",
    ".php": "php",
    ".md": "documentation",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
}


@dataclass
class CollectionItem:
    """Single asset referenced by a Copilot collection."""

    path: str
    kind: str
    usage: Optional[str] = None


@dataclass
class CopilotCollection:
    """Represents a Copilot collection manifest."""

    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    items: List[CollectionItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CopilotCollection":
        """Create a collection from a parsed YAML manifest."""
        if not data or "id" not in data or "name" not in data:
            raise ValueError("Invalid collection manifest: missing id or name")

        raw_items = data.get("items", []) or []
        items: List[CollectionItem] = []
        for item in raw_items:
            path = item.get("path")
            if not path:
                continue
            items.append(
                CollectionItem(
                    path=str(path),
                    kind=str(item.get("kind", "instruction")),
                    usage=item.get("usage"),
                )
            )

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            tags=[str(tag).lower() for tag in data.get("tags", []) or []],
            items=items,
        )


def fetch_available_collections(
    session: Optional[requests.Session] = None,
) -> List[CopilotCollection]:
    """
    Fetch all Copilot collections from the awesome-copilot repository.

    Network access is required; callers may pass a preconfigured requests.Session
    (with auth headers or caching) for efficiency.
    """
    sess = session or requests.Session()
    response = sess.get(COLLECTIONS_INDEX_URL, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    entries = response.json()

    collections: List[CopilotCollection] = []
    for entry in entries:
        name = entry.get("name", "")
        download_url = entry.get("download_url")
        if not name.endswith(".collection.yml") or not download_url:
            continue

        manifest_response = sess.get(download_url, timeout=HTTP_TIMEOUT)
        manifest_response.raise_for_status()
        manifest_data = yaml.safe_load(manifest_response.text) or {}

        try:
            collections.append(CopilotCollection.from_dict(manifest_data))
        except ValueError:
            # Skip malformed manifests instead of failing everything
            continue

    return collections


def _gather_repo_keywords(repo_path: Union[str, Path]) -> Set[str]:
    """Infer keywords from the repository contents."""
    keywords: Set[str] = set()
    repo_root = Path(repo_path)

    # Inspect file extensions
    for root, _, files in os.walk(repo_root):
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in EXTENSION_KEYWORDS:
                keywords.add(EXTENSION_KEYWORDS[ext])
        # Keep traversal light by stopping after many entries
        if len(keywords) >= 20:
            break

    # Dependencies from common manifests
    for manifest in ("requirements.txt", "pyproject.toml", "package.json"):
        manifest_path = repo_root / manifest
        if manifest_path.is_file():
            content = manifest_path.read_text(encoding="utf-8", errors="ignore")
            for token in re.findall(r"[A-Za-z0-9\+\#\.-]+", content.lower()):
                if len(token) > 2:
                    keywords.add(token)

    # Project title/description
    readme = repo_root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8", errors="ignore").lower()
        keywords.update(re.findall(r"[a-z0-9\+\#\-]{3,}", text))

    return keywords


def _normalize_tokens(tokens: Iterable[str]) -> Set[str]:
    """Normalize tokens to lowercase and filter out very short words."""
    normalized: Set[str] = set()
    for token in tokens:
        stripped = token.lower().strip()
        if len(stripped) >= 3:
            normalized.add(stripped)
    return normalized


def _score_collection(collection: CopilotCollection, keywords: Set[str]) -> int:
    """Compute a simple relevance score against provided keywords."""
    score = 0
    searchable = f"{collection.name} {collection.description}".lower()
    tag_set = {tag.lower() for tag in collection.tags}

    for keyword in keywords:
        if keyword in tag_set:
            score += 3
        if keyword in searchable:
            score += 1
    return score


def suggest_collections(
    repo_path: Union[str, Path],
    chat_history: str = "",
    collections: Optional[Sequence[CopilotCollection]] = None,
    limit: int = 5,
    session: Optional[requests.Session] = None,
) -> List[CopilotCollection]:
    """
    Suggest relevant Copilot collections based on repository contents and chat history.

    Args:
        repo_path: Path to the repository root for context scanning.
        chat_history: Recent chat transcript to mine for intent keywords.
        collections: Optional pre-fetched collection list (to avoid extra network calls).
        limit: Maximum number of suggestions to return.
        session: Optional requests.Session for fetching collections when not provided.
    """
    keywords = _gather_repo_keywords(repo_path)
    chat_tokens = re.findall(r"[A-Za-z0-9\+\#\-]{3,}", chat_history)
    keywords.update(_normalize_tokens(chat_tokens))

    available = list(collections) if collections is not None else fetch_available_collections(session=session)

    scored: List[tuple[int, CopilotCollection]] = []
    for collection in available:
        score = _score_collection(collection, keywords)
        if score > 0:
            scored.append((score, collection))

    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [collection for _, collection in scored[:limit]]


def _safe_destination(
    destination_root: Union[str, Path],
    collection_id: str,
    relative_path: Union[str, Path],
) -> Path:
    """Ensure downloaded files stay within the destination root."""
    dest_root = Path(destination_root).expanduser().resolve()
    collection_root = (dest_root / collection_id).resolve()
    target = (collection_root / Path(relative_path)).resolve()
    if not str(target).startswith(str(collection_root)):
        raise ValueError("Refusing to write outside destination directory")
    return target


def download_collection_assets(
    collection: CopilotCollection,
    destination_root: Union[str, Path],
    session: Optional[requests.Session] = None,
) -> List[Path]:
    """
    Download all assets for a collection into the destination directory.

    Args:
        collection: Collection manifest to install.
        destination_root: Root folder where assets will be placed.
        session: Optional requests.Session for HTTP reuse.

    Returns:
        List of file paths that were written.
    """
    sess = session or requests.Session()
    saved_paths: List[Path] = []

    for item in collection.items:
        relative_path = Path(item.path.lstrip("/"))
        target_path = _safe_destination(destination_root, collection.id, relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{RAW_BASE_URL}{relative_path.as_posix()}"
        response = sess.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        target_path.write_text(response.text, encoding="utf-8")
        saved_paths.append(target_path)

    return saved_paths


def _format_suggestion(collection: CopilotCollection) -> str:
    """Return a short human-readable summary for CLI output."""
    tag_str = ", ".join(collection.tags) if collection.tags else "no tags"
    return f"- {collection.id}: {collection.name} ({tag_str})"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Simple CLI for suggesting and installing Copilot collections."""
    import argparse

    parser = argparse.ArgumentParser(description="Suggest and install Copilot collections.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository to analyze (default: current directory)",
    )
    parser.add_argument(
        "--chat",
        default="",
        help="Recent chat history or intent to improve relevance",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of suggestions to show",
    )
    parser.add_argument(
        "--install",
        help="Install a specific collection id (downloads assets)",
    )
    parser.add_argument(
        "--dest",
        default="copilot_collections",
        help="Destination folder for downloaded assets",
    )

    args = parser.parse_args(argv)
    session = requests.Session()

    try:
        available = fetch_available_collections(session=session)
    except Exception as exc:
        print(f"Failed to fetch collections: {exc}")
        return 1

    suggestions = suggest_collections(
        repo_path=args.repo,
        chat_history=args.chat,
        collections=available,
        limit=args.limit,
    )

    if suggestions:
        print("Suggested Copilot collections:")
        for collection in suggestions:
            print(_format_suggestion(collection))
    else:
        print("No relevant collections found.")

    if args.install:
        target = next((c for c in available if c.id == args.install), None)
        if not target:
            print(f"Collection '{args.install}' not found.")
            return 1

        try:
            saved = download_collection_assets(target, args.dest, session=session)
            print(f"Installed {len(saved)} assets into {args.dest}")
        except Exception as exc:
            print(f"Failed to install collection '{args.install}': {exc}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
