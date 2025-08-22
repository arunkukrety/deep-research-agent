from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
import re
import json
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from collections import defaultdict
from utils.prompts import PLANNER_PROMPT

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters and fragments."""
    try:
        parsed = urlparse(url)
        # Remove common tracking parameters
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 
                          'fbclid', 'gclid', 'ref', 'source', 'campaign_id'}
        query_params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        clean_query = urlencode(filtered_params, doseq=True)
        
        # Remove fragment and rebuild URL
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, ''))
    except Exception:
        return url

def deduplicate_and_diversify_urls(urls: List[str], max_urls: int = 8, max_per_domain: int = 2) -> List[str]:
    """Deduplicate URLs and enforce domain diversity."""
    if not urls:
        return []
    
    # Normalize and deduplicate
    normalized = {}
    for url in urls:
        if not url or not url.startswith(('http://', 'https://')):
            continue
        norm_url = normalize_url(url)
        if norm_url not in normalized:
            normalized[norm_url] = url
    
    # Group by domain
    domain_groups = defaultdict(list)
    for norm_url, orig_url in normalized.items():
        try:
            domain = urlparse(norm_url).netloc.lower()
            # Remove 'www.' prefix for grouping
            if domain.startswith('www.'):
                domain = domain[4:]
            domain_groups[domain].append(orig_url)
        except Exception:
            continue
    
    # Select URLs with domain diversity
    selected = []
    for domain, domain_urls in domain_groups.items():
        # Take up to max_per_domain from each domain
        selected.extend(domain_urls[:max_per_domain])
        if len(selected) >= max_urls:
            break
    
    return selected[:max_urls]

class Article(TypedDict, total=False):
    title: Optional[str]
    url: str
    text: str
    error: Optional[str]

class GraphState(TypedDict):
    # LangGraph plumbing
    messages: Annotated[list, add_messages]
    
    # Inputs
    user_input: str
    
    # Query enhancer outputs
    enhanced_query: str
    followup_questions: List[str]
    
    # Planner outputs
    selected_urls: List[str]
    articles: List[Article]
    reddit_posts: List[str]
    youtube_urls: List[str]
    platform_questions: List[str]
    
    # Scraper agent outputs
    platform_content: str
    platform_summary: str
    
    # Summarizer outputs
    report_markdown: str
    
    # Meta
    errors: List[str]
    step_info: str

def create_planner_agent(search_tools, llm):
    # react for url selection, exa crawling outside llm
    serper_search_tool, exa_crawl_tool = search_tools[0], search_tools[1]
    react_agent = create_react_agent(
        model=llm,
        tools=[serper_search_tool],
        state_modifier=PLANNER_PROMPT
    )
    
    def planner_agent(state: GraphState) -> GraphState:
        try:
            followup_questions = state.get("followup_questions", [])
            original_query = state.get("user_input", "")
            enhanced_query = state.get("enhanced_query", original_query)
            
            logger.info(f"Planner processing {len(followup_questions)} follow-up questions for: {original_query[:100]}...")
            
            # Ensure we have questions to search
            if not followup_questions:
                followup_questions = [enhanced_query or original_query]
                logger.warning("No follow-up questions found, using enhanced/original query")
            
            logger.info(f"Searching {len(followup_questions)} questions")
            
            # create research prompt
            research_prompt = f"""
Research these questions about "{original_query}":

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(followup_questions[:6]))}

WORKFLOW:
1. Search question 1 with serper_search_tool
2. Search question 2 with serper_search_tool  
3. Continue until all questions are searched
4. Search for Reddit discussions by adding 'site:reddit.com' to 2-3 key questions
5. Search for YouTube videos by adding 'site:youtube.com' to 2-3 key questions
6. After all searches, analyze all URLs found
7. Select 6-8 best URLs for comprehensive coverage
8. Extract Reddit and YouTube URLs separately for platform scraping
9. Output selected URLs in JSON format

