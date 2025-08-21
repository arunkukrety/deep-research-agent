from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from utils.prompts import SUMMARIZER_PROMPT
import json
import logging

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

def create_summarizer_agent(gemini: ChatGoogleGenerativeAI):
    def summarizer_agent(state: GraphState) -> GraphState:
        try:
            articles = state.get("articles", [])
            original_query = state.get("user_input", "")
            selected_urls = state.get("selected_urls", [])
            reddit_content = state.get("reddit_content", "")
            reddit_summary = state.get("reddit_summary", "")
            
            logger.info(f"Summarizer processing {len(articles)} articles for: {original_query[:100]}...")
            
            # Filter out articles with errors and prepare content
            valid_articles = [a for a in articles if not a.get("error") and a.get("text", "").strip()]
            
            if not valid_articles:
                logger.warning("No valid articles found for summarization")
                error_msg = "No valid articles were found to create a comprehensive report."
                if articles:
                    error_msg += f" ({len(articles)} articles had errors or no content)"
                
                return {
                    **state,
                    "report_markdown": f"# Research Report\n\n**Query:** {original_query}\n\n## Error\n\n{error_msg}\n\n**Errors encountered:**\n" + 
                                   "\n".join(f"- {a.get('error', 'Unknown error')}" for a in articles if a.get("error")),
                    "errors": state.get("errors", []) + ["No valid articles for summarization"],
                    "step_info": "Summarizer (no content)",
                }
            
            # Create sources mapping for citations with URLs
            sources = []
            for i, article in enumerate(valid_articles):
                url = article.get('url', '')
                title = article.get('title', 'Untitled')
                if url and url.startswith(('http://', 'https://')):
                    sources.append(f"{i+1}. {title} - {url}")
                else:
                    sources.append(f"{i+1}. {title} - No URL available")
            
            # Prepare content for the model with article references
            articles_content = []
            for i, article in enumerate(valid_articles):
                article_text = f"[ARTICLE {i+1}]\nTitle: {article.get('title', 'Untitled')}\nURL: {article.get('url', 'No URL')}\nContent: {article.get('text', '')[:12000]}\n"  # Limit per article
                articles_content.append(article_text)
            
            content_for_model = "\n\n".join(articles_content)
            
            # Check if content is too large and needs chunking
            if len(content_for_model) > 80000:  # Conservative token limit
                logger.info("Content too large, using first batch of articles")
                # Use first half of articles to stay within limits
                mid_point = len(valid_articles) // 2
                valid_articles = valid_articles[:max(1, mid_point)]
                sources = sources[:len(valid_articles)]
                
                articles_content = []
                for i, article in enumerate(valid_articles):
                    article_text = f"[ARTICLE {i+1}]\nTitle: {article.get('title', 'Untitled')}\nURL: {article.get('url', 'No URL')}\nContent: {article.get('text', '')[:12000]}\n"
                    articles_content.append(article_text)
                
                content_for_model = "\n\n".join(articles_content)

            # Prepare content including Reddit discussions
            all_content = content_for_model
            
            if reddit_content and reddit_summary:
                all_content += f"\n\nREDDIT DISCUSSIONS:\n{reddit_content[:10000]}\n\nREDDIT SUMMARY:\n{reddit_summary}"
                logger.info("Including Reddit content in final report")
            
            messages = [
                SystemMessage(content=SUMMARIZER_PROMPT),
                HumanMessage(content=f"""Original Query: {original_query}

RESEARCH ARTICLES:
{all_content}

SOURCES FOR CLICKABLE CITATIONS:
{chr(10).join(sources)}

IMPORTANT: Create clickable citations using markdown format [1](url), [2](url), etc. that correspond to the sources above. Only cite important claims, specific data, or direct quotes - limit to 1-3 citations per paragraph.

Create a comprehensive markdown report with proper clickable citations. If Reddit discussions are included, mention community perspectives and insights from Reddit users.""")
            ]
            
            response = gemini.invoke(messages)
            
            # Append sources section to the report with clickable links
            report_with_sources = response.content.strip()
            
            if not report_with_sources.endswith("## Sources"):
                # Create clickable sources list
                clickable_sources = []
                for source in sources:
                    # Extract URL from source line (format: "1. Title - URL")
                    parts = source.split(" - ", 1)
                    if len(parts) == 2 and parts[1].startswith(('http://', 'https://')):
                        title = parts[0].split(". ", 1)[1] if ". " in parts[0] else parts[0]
                        url = parts[1]
                        clickable_sources.append(f"{len(clickable_sources)+1}. [{title}]({url})")
                    else:
                        clickable_sources.append(source)
                
                report_with_sources += f"\n\n## Sources\n\n" + "\n".join(clickable_sources)
            
            logger.info(f"Summarizer completed report generation ({len(report_with_sources)} characters)")
            
            return {
                **state,
                "report_markdown": report_with_sources,
                "step_info": "Summarizer",
            }
            
        except Exception as e:
            logger.error(f"Summarizer error: {e}")
            return {
                **state, 
                "report_markdown": f"# Research Report\n\n**Query:** {state.get('user_input', '')}\n\n## Error\n\nFailed to generate report: {e}",
                "errors": state.get("errors", []) + [f"Summarizer error: {e}"],
                "step_info": "Summarizer (error)"
            }
    
    return summarizer_agent
