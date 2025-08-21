from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from utils.prompts import QUERY_ENHANCER_PROMPT
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

def create_query_enhancer_agent(llm: ChatGroq):
    def query_enhancer_node(state: GraphState) -> GraphState:
        try:
            logger.info(f"Query enhancer processing: {state['user_input'][:100]}...")
            
            messages = [
                SystemMessage(content=QUERY_ENHANCER_PROMPT),
                HumanMessage(content=f"Original user query (preserve terms verbatim): \"{state['user_input']}\""),
            ]

            response = llm.invoke(messages)
            
            # Parse JSON response
            try:
                parsed = json.loads(response.content.strip())
                enhanced_query = parsed.get("enhanced_query", state["user_input"])
                followup_questions = parsed.get("followup_questions", [])
                
                # Ensure we have at least the original query as a fallback
                if not followup_questions:
                    followup_questions = [enhanced_query or state["user_input"]]
                    
                logger.info(f"Enhanced query: {enhanced_query[:100]}...")
                logger.info(f"Generated {len(followup_questions)} follow-up questions")
                
                return {
                    **state,
                    "enhanced_query": enhanced_query,
                    "followup_questions": followup_questions,
                    "step_info": "Query Enhancer",
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from query enhancer: {e}")
                # Fallback: use original query
                return {
                    **state,
                    "enhanced_query": state["user_input"],
                    "followup_questions": [state["user_input"]],
                    "errors": state.get("errors", []) + [f"Query enhancer JSON parse error: {e}"],
                    "step_info": "Query Enhancer (fallback)",
                }
                
        except Exception as e:
            logger.error(f"Query enhancer error: {e}")
            return {
                **state,
                "enhanced_query": state["user_input"],
                "followup_questions": [state["user_input"]],
                "errors": state.get("errors", []) + [f"Query enhancer error: {e}"],
                "step_info": "Query Enhancer (error)",
            }
    
    return query_enhancer_node
