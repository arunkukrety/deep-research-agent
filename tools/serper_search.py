from langchain_core.tools import tool
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()


@tool
def serper_search_tool(
    query: str,
    locale: str = "us",
    language: str = "en",
    max_results: int = 5,
) -> str:
    """
    Fast Google search for quick facts, definitions, basic information, and structured data.
    Best for: what/when/where/who questions, definitions, lists, overviews, recent news.
    Returns: Knowledge graphs, snippets, related searches, people also ask questions.
    """
    print(f"searching with serper: {query}")
    
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not SERPER_API_KEY:
        return "Error: SERPER_API_KEY not found in environment variables"
    
    BASE_URL = "https://google.serper.dev/search"
    
    payload = {"q": query, "gl": locale, "hl": language, "autocorrect": True}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    
    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Build a compact JSON result with only the essentials to minimize LLM token usage
        compact = {
            "query": query,
            "knowledge_graph": None,
            "results": [],
        }

        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            compact["knowledge_graph"] = {
                "title": kg.get("title"),
                "type": kg.get("type"),
                "description": kg.get("description"),
            }

        organic = data.get("organic", [])[:max_results]
        for item in organic:
            compact["results"].append({
                "title": item.get("title"),
                "url": item.get("link"),
            })

        return json.dumps(compact, ensure_ascii=False)

    except Exception as e:
        print(f"error occurred: {str(e)}")
        return json.dumps({"error": f"Error fetching search results: {str(e)}"})
