# Amazon Shopping Assistant Agent (LangGraph Edition)

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

2. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

4. Edit the `.env` file with your OpenAI API key and configuration:
   ```bash
   # Edit .env with your OpenAI API key and other settings
   ```

5. (Mac users only) Enable Safari WebDriver:
   ```bash
   safaridriver --enable
   ```

6. Run the LangGraph agent:
   ```bash
   python main_langgraph.py
   ```

## Usage

- When prompted, enter your shopping request in natural language (e.g., "Find me a coffee maker under $100 with good reviews that's available for Prime shipping").
- The agent will parse your query, search Amazon, rank products, and display the top results.

## Project Structure

```
amazon-shopping-assistant/
├── README.md
├── requirements.txt
├── setup.sh
├── .envrc                  # direnv configuration (optional)
├── .env.example
├── main_langgraph.py       # Main entry point (LangGraph agent)
├── venv/                   # Virtual environment directory
├── src/
│   ├── __init__.py
│   ├── amazon_scraper.py
│   ├── nlp_processor.py
│   ├── langgraph_nodes.py  # Stateless node functions for LangGraph
│   └── utils/
│       ├── __init__.py
│       ├── rate_limiter.py
│       └── config.py
└── tests/
    ├── __init__.py
    └── test_agent.py
```

## Development Notes

- Uses LangGraph for modular, stateful agent orchestration
- Rate limiting and human-like behavior for web scraping
- Focuses on extracting and ranking relevant product information
- Handles Amazon's dynamic interface changes

---

**To run the agent, always use:**
```bash
python main_langgraph.py
```

If you have questions or want to extend the workflow, see the code in `src/langgraph_nodes.py` and `main_langgraph.py` for how to add new steps or tools. 