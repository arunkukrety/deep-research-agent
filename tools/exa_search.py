from langchain_core.tools import tool
from exa_py import Exa
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


@tool
def exa_crawl_urls(urls: List[str], max_urls: int = 3) -> str:
    """
    Crawl and extract full content from specific URLs using Exa.
    Best for: getting complete article content from known URLs.
    Takes a list of URLs and returns full text content from each.
    """
    print(f"crawling {len(urls)} urls with exa")
    
    EXA_API_KEY = os.getenv("EXA_API_KEY")
    if not EXA_API_KEY:
        return "Error: EXA_API_KEY not found in environment variables"
    
    try:
        exa_client = Exa(api_key=EXA_API_KEY)
        
        # limit to max_urls to avoid too many requests
        urls_to_crawl = urls[:max_urls]
        
        # get contents from specific URLs
        result = exa_client.get_contents(
            urls=urls_to_crawl,
            text=True,
        )
        
        if not result.results:
            return f"no content extracted from provided urls"
        
        # format crawled content
        formatted_result = f"Crawled Content from {len(result.results)} URLs:\n\n"
        
        for i, res in enumerate(result.results, 1):
            formatted_result += f"ARTICLE {i}:\n"
            formatted_result += f"Title: {res.title}\n"
            formatted_result += f"URL: {res.url}\n\n"
            formatted_result += f"FULL CONTENT:\n{res.text}\n"
            formatted_result += "=" * 80 + "\n\n"
        
        return formatted_result
        
    except Exception as e:
        print(f"exa crawl error: {e}")
        return f"Error crawling URLs with Exa: {str(e)}"
