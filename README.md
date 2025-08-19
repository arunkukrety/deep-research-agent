# langgraph research agent

comprehensive ai research agent with web api that generates detailed reports using multiple llms and search tools.

## 🚀 features

- **3-stage pipeline**: query enhancer → planner → summarizer
- **dual llm setup**: groq (llama 3.1) for search planning, gemini for report writing
- **web search**: serper api for google search results
- **content crawling**: exa api for full article extraction
- **fastapi endpoint**: `/research?q=query` returns markdown reports
- **token optimization**: prevents groq context overflow
- **detailed reports**: comprehensive analysis, not summaries
- **auto file saving**: saves reports to `output/` folder

## 📋 requirements

- python 3.13+
- api keys:
  - **GROQ_API_KEY** - [groq console](https://console.groq.com/)
  - **SERPER_API_KEY** - [serper.dev](https://serper.dev/)
  - **EXA_API_KEY** - [exa.ai](https://exa.ai/)
  - **GOOGLE_API_KEY** - [google ai studio](https://aistudio.google.com/)

## 🛠️ installation

### using uv (recommended)
```bash
git clone <repo-url>
cd langgraph-agent
uv sync
```

### using pip
```bash
git clone <repo-url>
cd langgraph-agent
pip install -r requirements.txt
```

### for api usage
```bash
# add api dependencies
uv add fastapi uvicorn
# or with pip
pip install fastapi uvicorn
```

## ⚙️ setup

create `.env` file:
```env
GROQ_API_KEY=your_key_here
SERPER_API_KEY=your_key_here  
EXA_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## 🚀 usage

### api mode (recommended)
```bash
python api.py
```
then visit: `http://localhost:8000/research?q=your-query`

### command line mode
```bash
python main.py
```

### programmatic usage
```python
from main import graph_builder

agent = graph_builder()
result = agent.invoke({"user_input": "ai trends 2024"})
print(result["llm_response"])
```

## 🏗️ structure

```
langgraph-agent/
├── agents/                 # research pipeline
│   ├── query_enhancer.py   # improves user queries
│   ├── planner.py          # searches + selects urls
│   └── summarizer.py       # writes final reports
├── tools/                  # search tools
│   ├── serper_search.py    # google search via serper
│   └── exa_search.py       # content crawling via exa
├── utils/                  # shared utilities
│   ├── llm.py             # groq + gemini clients
│   └── prompts.py         # agent prompts
├── output/                # saved reports
├── main.py                # cli workflow
├── api.py                 # fastapi web server
├── pyproject.toml         # dependencies
└── requirements.txt       # pip fallback
```

## 🌐 api endpoints

- `GET /` - health check
- `GET /research?q=query` - generates markdown research report
- `GET /docs` - api documentation

## 🔧 how it works

1. **query enhancer** (gemini) - improves user query, generates research questions
2. **planner** (groq) - searches with serper, selects best urls, crawls with exa
3. **summarizer** (gemini) - writes comprehensive report from crawled content

## 📊 token optimization

- groq only processes lightweight search results (not full articles)
- exa crawling happens outside llm context
- gemini handles large content for final reports
- prevents 413 token limit errors

## 🚀 deployment

works on any python hosting platform:
- railway, render, heroku
- vercel, netlify functions  
- aws lambda, google cloud run
- local with ngrok for testing


