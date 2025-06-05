# Amazon Shopping Assistant Agent

An autonomous agent that helps users shop on Amazon using natural language processing, advanced web automation with Playwright, and a modern graph-based workflow with [LangGraph](https://github.com/langchain-ai/langgraph).

## Features

- Natural language processing for shopping requests.
- Web automation using **Playwright** (standardized on Chromium) for Amazon interaction.
- Product information extraction and comparison.
- Smart filtering based on user preferences.
- **LLM-based relevance validation**: A post-processing step where top products are validated by an LLM for direct relevance to the search query, ensuring higher quality results.
- Interactive, modular, and extensible agent workflow using LangGraph.

## Technical Approach

- **Web Automation**: **Playwright** for robust browser interaction.
- **NLP**: OpenAI GPT models for natural language understanding and relevance validation.
- **Agent Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) for multi-step, stateful workflows.
- **Rate Limiting**: Human-like request throttling.
- **Concurrent Processing**: LLM validation calls for top products are made concurrently for improved performance.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd amazon-shopping-assistant
    ```

2.  **Prerequisites (If not already installed):**
    *   **Python**: Version 3.10 or higher recommended.
    *   **Node.js and npm**: For running the React frontend.
    *   **Rust (Potential Requirement)**: Some Python dependencies (like `pydantic-core` which might be a sub-dependency) may require Rust. If you encounter issues during `pip install`, you might need to install Rust:
        ```bash
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        rustc --version
        ```
    *   **OpenBLAS (Potential Requirement for `scipy`)**: If `scipy` is a direct or indirect dependency and causes issues, you might need to OpenBLAS. For macOS using Homebrew:
        ```bash
        brew install openblas
        ```

3.  **Run the Setup Script:**
    This script creates a Python virtual environment (`venv/`) and installs backend dependencies from `requirements.txt`.
    ```bash
    ./setup.sh
    ```
    *After running `setup.sh`, ensure the virtual environment is active for subsequent backend commands: `source venv/bin/activate`*

4.  **Install Playwright Browsers:**
    After dependencies are installed, you need to install the browser binaries for Playwright (this project primarily uses Chromium).
    ```bash
    playwright install chromium
    # Or 'playwright install' to install all default browsers (Chromium, Firefox, WebKit)
    ```

5.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory by copying `.env.example`:
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file with your configurations:
    *   `OPENAI_API_KEY`: **Required**. Your API key from OpenAI.
    *   `AMAZON_BASE_URL`: Defaults to `https://www.amazon.com`. Change if needed for a different Amazon region.
    *   `HEADLESS_MODE`: Set to `True` to run the browser invisibly in the background, or `False` to see the browser window. **Defaults to `False` (headed mode)** if not set.
    *   `USER_AGENT`: A default user agent is provided. Change if necessary.
    *   Other variables like `MAX_REQUESTS_PER_MINUTE`, `REQUEST_DELAY_MIN`, `REQUEST_DELAY_MAX` can also be configured.

## Running the Web Application (React UI + Python API)

The primary way to interact with the Amazon Shopping Assistant is through a web interface. The backend API server and the frontend development server must run concurrently.

### 1. Backend Setup & Execution (API Server)

-   **Location**: Project root directory (`amazon-shopping-assistant/`).
-   **Environment**:
    -   Activate the Python virtual environment: `source venv/bin/activate`.
    -   Ensure your `.env` file is correctly configured in the project root.
-   **Run the API Server**:
    ```bash
    python app.py
    ```
-   **API Availability**: Typically at `http://127.0.0.1:5001`. Main endpoint: `POST /api/query`.

### 2. Frontend Setup & Execution (React UI)

-   **Location**: The `frontend/` directory.
-   **Dependencies**: Navigate to the frontend directory and install Node.js dependencies:
    ```bash
    cd frontend
    npm install
    # If not already present from previous setup, ensure Tailwind dependencies are there:
    # npm install -D tailwindcss postcss autoprefixer
    ```
-   **Run the Frontend Development Server**:
    ```bash
    npm run dev
    ```
-   **Accessing the UI**: Typically at `http://localhost:5173` (check terminal output). Open this URL in your browser.

**Note:** Both backend and frontend servers must be running simultaneously.

## Key Configuration Constants (Code)

Some operational parameters are set as constants in the Python code:
-   `src/constants.py`:
    -   `TOP_N_FOR_LLM_VALIDATION`: Defines how many top-scored products (after initial scoring) are sent for LLM relevance validation. Currently set to `25`.
    -   `MISSING_SCORE`: Default score for certain missing attributes.

## Project Structure Overview

```
amazon-shopping-assistant/
├── README.md
├── requirements.txt        # Python backend dependencies
├── setup.sh                # Script to set up Python environment
├── .env.example            # Example environment variables
├── .env                    # Your environment variables
├── app.py                  # Main Flask application (Backend API server)
├── frontend/               # React frontend application
│   └── ...                 # (Structure as before)
├── src/                    # Python source code for the backend
│   ├── agent.py            # Core agent workflow (LangGraph definition)
│   ├── amazon_scraper.py   # Playwright-based Amazon scraper
│   ├── nlp_processor.py    # NLP (OpenAI GPT) & LLM validation logic
│   ├── langgraph_nodes.py  # Nodes for the LangGraph agent
│   ├── product_scorer.py   # Logic for scoring products (excluding main search term relevance)
│   ├── constants.py        # Key constants like TOP_N_FOR_LLM_VALIDATION
│   ├── models.py           # Pydantic models
│   └── utils/              # Utility modules (config, rate limiter)
│   └── prompts/            # Prompt files for LLMs
│       ├── relevance_validator.txt # Prompt for yes/no relevance
│       └── ...
├── tests/                  # Python backend tests
│   └── ...                 # (Structure as before)
└── ...
```
*(Project structure is simplified for brevity here, showing key changes.)*

## Development Notes

- Uses LangGraph for modular, stateful agent orchestration.
- Playwright with Chromium is used for web scraping.
- LLM validation acts as a post-processing filter on an initial set of top products to improve final relevance.
- Focuses on extracting and ranking relevant product information based on user queries and explicit preferences.

## Original CLI (`main.py`)
The `main.py` file provides an older command-line interface. While the core logic has been updated, the primary interaction method is now the web application (`app.py` + frontend). If using `main.py`, ensure it's adapted for any changes in `agent.py` or other core modules if necessary.

---

Find the original report [here](https://hackmd.io/@nJ3wWZdKQGi1_-J7hyBKlg/r177wlNxlg) and demo [here](https://youtu.be/FADMUAF30ak). (These may refer to older versions of the project).
