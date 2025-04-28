# Amazon Shopping Assistant Agent

An autonomous agent that helps users shop on Amazon using natural language processing and web automation.

## Features

- Natural language processing for shopping requests
- Amazon interface navigation
- Product information extraction and comparison
- Smart filtering based on user preferences
- Interactive follow-up and refinement capabilities

## Technical Approach

- **Web Automation**: Using Selenium WebDriver for reliable Amazon interface interaction
- **NLP**: Leveraging OpenAI's GPT models for natural language understanding
- **Data Processing**: Structured product information extraction and comparison
- **Rate Limiting**: Implemented request throttling and human-like behavior patterns

## Setup

1. Clone the repository:
```bash
git clone https://github.com/tuanyuan2008/amazon-shopping-assistant.git
cd amazon-shopping-assistant
```

2. Run the setup script to create a virtual environment and install dependencies:
```bash
./setup.sh
```

3. Choose one of the following methods for auto-activating the virtual environment:

   a. Using direnv (recommended):
   ```bash
   # Install direnv if you haven't already
   brew install direnv  # For macOS
   # or
   sudo apt-get install direnv  # For Ubuntu/Debian

   # Add to your shell config (~/.bashrc or ~/.zshrc)
   eval "$(direnv hook bash)"  # For bash
   # or
   eval "$(direnv hook zsh)"   # For zsh

   # Allow the .envrc file
   direnv allow
   ```

   b. Using bash auto-activation:
   ```bash
   # Add to your ~/.bashrc
   source /path/to/amazon-shopping-assistant/.bashrc
   ```

4. Edit the `.env` file with your API keys and configuration:
```bash
# Edit .env with your OpenAI API key and other settings
```

5. Run the agent:
```bash
safaridriver --enable
python main.py
```

To deactivate the virtual environment when you're done:
```bash
deactivate
```

## Project Structure

```
amazon-shopping-assistant/
├── README.md
├── requirements.txt
├── setup.sh
├── .envrc                  # direnv configuration
├── .bashrc                 # bash auto-activation
├── .env.example
├── main.py
├── venv/                  # Virtual environment directory
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── amazon_scraper.py
│   ├── nlp_processor.py
│   └── utils/
│       ├── __init__.py
│       ├── rate_limiter.py
│       └── config.py
└── tests/
    ├── __init__.py
    └── test_agent.py
```

## Development Notes

- Implemented rate limiting to avoid detection
- Uses human-like behavior patterns for web interaction
- Focuses on extracting relevant product information
- Handles Amazon's dynamic interface changes 