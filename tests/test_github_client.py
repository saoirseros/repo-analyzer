import base64
from unittest.mock import Mock

import pytest
import requests

from github_client import GitHubAPIError, GitHubClient, parse_repo_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World.git/", ("octocat", "Hello-World")),
    ],
)
def test_parse_repo_url(url, expected):
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/octocat/Hello-World",
        "http://github.com/octocat/Hello-World",
        "https://github.com/octocat/Hello-World/tree/main",
        "https://github.com/octocat/%2e%2e",
        "https://user@github.com/octocat/Hello-World",
    ],
)
def test_parse_repo_url_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        parse_repo_url(url)


def make_response(payload, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = ""
    return response


def make_client(responses):
    session = Mock()
    session.get.side_effect = responses
    return GitHubClient("https://github.com/octocat/Hello-World", token="", session=session), session


def test_get_repo_metadata_combines_github_endpoints():
    client, session = make_client(
        [
            make_response(
                {
                    "full_name": "octocat/Hello-World",
                    "description": "A test repository",
                    "html_url": "https://github.com/octocat/Hello-World",
                    "stargazers_count": 123,
                    "forks_count": 45,
                    "default_branch": "main",
                }
            ),
            make_response({"Python": 2048, "TypeScript": 1024}),
            make_response(
                [{"commit": {"committer": {"date": "2025-01-02T03:04:05Z"}}}]
            ),
        ]
    )

    metadata = client.get_repo_metadata()

    assert metadata.full_name == "octocat/Hello-World"
    assert metadata.languages == {"Python": 2048, "TypeScript": 1024}
    assert metadata.stars == 123
    assert metadata.forks == 45
    assert metadata.latest_commit_date == "2025-01-02T03:04:05Z"
    assert session.get.call_count == 3


def test_get_readme_decodes_and_truncates_content():
    encoded = base64.b64encode(b"README contents").decode("ascii")
    client, _ = make_client([make_response({"encoding": "base64", "content": encoded})])

    assert client.get_readme(max_bytes=6) == "README"


def test_get_file_tree_uses_default_branch_and_recursive_option():
    client, session = make_client(
        [
            make_response({"default_branch": "main"}),
            make_response({"tree": [{"path": "src/main.py", "type": "blob"}], "truncated": False}),
        ]
    )

    assert client.get_file_tree() == [{"path": "src/main.py", "type": "blob"}]
    assert session.get.call_args.kwargs["params"] == {"recursive": "1"}


def test_get_file_content_rejects_parent_path_before_requesting():
    client, session = make_client([])

    with pytest.raises(ValueError, match="repository-relative"):
        client.get_file_content("../secrets.txt")

    session.get.assert_not_called()


def test_http_errors_include_status_and_github_message():
    client, _ = make_client([make_response({"message": "Not Found"}, status_code=404)])

    with pytest.raises(GitHubAPIError, match="404.*Not Found") as error:
        client.get_readme()

    assert error.value.status_code == 404


def test_request_errors_are_reported():
    client, _ = make_client([requests.Timeout("timed out")])

    with pytest.raises(GitHubAPIError, match="GitHub API request failed"):
        client.get_readme()
