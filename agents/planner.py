from typing import TypedDict, Annotated, List, Dict
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
import re
import json

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    llm_response: str
    step_info: str

def create_planner_agent(search_tools, llm):
    # react for url selection, exa crawling outside llm
    serper_search_tool, exa_crawl_tool = search_tools[0], search_tools[1]
    react_agent = create_react_agent(
        model=llm,
        tools=[serper_search_tool],
        state_modifier="""You are an intelligent research agent. Your task is to search for information and intelligently select the best URLs for deep content analysis.

WORKFLOW:
1. Search each research question ONE BY ONE using serper_search_tool
2. After ALL searches are complete, analyze all the URLs you found
3. Select 6-8 best URLs that provide comprehensive coverage
4. Output your selected URLs in JSON format

IMPORTANT RULES:
- Call serper_search_tool ONE AT A TIME for each question
- Wait for each search to complete before moving to the next
- Do NOT call any other tools - content crawling will be done separately
- Be selective - choose quality sources over quantity

SELECTION CRITERIA:
- Authoritative sources (official docs, reputable sites, academic papers)
- Unique information (avoid duplicates)
- Comprehensive topic coverage
- Relevance to the original query
- Diverse perspectives and viewpoints

OUTPUT FORMAT (at the end):
{
  "selected_urls": ["https://example.com/article1", "https://example.com/article2", "..."],
  "reasoning": "Brief explanation of why these URLs were selected"
}"""
    )
    
    def planner_agent(state: GraphState) -> GraphState:
        try:
            enhanced_text = state["llm_response"]
            original_query = state.get("user_input", "")
            
            print(f"planner processing: {enhanced_text[:200]}...")
            
            # extract follow-up questions
            followups = []
            followup_match = re.search(r"FOLLOW-UP QUESTIONS[^:]*:(.*?)(?:\n\n|CLARIFICATION QUESTIONS|$)", enhanced_text, re.DOTALL)
            if followup_match:
                block = followup_match.group(1)
                for line in block.splitlines():
                    line = line.strip()
                    if re.match(r"^\d+\.", line):
                        question = re.sub(r"^\d+\.\s*", "", line).strip()
                        if question:
                            followups.append(question)
            
            if not followups:
                followups = [original_query or enhanced_text[:200]]
            
            print(f"found {len(followups)} follow-up questions")
            
            # create research prompt
            research_prompt = f"""
Research these questions about "{original_query}":

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(followups[:6]))}

WORKFLOW:
1. Search question 1 with serper_search_tool
2. Search question 2 with serper_search_tool  
3. Continue until all questions are searched
4. After all searches, analyze all URLs found
5. Select 6-8 best URLs for comprehensive coverage
6. Output selected URLs in JSON format

CRITICAL:
- Search questions ONE BY ONE (don't try to search multiple at once)
- Do NOT call any other tools besides serper_search_tool
- Choose URLs that complement each other, avoid duplicates
- Prioritize authoritative sources
- End with JSON: {{"selected_urls": ["url1", "url2", ...], "reasoning": "why these URLs"}}

Start with question 1 now.
"""
            
            # run react agent
            messages = [HumanMessage(content=research_prompt)]
            response = react_agent.invoke({"messages": messages})
            
            # extract urls from response
            final_message = response["messages"][-1].content
            urls: List[str] = []
            try:
                # extract json with urls
                json_match = re.search(r'\{[\s\S]*?"selected_urls"[\s\S]*?\}', final_message)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if isinstance(parsed.get("selected_urls"), list):
                        urls = [u for u in parsed["selected_urls"] if isinstance(u, str)]
            except Exception:
                pass

            if not urls:
                # fallback: find urls in text
                urls = re.findall(r"https?://\S+", final_message)
                urls = urls[:8]

            # crawl content with exa
            articles = []
            if urls:
                try:
                    crawl_result_str = exa_crawl_tool.invoke({
                        "urls": urls[:8],
                        "max_urls": 8,
                        "max_chars_per_article": 15000,
                        "max_total_chars": 100000,
                    })
                    crawl_json = json.loads(crawl_result_str) if isinstance(crawl_result_str, str) else {}
                    articles = crawl_json.get("articles", []) or []
                except Exception as crawl_err:
                    articles.append({"error": f"Exa crawl failed: {crawl_err}"})

            output_payload = {
                "query": original_query,
                "selected_urls": urls,
                "articles": articles,
            }

            print(f"planner completed research")

            return {
                **state,
                "llm_response": json.dumps(output_payload, ensure_ascii=False),
                "step_info": "planner agent",
            }

        except Exception as e:
            print(f"planner error: {e}")
            return {
                **state,
                "llm_response": f"Error: {e}",
                "step_info": "planner error",
            }
    
    return planner_agent
