from unittest.mock import Mock

import pytest

from github_client import RepositoryMetadata
from tools.langchain_tools import create_github_tools


def make_client():
    client = Mock()
    client.get_repo_metadata.return_value = RepositoryMetadata(
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        description="A test repository",
        html_url="https://github.com/octocat/Hello-World",
        stars=10,
        forks=2,
        default_branch="main",
        languages={"Python": 100},
        latest_commit_date="2025-01-02T03:04:05Z",
    )
    return client


def tool_map(tools):
    return {item.name: item for item in tools}


def test_factory_exposes_repository_tools():
    tools = tool_map(create_github_tools(make_client()))

    assert set(tools) == {
        "get_repo_metadata",
        "get_readme",
        "get_folder_structure",
        "read_file",
    }


def test_metadata_tool_returns_serializable_repository_details():
    tools = tool_map(create_github_tools(make_client()))

    result = tools["get_repo_metadata"].invoke({})

    assert result["full_name"] == "octocat/Hello-World"
    assert result["languages"] == {"Python": 100}


def test_folder_structure_filters_irrelevant_files():
    client = make_client()
    client.get_file_tree.return_value = [
        {"path": "src", "type": "tree"},
        {"path": "src/main.py", "type": "blob", "size": 128},
        {"path": "node_modules/pkg/index.js", "type": "blob", "size": 512},
        {"path": "package-lock.json", "type": "blob", "size": 256},
        {"path": "assets/logo.png", "type": "blob", "size": 256},
        {"path": "web/app.min.js", "type": "blob", "size": 1024},
    ]
    tools = tool_map(create_github_tools(client))

    result = tools["get_folder_structure"].invoke({})

    assert [entry["path"] for entry in result["entries"]] == ["src", "src/main.py"]
    assert result["truncated"] is False


def test_read_file_applies_size_limit_and_run_read_budget():
    client = make_client()
    client.get_file_content.return_value = "source text"
    tools = tool_map(create_github_tools(client, max_file_reads=1, max_file_bytes=100))

    result = tools["read_file"].invoke({"path": "src/main.py"})

    assert result == "source text"
    client.get_file_content.assert_called_once_with("src/main.py", max_bytes=100)
    assert "File read limit reached" in tools["read_file"].invoke({"path": "src/other.py"})
    assert client.get_file_content.call_count == 1


def test_read_file_rejects_filtered_paths_without_calling_client():
    client = make_client()
    tools = tool_map(create_github_tools(client))

    result = tools["read_file"].invoke({"path": "node_modules/pkg/index.js"})

    assert "not eligible" in result
    client.get_file_content.assert_not_called()


def test_factory_rejects_invalid_limits():
    client = make_client()

    with pytest.raises(ValueError, match="max_file_reads"):
        create_github_tools(client, max_file_reads=0)
