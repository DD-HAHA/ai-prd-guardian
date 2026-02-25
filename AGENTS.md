# AGENTS.md

## Cursor Cloud specific instructions

### Overview

AI PRD Guardian Pro — a single-file Python/Streamlit app that uses DeepSeek LLM API (via OpenAI SDK) to perform multi-agent PRD reviews. No database, no Docker, no build step.

### Running the app

```bash
export PATH="$HOME/.local/bin:$PATH"
streamlit run app.py --server.headless true --server.port 8501
```

The app serves on `http://localhost:8501`. The `--server.headless true` flag is required in headless/cloud environments to avoid the "email prompt" on first launch.

### Key caveats

- **PATH**: After `pip install`, Streamlit and other scripts are installed to `~/.local/bin`. You must ensure `$HOME/.local/bin` is on `PATH` before running `streamlit`.
- **API key**: The app requires a `DEEPSEEK_API_KEY` to perform reviews. It can be provided either via a `.env` file in the project root or entered directly in the sidebar UI at runtime. Without a valid key, the AI review functionality will not work, but the UI itself loads and is interactive.
- **No linter/test suite configured**: The project has no linting config (pylint, flake8, etc.) or test framework. Use `python3 -m py_compile app.py` for basic syntax validation.
- **Hot reload**: Streamlit has built-in file watching. Editing `app.py` while the server is running will trigger an automatic re-run prompt in the browser.
