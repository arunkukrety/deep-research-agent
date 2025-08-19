from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()


@tool
def serper_search_tool(query: str, locale: str = "us", language: str = "en") -> str:
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
        response = requests.post(BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        formatted_result = f"Search Results for: {query}\n\n"
        
        # knowledge graph info
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            formatted_result += "KNOWLEDGE GRAPH:\n"
            formatted_result += f"Title: {kg.get('title', 'N/A')}\n"
            formatted_result += f"Type: {kg.get('type', 'N/A')}\n"
            if "description" in kg:
                formatted_result += f"Description: {kg['description']}\n"
            if "attributes" in kg:
                formatted_result += "Attributes:\n"
                for key, value in kg["attributes"].items():
                    formatted_result += f"  - {key}: {value}\n"
            formatted_result += "\n"
        
        # organic search results
        if "organic" in data:
            formatted_result += "ORGANIC RESULTS:\n"
            for i, result in enumerate(data["organic"], 1):
                formatted_result += f"{i}. {result.get('title', 'No title')}\n"
                formatted_result += f"   URL: {result.get('link', 'No link')}\n"
                formatted_result += f"   Snippet: {result.get('snippet', 'No snippet')}\n"
                
                if "sitelinks" in result:
                    formatted_result += "   Sitelinks:\n"
                    for sitelink in result["sitelinks"]:
                        formatted_result += f"     - {sitelink.get('title', 'No title')}: {sitelink.get('link', 'No link')}\n"
                formatted_result += "\n"
        
        # people also ask
        if "peopleAlsoAsk" in data:
            formatted_result += "PEOPLE ALSO ASK:\n"
            for i, question in enumerate(data["peopleAlsoAsk"], 1):
                formatted_result += f"{i}. Q: {question.get('question', 'No question')}\n"
                formatted_result += f"   A: {question.get('snippet', 'No answer')}\n\n"
        
        # related searches
        if "relatedSearches" in data:
            formatted_result += "RELATED SEARCHES:\n"
            for i, related in enumerate(data["relatedSearches"], 1):
                formatted_result += f"{i}. {related.get('query', 'No query')}\n"
        
        return formatted_result
        
    except Exception as e:
        print(f"error occurred: {str(e)}")
        return f"Error fetching search results: {str(e)}"