CRITICAL:
- Search questions ONE BY ONE (don't try to search multiple at once)
- For Reddit searches: add 'site:reddit.com' to your query (e.g., "AI agents site:reddit.com")
- For YouTube searches: add 'site:youtube.com' to your query (e.g., "AI agents tutorial site:youtube.com")
- Look for URLs starting with 'https://www.reddit.com/r/' or 'https://reddit.com/r/'
- Look for URLs starting with 'https://www.youtube.com/watch' or 'https://youtu.be/'
- Choose URLs that complement each other, avoid duplicates
- Prioritize authoritative sources
- End with JSON: {{"selected_urls": ["url1", "url2", ...], "reddit_urls": ["reddit_url1", "reddit_url2", ...], "youtube_urls": ["youtube_url1", "youtube_url2", ...], "reasoning": "why these URLs"}}

Start with question 1 now.
"""
            
            # run react agent
            messages = [HumanMessage(content=research_prompt)]
            response = react_agent.invoke({"messages": messages})
            
            # extract urls from response
            final_message = response["messages"][-1].content
            raw_urls: List[str] = []
            reddit_urls: List[str] = []
            
            try:
                # extract json with urls
                json_match = re.search(r'\{[\s\S]*?"selected_urls"[\s\S]*?\}', final_message)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if isinstance(parsed.get("selected_urls"), list):
                        raw_urls = [u for u in parsed["selected_urls"] if isinstance(u, str) and u.startswith(('http://', 'https://'))]
                    if isinstance(parsed.get("reddit_urls"), list):
                        reddit_urls = [u for u in parsed["reddit_urls"] if isinstance(u, str) and u.startswith(('https://www.reddit.com/', 'https://reddit.com/'))]
                    if isinstance(parsed.get("youtube_urls"), list):
                        youtube_urls = [u for u in parsed["youtube_urls"] if isinstance(u, str) and u.startswith(('https://www.youtube.com/watch', 'https://youtu.be/'))]
            except Exception as e:
                logger.warning(f"Failed to parse URLs from JSON: {e}")

            if not raw_urls:
                # fallback: find urls in text
                raw_urls = re.findall(r"https?://\S+", final_message)
                logger.info(f"Fallback: extracted {len(raw_urls)} URLs from text")
            
            # Extract platform URLs from all found URLs
            youtube_urls = []
            if not reddit_urls:
                reddit_pattern = r'https?://(?:www\.)?reddit\.com/r/[^/\s]+/comments/[^/\s]+/[^/\s]+/?'
                reddit_urls = re.findall(reddit_pattern, final_message)
                # Also check in raw_urls for Reddit URLs
                for url in raw_urls:
                    if re.match(reddit_pattern, url):
                        reddit_urls.append(url)
                        raw_urls.remove(url)  # Remove from regular URLs
            
            # Extract YouTube URLs
            youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)[^&\s]+'
            youtube_urls = re.findall(youtube_pattern, final_message)
            # Also check in raw_urls for YouTube URLs
            for url in raw_urls:
                if re.match(youtube_pattern, url):
                    youtube_urls.append(url)
                    raw_urls.remove(url)  # Remove from regular URLs

            # Post-process URLs: deduplicate and enforce domain diversity
            selected_urls = deduplicate_and_diversify_urls(raw_urls, max_urls=8, max_per_domain=2)
            logger.info(f"Selected {len(selected_urls)} URLs after deduplication and diversity filtering")

            # crawl content with exa
            articles: List[Article] = []
            if selected_urls:
                try:
                    crawl_result_str = exa_crawl_tool.invoke({
                        "urls": selected_urls,
                        "max_urls": len(selected_urls),
                        "max_chars_per_article": 15000,
                        "max_total_chars": 100000,
                    })
                    
                    if isinstance(crawl_result_str, str):
                        crawl_json = json.loads(crawl_result_str)
                        raw_articles = crawl_json.get("articles", [])
                        
                        # Process articles and handle errors
                        for article in raw_articles:
                            if isinstance(article, dict):
                                processed_article: Article = {
                                    "title": article.get("title") or "Untitled",
                                    "url": article.get("url", ""),
                                    "text": article.get("text", "").strip(),
                                }
                                
                                # Skip articles with no meaningful content
                                if processed_article["text"] and len(processed_article["text"]) > 50:
                                    articles.append(processed_article)
                                else:
                                    processed_article["error"] = "No meaningful content extracted"
                                    articles.append(processed_article)
                        
                        logger.info(f"Successfully crawled {len([a for a in articles if not a.get('error')])} articles")
                        
                except Exception as crawl_err:
                    logger.error(f"Exa crawl failed: {crawl_err}")
                    articles.append({
                        "title": "Crawl Error",
                        "url": "",
                        "text": "",
                        "error": f"Exa crawl failed: {crawl_err}"
                    })
            else:
                logger.warning("No URLs to crawl")

            # Prepare platform questions for scraper agent
            platform_questions = followup_questions[:3]  # Use first 3 questions for platform search
            
            logger.info(f"Planner completed research with {len(selected_urls)} URLs, {len(articles)} articles, {len(reddit_urls)} Reddit URLs, and {len(youtube_urls)} YouTube URLs")

            return {
                **state,
                "selected_urls": selected_urls,
                "articles": articles,
                "reddit_posts": reddit_urls,  # Pass Reddit URLs to next step
                "youtube_urls": youtube_urls,  # Pass YouTube URLs to next step
                "platform_questions": platform_questions,  # Pass questions for platform search
                "step_info": "Planner",
            }

        except Exception as e:
            logger.error(f"Planner error: {e}")
            return {
                **state,
                "selected_urls": [],
                "articles": [],
                "errors": state.get("errors", []) + [f"Planner error: {e}"],
                "step_info": "Planner (error)",
            }
    
    return planner_agent
