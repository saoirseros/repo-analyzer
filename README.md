# GitHub Repository Analyzer

GitHub Repository Analyzer is an LLM-powered application that helps developers quickly understand an unfamiliar GitHub repository. Give it a repository URL, and the analyzer gathers repository metadata and selected source files, then produces an evidence-based architectural overview, potential code quality findings, and improvement suggestions.

> **Project status:** The Python environment, read-only GitHub API client, bounded LangChain tools, structured analysis agent, and Streamlit interface are in place.

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
- **Google Gemini Developer API** for analysis and report generation
- **Streamlit** for the user interface
- **Pydantic** for structured data and report models
- **pytest** for automated tests

## Requirements

- Python 3.10 or newer
- A Google AI Studio API key. The default Gemini model is listed on Google's free tier, subject to current model availability and usage limits.
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
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, you can invoke the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configure API credentials

Copy the example environment file and add your credentials:

```powershell
Copy-Item .env.example .env
```

#### Get a Gemini API key

1. Open [Google AI Studio's API keys page](https://aistudio.google.com/apikey) and sign in with your Google account.
2. Accept the Gemini API terms if prompted.
3. Select **Create API key**. If prompted to choose a project, use the project AI Studio created or import a Google Cloud project you control.
4. Copy the generated key and keep it private.
5. In `.env`, replace the `GOOGLE_API_KEY` placeholder with the key:

   ```text
   GOOGLE_API_KEY=paste-your-key-here
   ```

Do not paste the key into chat, commit it, or put it in screenshots. Google's free tier has usage limits, and Google may use free-tier content to improve its products, so use only public, non-confidential repositories.

Set the following values in `.env`:

| Variable | Description |
| --- | --- |
| `GOOGLE_API_KEY` | API key from Google AI Studio used to access the Gemini API. `GEMINI_API_KEY` is also accepted. |
| `GITHUB_TOKEN` | Optional for public repositories; recommended for higher API limits. |
| `GOOGLE_MODEL` | Gemini model name. Defaults to `gemini-3.1-flash-lite`. |

Replace the example placeholder values with your own credentials. The Gemini free tier has usage limits, and Google may use free-tier content to improve its products. Do not send private or confidential repository code to the free-tier API. Never commit `.env` or expose API keys in source code, screenshots, logs, or issue reports. The `.env` file is excluded by `.gitignore`.

## Running the application

After completing the setup and configuring `.env`, launch the Streamlit interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Paste a repository URL, choose a model and source-file limit in the sidebar, and select **Analyze repository**. The report is shown in tabs and can be downloaded as JSON.

## Development

Install the project dependencies with `python -m pip install -r requirements.txt`. Run the GitHub client tests with:

```powershell
python -m pytest
```

The read-only client is available in `github_client.py`. LangChain tools are available through `create_github_tools` in `tools/langchain_tools.py`. The structured report models are in `agent/schemas.py`, and `analyze_repository` in `agent/runner.py` runs the analysis agent. Tools expose repository metadata, the README, a filtered recursive file tree, and individual file reads. File reads are limited to 10 per analysis and 200 KB per file by default. Generated directories, binary files, minified files, and lockfiles are excluded from file reads. Public repositories can be accessed without a token; the client reads `GITHUB_TOKEN` from the environment or `.env` when present.

## Privacy and responsible use

The planned analyzer will send selected repository text to the configured LLM provider for analysis. Only analyze repositories and content you are authorized to share with that provider. Do not put credentials or other secrets in prompts, and treat generated findings as suggestions that should be verified against the source code.

## Roadmap

- [x] Add project configuration, dependency list, and environment variable template.
- [x] Implement and test the GitHub API client.
- [x] Expose repository operations as agent tools.
- [x] Build the analysis agent and structured report.
- [x] Create the Streamlit interface.
- [ ] Add end-to-end testing.
