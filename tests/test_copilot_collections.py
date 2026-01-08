import pytest

import copilot_collections as cc


def test_from_dict_parses_manifest():
    manifest = {
        "id": "python-tools",
        "name": "Python Tools",
        "description": "Great helpers for Python developers",
        "tags": ["python", "devops"],
        "items": [
            {"path": "prompts/task.prompt.md", "kind": "prompt"},
            {"path": "instructions/workflow.md", "kind": "instruction"},
        ],
    }

    collection = cc.CopilotCollection.from_dict(manifest)

    assert collection.id == "python-tools"
    assert collection.tags == ["python", "devops"]
    assert len(collection.items) == 2
    assert collection.items[0].path == "prompts/task.prompt.md"


def test_suggest_collections_prefers_matching_tags(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hi')", encoding="utf-8")
    (repo / "README.md").write_text("Cloud automation helper", encoding="utf-8")
    (repo / "requirements.txt").write_text("fastapi==0.1", encoding="utf-8")

    matching = cc.CopilotCollection(
        id="python-cli",
        name="Python CLI Helpers",
        description="Tools for automation and CLI work",
        tags=["python", "cli", "automation"],
        items=[],
    )
    non_matching = cc.CopilotCollection(
        id="java-web",
        name="Java Web",
        description="Java only content",
        tags=["java", "spring"],
        items=[],
    )

    suggestions = cc.suggest_collections(
        repo_path=repo,
        chat_history="Looking for automation helpers",
        collections=[matching, non_matching],
        limit=3,
    )

    assert [s.id for s in suggestions] == ["python-cli"]


class _StubResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _StubSession:
    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, url, timeout):
        if url not in self._mapping:
            raise AssertionError(f"Unexpected URL requested: {url}")
        return _StubResponse(self._mapping[url])


def test_download_collection_assets_writes_files(tmp_path):
    collection = cc.CopilotCollection(
        id="python-cli",
        name="Python CLI Helpers",
        description="Tools for automation and CLI work",
        tags=["python", "cli", "automation"],
        items=[
            cc.CollectionItem(path="prompts/task.prompt.md", kind="prompt"),
            cc.CollectionItem(path="instructions/workflow.md", kind="instruction"),
        ],
    )

    mapping = {
        f"{cc.RAW_BASE_URL}prompts/task.prompt.md": "prompt content",
        f"{cc.RAW_BASE_URL}instructions/workflow.md": "workflow content",
    }
    session = _StubSession(mapping)

    saved_paths = cc.download_collection_assets(collection, tmp_path, session=session)

    assert len(saved_paths) == 2
    assert (tmp_path / "python-cli" / "prompts" / "task.prompt.md").read_text() == "prompt content"
    assert (tmp_path / "python-cli" / "instructions" / "workflow.md").read_text() == "workflow content"


def test_download_collection_assets_blocks_traversal(tmp_path):
    collection = cc.CopilotCollection(
        id="python-cli",
        name="Python CLI Helpers",
        description="Tools for automation and CLI work",
        tags=["python", "cli", "automation"],
        items=[cc.CollectionItem(path="../escape.txt", kind="prompt")],
    )

    with pytest.raises(ValueError):
        cc.download_collection_assets(collection, tmp_path, session=_StubSession({}))
