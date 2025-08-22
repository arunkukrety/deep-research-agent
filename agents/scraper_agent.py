from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
import logging
import json

from tools.reddit_scraper import get_multiple_reddit_posts
from tools.youtube_transcript import get_multiple_youtube_transcripts
from utils.prompts import SCRAPER_AGENT_PROMPT

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
    youtube_urls: List[str]
    platform_questions: List[str]
    
    # Scraper agent outputs
    platform_content: str
    platform_summary: str
    platform_urls: dict
    
    # Summarizer outputs
    report_markdown: str
    
    # Meta
    errors: List[str]
    step_info: str

def create_scraper_agent(llm: ChatGroq):
    """
    Creates a central scraper agent that:
    1. Receives platform questions and URLs from the planner
    2. Performs platform-specific searches if needed
    3. Extracts content using Reddit and YouTube tools
    4. Generates a comprehensive summary of all platform content
    5. Updates the state with platform content and summary
    """
    
    def scraper_agent(state: GraphState) -> GraphState:
        try:
            reddit_urls = state.get("reddit_posts", [])
            youtube_urls = state.get("youtube_urls", [])
            platform_questions = state.get("platform_questions", [])
            original_query = state.get("user_input", "")
            
            logger.info(f"Scraper agent processing {len(reddit_urls)} Reddit URLs, {len(youtube_urls)} YouTube URLs for: {original_query[:100]}...")
            
            all_platform_content = []
            platform_summaries = []
            
            # Process Reddit content
            if reddit_urls:
                try:
                    logger.info(f"Extracting Reddit content from {len(reddit_urls)} URLs")
                    reddit_content = get_multiple_reddit_posts.invoke({"urls": reddit_urls})
                    all_platform_content.append(f"## REDDIT DISCUSSIONS\n\n{reddit_content}")
                    platform_summaries.append("Reddit: Community discussions and opinions extracted")
                    logger.info("Successfully extracted Reddit content")
                except Exception as e:
                    logger.error(f"Error extracting Reddit content: {e}")
                    all_platform_content.append(f"## REDDIT DISCUSSIONS\n\nError extracting Reddit content: {e}")
                    platform_summaries.append("Reddit: Error occurred during extraction")
            else:
                logger.info("No Reddit URLs to process")
            
            # Process YouTube content
            if youtube_urls:
                try:
                    logger.info(f"Extracting YouTube transcripts from {len(youtube_urls)} URLs: {youtube_urls[:3]}...")
                    youtube_content = get_multiple_youtube_transcripts.invoke({"urls": youtube_urls})
                    all_platform_content.append(f"## YOUTUBE TRANSCRIPTS\n\n{youtube_content}")
                    platform_summaries.append(f"YouTube: {len(youtube_urls)} video transcripts extracted")
                    logger.info(f"Successfully extracted YouTube content from {len(youtube_urls)} videos")
                except Exception as e:
                    logger.error(f"Error extracting YouTube content: {e}")
                    all_platform_content.append(f"## YOUTUBE TRANSCRIPTS\n\nError extracting YouTube content: {e}")
                    platform_summaries.append("YouTube: Error occurred during extraction")
            else:
                logger.warning("No YouTube URLs found - planner may not have searched for YouTube content properly")
            
            # Combine all platform content
            if all_platform_content:
                platform_content = "\n\n" + "=" * 80 + "\n\n".join(all_platform_content)
                logger.info(f"Combined platform content ({len(platform_content)} characters)")
            else:
                platform_content = "No platform content found for this query."
                logger.warning("No platform content to process")
            
            # Skip LLM processing to avoid token limits - pass raw content directly
            platform_summary = f"Raw platform content extracted: {len(reddit_urls)} Reddit posts ({len([c for c in all_platform_content if 'REDDIT' in c])} successful), {len(youtube_urls)} YouTube videos ({len([c for c in all_platform_content if 'YOUTUBE' in c])} successful)"
            logger.info(f"Passing raw platform content directly to avoid token limits - {len(platform_content)} total characters")
            
            # Add platform URLs to state for sources
            platform_urls = {
                "reddit_urls": reddit_urls,
                "youtube_urls": youtube_urls
            }
            
            return {
                **state,
                "platform_content": platform_content,
                "platform_summary": platform_summary,
                "platform_urls": platform_urls,
                "step_info": "Scraper Agent",
            }
            
        except Exception as e:
            logger.error(f"Scraper agent error: {e}")
            return {
                **state,
                "platform_content": "",
                "platform_summary": f"Error processing platform content: {e}",
                "errors": state.get("errors", []) + [f"Scraper agent error: {e}"],
                "step_info": "Scraper Agent (error)",
            }
    
    return scraper_agent
