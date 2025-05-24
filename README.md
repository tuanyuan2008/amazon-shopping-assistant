# Amazon Shopping Assistant Agent

An autonomous agent that helps users shop on Amazon using natural language processing, web automation, and a modern graph-based workflow with [LangGraph](https://github.com/langchain-ai/langgraph).

## Features

- Natural language processing for shopping requests
- Amazon interface navigation (auto-detects Safari on Mac, Chrome elsewhere)
- Product information extraction and comparison
- Smart filtering based on user preferences
- Interactive, modular, and extensible agent workflow using LangGraph

## Technical Approach

- **Web Automation**: Selenium WebDriver for Amazon interaction
- **NLP**: OpenAI GPT models for natural language understanding
- **Agent Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) for multi-step, stateful workflows
- **Rate Limiting**: Human-like request throttling

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd amazon-shopping-assistant
   ```

2. Install Rust (required for pydantic-core):
   ```bash
   # Install Rust
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
   
   # Add Rust to your PATH
   source "$HOME/.cargo/env"
   
   # Verify installation
   rustc --version
   ```

3. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   ./setup.sh
   ```

4. Install OpenBLAS and scipy:
   ```bash
   # Install OpenBLAS (required for scipy)
   brew install openblas
   
   # Install scipy using pre-built wheel
   pip install --only-binary :all: scipy
   ```

5. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

6. Edit the `.env` file with your OpenAI API key and configuration:
   ```bash
   # Edit .env with your OpenAI API key and other settings
   ```

7. (Mac users only) Enable Safari WebDriver:
   ```bash
   safaridriver --enable
   ```
   
## Usage (CLI)

The original command-line interface (CLI) for the agent can be run as described below. For the new web-based UI, see the "Running the Web Application" section.

- After completing the "Setup" steps (including activating the virtual environment and setting up the `.env` file):
- Run the CLI using:
  ```bash
  python main.py
  ```
- When prompted, enter your shopping request in natural language (e.g., "Find me a coffee maker under $100 with good reviews that's available for Prime shipping").
- The agent will parse your query, search Amazon, rank products, and display the top results in the console.

## Running the Web Application (React UI + Python API)

The primary way to interact with the Amazon Shopping Assistant is now through a web interface powered by a React frontend and a Python (Flask) backend API. These two components need to be run concurrently.

### 1. Backend Setup & Execution (API Server)

The backend server provides the API that the frontend consumes.

-   **Location**: The project root directory (`amazon-shopping-assistant/`).
-   **Environment**:
    -   Ensure your Python virtual environment is activated (e.g., `source venv/bin/activate` if you used `setup.sh`).
    -   Make sure you have a `.env` file in the project root with your `OPENAI_API_KEY` and any other necessary configurations (refer to `.env.example`).
-   **Dependencies**: Install or update Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
-   **Running the API Server**:
    ```bash
    python app.py
    ```
-   **API Availability**: The backend API will start and typically be available at `http://127.0.0.1:5000`. The main endpoint used by the frontend is `POST /api/query`.

### 2. Frontend Setup & Execution (React UI)

The frontend provides the user interface in your browser.

-   **Location**: The `frontend/` directory.
-   **Dependencies**: Navigate to the frontend directory and install Node.js dependencies:
    ```bash
    cd frontend
    npm install
    npm install -D tailwindcss@3.4.1 postcss autoprefixer
    ```
-   **Tailwind CSS Setup**: The project uses Tailwind CSS for styling. The configuration is already set up in:
    - `tailwind.config.js` - Contains custom theme settings and content paths
    - `postcss.config.js` - Configures PostCSS with Tailwind CSS and Autoprefixer
    - `src/index.css` - Includes Tailwind directives (@tailwind base, components, utilities)
-   **Running the Frontend Development Server**:
    ```bash
    npm run dev
    ```
    *(Note: In some environments, if `vite` is not found, you might need to run `npx vite` or `./node_modules/.bin/vite` directly from the `frontend` directory.)*
-   **Accessing the UI**: Vite will typically start the frontend development server at `http://localhost:5173` (or another port if 5173 is busy - check the output in your terminal). Open this URL in your web browser.

### Development Note:
Both the backend API server (`python app.py`) and the frontend development server (`npm run dev` in the `frontend` directory) must be running at the same time for the web application to function correctly. The React frontend makes requests to the Python backend API to process queries and fetch results.

## Project Structure

```
amazon-shopping-assistant/
├── README.md
├── requirements.txt        # Python backend dependencies
├── setup.sh                # Script to set up Python environment
├── .env.example            # Example environment variables
├── .env                    # Your environment variables (contains API keys)
├── app.py                  # Main Flask application (Backend API server)
├── main.py                 # Original CLI entry point for the agent
├── frontend/               # React frontend application
│   ├── package.json        # Frontend dependencies and scripts
│   ├── vite.config.ts      # Vite configuration (build tool for frontend)
│   ├── tailwind.config.js  # Tailwind CSS configuration
│   ├── postcss.config.js   # PostCSS configuration
│   ├── public/             # Static assets for the frontend
│   └── src/                # Frontend source code (React components, services)
│       ├── App.tsx         # Main React application component
│       ├── index.css       # Main CSS file (includes Tailwind directives)
│       └── components/     # Reusable React components
│           ├── QueryInput.tsx
│           ├── ResultsDisplay.tsx
│           └── SummaryDisplay.tsx
│       └── services/       # API service for frontend-backend communication
│           └── api.ts
├── src/                    # Python source code for the backend agent logic
│   ├── __init__.py
│   ├── agent.py            # Core agent workflow and state management
│   ├── amazon_scraper.py   # Selenium-based Amazon scraper
│   ├── nlp_processor.py    # NLP processing using OpenAI
│   ├── langgraph_nodes.py  # Nodes for the LangGraph agent
│   ├── models.py           # Pydantic models
│   └── utils/              # Utility modules (config, rate limiter)
│       ├── __init__.py
│       ├── config.py
│       └── rate_limiter.py
├── tests/                  # Python backend tests
│   ├── __init__.py
│   └── test_app.py         # Pytest tests for the Flask API
└── venv/                   # Python virtual environment (if created by setup.sh)
```

## Development Notes

- Uses LangGraph for modular, stateful agent orchestration
- Rate limiting and human-like behavior for web scraping
- Focuses on extracting and ranking relevant product information
- Handles Amazon's dynamic interface changes

## Walk-Through Demo
https://youtu.be/FADMUAF30ak

Find the report [here](https://hackmd.io/@nJ3wWZdKQGi1_-J7hyBKlg/r177wlNxlg).

---

**To run the agent, always use:**
```bash
python main.py
```

If you have questions or want to extend the workflow, see the code in `src/langgraph_nodes.py` and `main.py` for how to add new steps or tools. 
