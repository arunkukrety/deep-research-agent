from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
import logging
import json

from tools.reddit_scraper import get_multiple_reddit_posts
from utils.prompts import REDDIT_PROCESSOR_PROMPT

logger = logging.getLogger(__name__)

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
    
    # Reddit processor outputs
    reddit_content: str
    reddit_summary: str
    
    # Summarizer outputs
    report_markdown: str
    
    # Meta
    errors: List[str]
    step_info: str

def create_reddit_processor_agent(llm: ChatGroq):
    """
    Creates a Reddit processor agent that:
    1. Takes Reddit URLs from the planner
    2. Scrapes the Reddit posts and comments using get_multiple_reddit_posts
    3. Provides a summary of the Reddit discussions
    """
    
    def reddit_processor_agent(state: GraphState) -> GraphState:
        try:
            reddit_urls = state.get("reddit_posts", [])
            original_query = state.get("user_input", "")
            
            logger.info(f"Reddit processor processing {len(reddit_urls)} Reddit URLs for: {original_query[:100]}...")
            
            if not reddit_urls:
                logger.info("No Reddit URLs to process")
                return {
                    **state,
                    "reddit_content": "",
                    "reddit_summary": "No Reddit discussions found for this topic.",
                    "step_info": "Reddit Processor (no URLs)",
                }
            
            # Scrape Reddit content
            try:
                # Call the tool with proper parameters
                reddit_content = get_multiple_reddit_posts.invoke({"urls": reddit_urls})
                logger.info(f"Successfully scraped {len(reddit_urls)} Reddit posts")
            except Exception as e:
                logger.error(f"Error scraping Reddit posts: {e}")
                reddit_content = f"Error scraping Reddit posts: {e}"
            
            # Generate summary using LLM
            try:
                summary_prompt = REDDIT_PROCESSOR_PROMPT.format(
                    query=original_query,
                    reddit_content=reddit_content[:8000]  # Limit content to avoid token limits
                )
                
                messages = [HumanMessage(content=summary_prompt)]
                response = llm.invoke(messages)
                reddit_summary = response.content
                
                logger.info("Generated Reddit summary successfully")
                
            except Exception as e:
                logger.error(f"Error generating Reddit summary: {e}")
                reddit_summary = f"Error generating summary: {e}"
            
            return {
                **state,
                "reddit_content": reddit_content,
                "reddit_summary": reddit_summary,
                "step_info": "Reddit Processor",
            }
            
        except Exception as e:
            logger.error(f"Reddit processor error: {e}")
            return {
                **state,
                "reddit_content": "",
                "reddit_summary": f"Error in Reddit processing: {e}",
                "errors": state.get("errors", []) + [f"Reddit processor error: {e}"],
                "step_info": "Reddit Processor (error)",
            }
    
    return reddit_processor_agent
