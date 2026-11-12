"""Streamlit interface for the GitHub Repository Analyzer."""

import json
import os

import streamlit as st
from dotenv import load_dotenv
from langgraph.errors import GraphRecursionError
from langchain_google_genai.chat_models import GoogleAuthenticationError, GoogleGenerativeAIError

from agent.runner import DEFAULT_MODEL, analyze_repository
from agent.schemas import RepositoryAnalysisReport
from github_client import GitHubAPIError, parse_repo_url
from tools.langchain_tools import DEFAULT_MAX_FILE_READS

load_dotenv()

st.set_page_config(
    page_title="GitHub Repository Analyzer",
    page_icon="🔎",
    layout="wide",
)


def _show_file_references(files: list[str]) -> None:
    if files:
        st.caption("Evidence files: " + ", ".join(f"`{path}`" for path in files))


def _show_report(report: RepositoryAnalysisReport) -> None:
    st.subheader(report.summary)
    st.caption(report.repository_url)

    overview_tab, architecture_tab, quality_tab, improvements_tab = st.tabs(
        ["Overview", "Architecture", "Code quality", "Improvements"]
    )

    with overview_tab:
        st.markdown("#### Architecture overview")
        st.write(report.architecture_overview)
        st.markdown("#### Technology identified")
        if report.tech_stack:
            st.write(", ".join(report.tech_stack))
        else:
            st.info("The analyzed files did not identify a technology stack.")
        if report.limitations:
            st.markdown("#### Analysis limitations")
            for limitation in report.limitations:
                st.write(f"- {limitation}")

    with architecture_tab:
        st.markdown("#### Components")
        if report.components:
            for component in report.components:
                with st.expander(component.name):
                    st.write(component.description)
                    _show_file_references(component.files)
        else:
            st.info("No components were identified from the available evidence.")
        st.markdown("#### Data flow")
        st.write(report.data_flow)

    with quality_tab:
        if report.code_quality_issues:
            for issue in report.code_quality_issues:
                with st.expander(f"{issue.severity.title()}: {issue.title}"):
                    st.write(issue.description)
                    st.markdown("**Evidence**")
                    st.write(issue.evidence)
                    _show_file_references(issue.files)
        else:
            st.success("No evidence-backed code quality issues were identified.")

    with improvements_tab:
        if report.improvements:
            for suggestion in report.improvements:
                with st.expander(f"{suggestion.priority.title()}: {suggestion.title}"):
                    st.markdown("**Suggested action**")
                    st.write(suggestion.suggested_action)
                    st.markdown("**Why it may help**")
                    st.write(suggestion.rationale)
                    _show_file_references(suggestion.files)
        else:
            st.info("No improvements were suggested from the available evidence.")

    st.download_button(
        "Download report (JSON)",
        data=json.dumps(report.model_dump(mode="json"), indent=2),
        file_name="repository-analysis.json",
        mime="application/json",
    )


st.title("GitHub Repository Analyzer")
st.write(
    "Explore a repository's structure and selected source files, then review an "
    "AI-generated architecture summary, code quality findings, and suggestions."
)
st.info(
    "Repository files are sent to Google's Gemini API for analysis. The free tier may use "
    "submitted content to improve Google products; do not analyze private or confidential code."
)

with st.sidebar:
    st.header("Analysis settings")
    model_name = st.text_input(
        "Gemini model",
        value=os.getenv("GOOGLE_MODEL") or DEFAULT_MODEL,
        help="Model used to inspect the repository and generate the report.",
    )
    max_file_reads = st.slider(
        "Maximum source files to read",
        min_value=1,
        max_value=DEFAULT_MAX_FILE_READS,
        value=DEFAULT_MAX_FILE_READS,
        help="Limits the number of source files the agent can inspect per analysis.",
    )
    st.caption("Each file is limited to 200 KB. Repository code is never executed.")

with st.form("repository-analysis"):
    repo_url = st.text_input(
        "GitHub repository URL",
        placeholder="https://github.com/owner/repository",
        help="Enter a repository URL, not a branch, issue, pull request, or file URL.",
    )
    submitted = st.form_submit_button("Analyze repository", type="primary")

if "analysis_report" not in st.session_state:
    st.session_state.analysis_report = None

if submitted:
    st.session_state.analysis_report = None
    try:
        owner, repository = parse_repo_url(repo_url)
    except ValueError as exc:
        st.error(str(exc))
    else:
        api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key or api_key.lower().startswith(("your_", "your-", "replace_", "replace-")):
            st.error(
                "Set GOOGLE_API_KEY in .env to a valid Google AI Studio API key. "
                "Replace the example placeholder value before analyzing."
            )
        else:
            try:
                with st.status(
                    f"Analyzing {owner}/{repository}...",
                    expanded=True,
                ) as status:
                    st.write("Reading repository metadata and selected files...")
                    report = analyze_repository(
                        repo_url=repo_url,
                        model_name=model_name.strip() or DEFAULT_MODEL,
                        max_file_reads=max_file_reads,
                    )
                    st.session_state.analysis_report = report
                    status.update(label="Repository analysis complete.", state="complete")
            except GraphRecursionError:
                st.error(
                    "The agent reached its step limit before finishing. Try again with a "
                    "smaller source-file limit."
                )
            except GoogleAuthenticationError:
                st.error(
                    "Google rejected the configured API key. Check GOOGLE_API_KEY in .env, "
                    "save a valid key, and restart the app."
                )
            except (
                GitHubAPIError,
                GoogleGenerativeAIError,
                RuntimeError,
                ValueError,
            ) as exc:
                st.error(f"Analysis failed: {exc}")

if st.session_state.analysis_report is not None:
    _show_report(st.session_state.analysis_report)
