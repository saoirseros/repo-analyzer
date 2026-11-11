# GitHub Repository Analyzer

GitHub Repository Analyzer is an LLM-powered application that helps developers quickly understand an unfamiliar GitHub repository. Give it a repository URL, and the planned analyzer will gather repository metadata and selected source files, then produce an evidence-based architectural overview, potential code quality findings, and improvement suggestions.

> **Project status:** The Python environment, read-only GitHub API client, and bounded LangChain tools are in place. The analysis agent and Streamlit interface have not been implemented yet.

## What it will do

- Accept a GitHub repository URL.
- Retrieve repository metadata, its README, and folder structure through the GitHub API.
- Select and inspect relevant source files while limiting the amount of repository content analyzed.
- Use an LLM agent to explain the architecture and data flow.
- Report potential code quality issues and actionable improvements, with file-path evidence where possible.
- Present the results in a Streamlit interface.

## Planned workflow

1. Validate and parse the repository URL.
2. Fetch repository information, README, and file tree.
3. Choose relevant files and retrieve their contents.
4. Ask the agent to analyze the gathered evidence.
5. Display the architecture explanation, findings, and suggestions.

The agent is intended to analyze repository content as untrusted input and will not execute code from the repository.

## Technology stack

- **Python** for the application and GitHub API client
- **GitHub REST API** for repository metadata and file contents
- **LangChain and LangGraph** for LLM tools and agent orchestration
- **OpenAI API** for analysis and report generation
- **Streamlit** for the user interface
- **Pydantic** for structured data and report models
- **pytest** for automated tests

## Requirements

- Python 3.10 or newer
- An OpenAI API key
- A GitHub personal access token is recommended to increase API rate limits. Public repositories can generally be accessed without authentication; private repository access will require appropriate permissions.

## Getting started

### 1. Clone the repository

```powershell
git clone <repository-url>
cd github-repo-analyzer
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can invoke the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure API credentials

Copy the example environment file and add your credentials:

```powershell
Copy-Item .env.example .env
```

Set the following values in `.env`:

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | API key used to access the OpenAI API. |
| `GITHUB_TOKEN` | Optional for public repositories; recommended for higher API limits. |
| `OPENAI_MODEL` | OpenAI model name used by the analyzer. |

Never commit `.env` or expose API keys in source code, screenshots, logs, or issue reports. The `.env` file is excluded by `.gitignore`.

## Running the application

The Streamlit app entry point has not been added yet. Once the GitHub client, agent, and UI are implemented, this section will include the command to launch the app and instructions for analyzing a repository.

## Development

Install the project dependencies with `python -m pip install -r requirements.txt`. Run the GitHub client tests with:

```powershell
python -m pytest
```

The read-only client is available in `github_client.py`. LangChain tools are available through `create_github_tools` in `tools/langchain_tools.py`. They expose repository metadata, the README, a filtered recursive file tree, and individual file reads. File reads are limited to 10 per tool set and 200 KB per file by default. Generated directories, binary files, minified files, and lockfiles are excluded from file reads. Public repositories can be accessed without a token; the client reads `GITHUB_TOKEN` from the environment or `.env` when present.

## Privacy and responsible use

The planned analyzer will send selected repository text to the configured LLM provider for analysis. Only analyze repositories and content you are authorized to share with that provider. Do not put credentials or other secrets in prompts, and treat generated findings as suggestions that should be verified against the source code.

## Roadmap

- [x] Add project configuration, dependency list, and environment variable template.
- [x] Implement and test the GitHub API client.
- [x] Expose repository operations as agent tools.
- [ ] Build the analysis agent and structured report.
- [ ] Create the Streamlit interface.
- [ ] Add end-to-end testing and usage documentation.
