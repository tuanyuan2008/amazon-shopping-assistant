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
   
## Usage

- When prompted, enter your shopping request in natural language (e.g., "Find me a coffee maker under $100 with good reviews that's available for Prime shipping").
- The agent will parse your query, search Amazon, rank products, and display the top results.

## Running the Web UI

As an alternative to the command-line interface, you can interact with the Amazon Shopping Assistant through a web-based UI.

1.  **Ensure Dependencies are Installed**:
    Make sure you have all the necessary Python packages installed. If you've followed the main "Setup" instructions, these should already be in your virtual environment. If not, or if you're setting up fresh, install them from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure your virtual environment is activated if you are using one.)*

2.  **Start the Flask Development Server**:
    Run the `app.py` script from the root of the project:
    ```bash
    python app.py
    ```

3.  **Access the UI**:
    Open your web browser and navigate to:
    ```
    http://127.0.0.1:5000
    ```
    You should see the Amazon Shopping Assistant interface, where you can type your search queries.

The web UI provides a graphical way to input your shopping requests and view the summarized results and product listings.

## Project Structure

```
amazon-shopping-assistant/
├── README.md
├── requirements.txt
├── setup.sh
├── .envrc                  # direnv configuration
├── .env.example
├── .env                    # environment variables
├── main.py                 # Main entry point (LangGraph workflow)
├── venv/                   # Virtual environment directory
├── src/
│   ├── __init__.py
│   ├── amazon_scraper.py
│   ├── nlp_processor.py
│   ├── langgraph_nodes.py  # Stateless node functions for LangGraph
│   ├── models.py           # Pydantic models for data validation
│   └── utils/
│       ├── __init__.py
│       ├── rate_limiter.py
│       └── config.py
└── tests/
    └── __init__.py
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
