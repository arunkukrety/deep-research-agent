from .serper_search import serper_search_tool

# Import exa_crawl_urls only if exa_py is available
try:
    from .exa_search import exa_crawl_urls
    __all__ = [
        "serper_search_tool",
        "exa_crawl_urls"
    ]
except ImportError:
    # If exa_py is not available, create a placeholder
    def exa_crawl_urls(urls):
        return f"Error: exa_py not installed. Cannot crawl URLs: {urls}"
    
    __all__ = [
        "serper_search_tool",
        "exa_crawl_urls"
    ]
