from langchain_core.tools import tool
from exa_py import Exa
import os
from typing import List, Optional
from dotenv import load_dotenv
import json

load_dotenv()

_EXA_CLIENT: Optional[Exa] = None

def _get_exa_client() -> Optional[Exa]:
    global _EXA_CLIENT
    if _EXA_CLIENT is None:
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            return None
        _EXA_CLIENT = Exa(api_key=api_key)
    return _EXA_CLIENT


@tool
def exa_crawl_urls(
    urls: List[str],
    max_urls: int = 3,
    max_chars_per_article: int = 6000,
    max_total_chars: int = 20000,
) -> str:
    """
    Crawl and extract full content from specific URLs using Exa.
    Best for: getting complete article content from known URLs.
    Takes a list of URLs and returns full text content from each.
    """
    print(f"crawling {len(urls)} urls with exa")
    
    client = _get_exa_client()
    if client is None:
        return "Error: EXA_API_KEY not found in environment variables"
    
    try:
        # limit to max_urls to avoid too many requests
        urls_to_crawl = urls[:max_urls]
        
        # get contents from specific URLs
        result = client.get_contents(
            urls=urls_to_crawl,
            text=True,
        )
        
        if not result.results:
            return json.dumps({"articles": []})
        
        articles = []
        total = 0
        for res in result.results:
            text = (res.text or "")[:max_chars_per_article]
            total += len(text)
            articles.append({
                "title": getattr(res, "title", None),
                "url": getattr(res, "url", None),
                "text": text,
            })
            if total >= max_total_chars:
                break
        
        return json.dumps({"articles": articles}, ensure_ascii=False)
        
    except Exception as e:
        print(f"exa crawl error: {e}")
        return f"Error crawling URLs with Exa: {str(e)}"
