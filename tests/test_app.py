from pathlib import Path
from unittest.mock import patch

import dotenv
import pytest
from langgraph.errors import GraphRecursionError
from langchain_google_genai.chat_models import GoogleAuthenticationError
from streamlit.testing.v1 import AppTest

from agent.schemas import RepositoryAnalysisReport

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(autouse=True)
def prevent_dotenv_loading(monkeypatch):
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)


def run_app():
    return AppTest.from_file(APP_PATH, default_timeout=20).run()


def test_app_renders_repository_input_and_analysis_settings():
    app = run_app()
    assert not app.exception
    assert app.text_input[0].label == "GitHub repository URL"
    assert app.text_input[1].label == "Gemini model"
    assert app.button[0].label == "Analyze repository"


def test_app_shows_validation_error_for_invalid_repository_url():
    app = run_app()
    app.text_input[0].set_value("https://example.com/not-a-repository")
    app.form_submit_button[0].click().run()

    assert any("URL must use https://github.com" in error.value for error in app.error)


def test_app_requires_google_key_before_running_analysis(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = run_app()
    app.text_input[0].set_value("https://github.com/octocat/Hello-World")
    app.form_submit_button[0].click().run()

    assert any("Set GOOGLE_API_KEY" in error.value for error in app.error)


def test_app_rejects_placeholder_google_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "your_api_key_here")
    app = run_app()
    app.text_input[0].set_value("https://github.com/octocat/Hello-World")
    app.form_submit_button[0].click().run()

    assert any("Replace the example placeholder value" in error.value for error in app.error)


def test_app_shows_actionable_message_when_google_rejects_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "invalid-key")
    error = GoogleAuthenticationError("Invalid API key")
    with patch("agent.runner.analyze_repository", side_effect=error):
        app = run_app()
        app.text_input[0].set_value("https://github.com/octocat/Hello-World")
        app.form_submit_button[0].click().run()

    assert any("Google rejected the configured API key" in item.value for item in app.error)


def test_app_suggests_reducing_file_limit_after_recursion_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with patch(
        "agent.runner.analyze_repository",
        side_effect=GraphRecursionError("recursion limit reached"),
    ):
        app = run_app()
        app.text_input[0].set_value("https://github.com/octocat/Hello-World")
        app.form_submit_button[0].click().run()

    assert any("smaller source-file limit" in item.value for item in app.error)


def test_app_renders_analysis_report(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    report = RepositoryAnalysisReport(
        repository_url="https://github.com/octocat/Hello-World",
        summary="A small test project.",
        architecture_overview="One application component.",
        data_flow="The entry point calls the application.",
        tech_stack=["Python"],
        limitations=[],
    )
    with patch("agent.runner.analyze_repository", return_value=report):
        app = run_app()
        app.text_input[0].set_value("https://github.com/octocat/Hello-World")
        app.form_submit_button[0].click().run()

    assert any("A small test project." in item.value for item in app.subheader)
    assert any(tab.label == "Architecture" for tab in app.tabs)
    assert not app.exception
