# LangGraph Research Agent

A powerful research agent built with LangGraph that uses Groq's LLaMA and Google's Gemini models for comprehensive web research and report generation.

## 🚀 Features

- **Multi-Agent Architecture**: Query enhancer → Planner → Summarizer workflow
- **Dual LLM Support**: Groq (LLaMA 3.1) for research, Gemini for summarization
- **Web Search Integration**: Serper API for comprehensive search results
- **Markdown Reports**: Automatically saves research reports to `output/` folder
- **Modular Design**: Separate agents, tools, and utilities for easy maintenance

## 📋 Prerequisites

- Python 3.13+
- API Keys:
  - **GROQ_API_KEY** - Get from [Groq Console](https://console.groq.com/)
  - **SERPER_API_KEY** - Get from [Serper.dev](https://serper.dev/)
  - **GOOGLE_API_KEY** - Get from [Google AI Studio](https://aistudio.google.com/)

## 🛠️ Installation

### Option 1: Using UV (Recommended - Faster)
```bash
# Clone the repository
git clone <your-repo-url>
cd langgraph-agent

# Install dependencies with uv
uv sync

# Or add individual packages
uv add langchain langgraph langchain-groq
```

### Option 2: Using PIP (Traditional)
```bash
# Clone the repository
git clone <your-repo-url>
cd langgraph-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Using pyproject.toml directly
```bash
# Modern pip supports pyproject.toml
pip install -e .
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
SERPER_API_KEY=your_serper_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Optional (for tracing)
LANGSMITH_API_KEY=your_langsmith_key_here
```

## 🚀 Usage

### Basic Usage
```python
from main import mygraph

# Run research on any topic
result = mygraph.invoke({"user_input": "What are the latest AI developments?"})

# Result is automatically saved to output/ folder as markdown
```

### Command Line
```bash
python main.py
```

## 🏗️ Project Structure

```
langgraph-agent/
├── agents/                 # Agent implementations
│   ├── query_enhancer.py   # Enhances user queries
│   ├── planner.py          # Research planning & execution
│   └── summarizer.py       # Final report generation
├── tools/                  # Search tools
│   └── serper_search.py    # Web search functionality
├── utils/                  # Utilities
│   ├── llm.py             # LLM initialization
│   └── prompts.py         # Centralized prompts
├── output/                # Generated reports (auto-created)
├── main.py                # Main workflow orchestration
├── pyproject.toml         # Modern Python project config
└── requirements.txt       # Pip compatibility
```

## 🔧 Development

### Adding New Dependencies

**With UV:**
```bash
uv add new-package
```

**With PIP:**
```bash
pip install new-package
pip freeze > requirements.txt
```

### Running Tests
```bash
python main.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---


