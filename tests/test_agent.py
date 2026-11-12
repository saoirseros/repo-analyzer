from unittest.mock import Mock

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

import agent.runner as runner
from agent.schemas import (
    ArchitectureComponent,
    CodeQualityIssue,
    ImprovementSuggestion,
    RepositoryAnalysisReport,
)


def make_report():
    return RepositoryAnalysisReport(
        repository_url="https://github.com/octocat/Hello-World",
        summary="A small example repository.",
        architecture_overview="The inspected source contains one application module.",
        components=[
            ArchitectureComponent(
                name="Application",
                description="Implements the main application behavior.",
                files=["src/main.py"],
            )
        ],
        data_flow="The entry point calls the application module.",
        tech_stack=["Python"],
        code_quality_issues=[
            CodeQualityIssue(
                title="Missing input validation",
                severity="medium",
                description="The inspected function accepts unchecked user input.",
                evidence="The function passes its argument directly to the parser.",
                files=["src/main.py"],
            )
        ],
        improvements=[
            ImprovementSuggestion(
                title="Validate input",
                priority="medium",
                rationale="Validation can reject malformed input before parsing.",
                suggested_action="Add validation at the public function boundary.",
                files=["src/main.py"],
            )
        ],
        limitations=["Only one source file was inspected."],
    )


def test_report_schema_accepts_expected_structured_output():
    report = make_report()

    assert report.code_quality_issues[0].severity == "medium"
    assert report.improvements[0].files == ["src/main.py"]


def test_report_schema_rejects_unknown_severity():
    with pytest.raises(ValueError):
        CodeQualityIssue(
            title="Issue",
            severity="critical",
            description="Invalid severity.",
            evidence="No evidence.",
        )


def test_agent_factory_builds_langgraph_agent_without_api_request():
    agent = runner.create_repository_analysis_agent(
        client=Mock(),
        model=ChatGoogleGenerativeAI(
            model=runner.DEFAULT_MODEL,
            api_key="test-key",
        ),
    )

    assert {"model", "tools"} <= set(agent.nodes)


def test_agent_uses_google_api_key_and_free_tier_default_model(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setattr(runner, "load_dotenv", lambda: None)
    monkeypatch.setattr(runner, "create_agent", lambda **kwargs: kwargs)
    model_factory = Mock(return_value=Mock())
    monkeypatch.setattr(runner, "ChatGoogleGenerativeAI", model_factory)

    configuration = runner.create_repository_analysis_agent(client=Mock())

    assert configuration["model"] is model_factory.return_value
    assert model_factory.call_args.kwargs == {
        "model": "gemini-3.1-flash-lite",
        "api_key": "test-google-key",
        "temperature": 0,
    }


def test_agent_requires_api_key_when_model_is_not_injected(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(runner, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        runner.create_repository_analysis_agent(client=Mock())


def test_analyze_repository_returns_validated_structured_response(monkeypatch):
    report = make_report()
    fake_agent = Mock()
    fake_agent.invoke.return_value = {"structured_response": report.model_dump()}
    monkeypatch.setattr(runner, "GitHubClient", lambda url: Mock())
    monkeypatch.setattr(runner, "create_repository_analysis_agent", lambda **kwargs: fake_agent)

    result = runner.analyze_repository("https://github.com/octocat/Hello-World", recursion_limit=20)

    assert result == report
    assert fake_agent.invoke.call_args.kwargs["config"] == {"recursion_limit": 20}


def test_analyze_repository_fails_if_structured_response_is_missing(monkeypatch):
    fake_agent = Mock()
    fake_agent.invoke.return_value = {}
    monkeypatch.setattr(runner, "GitHubClient", lambda url: Mock())
    monkeypatch.setattr(runner, "create_repository_analysis_agent", lambda **kwargs: fake_agent)

    with pytest.raises(RuntimeError, match="did not return a structured report"):
        runner.analyze_repository("https://github.com/octocat/Hello-World")


def test_analyze_repository_rejects_invalid_recursion_limit():
    with pytest.raises(ValueError, match="recursion_limit"):
        runner.analyze_repository("https://github.com/octocat/Hello-World", recursion_limit=0)
