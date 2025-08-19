from typing import TypedDict, Annotated
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
    # create react agent with search and crawl tools
    serper_search_tool, exa_crawl_urls = search_tools
    react_agent = create_react_agent(
        model=llm,
        tools=[serper_search_tool, exa_crawl_urls],
        state_modifier="""You are an intelligent research agent. Follow this workflow:

1. Search each question ONE BY ONE using serper_search_tool
2. After ALL searches are complete, analyze all the URLs you found
3. Select 3-6 best URLs that provide comprehensive coverage
4. Use exa_crawl_urls ONCE with your selected URLs

IMPORTANT RULES:
- Call tools ONE AT A TIME, never multiple tools in parallel
- Wait for each search to complete before moving to the next
- Only use exa_crawl_urls ONCE at the end with your best URLs
- Be selective - choose quality sources over quantity

SELECTION CRITERIA:
- Authoritative sources (official docs, reputable sites)
- Unique information (avoid duplicates)
- Comprehensive topic coverage
- Relevance to the original query"""
    )
    
    def planner_agent(state: GraphState) -> GraphState:
        try:
            enhanced_text = state["llm_response"]
            original_query = state.get("user_input", "")
            
            print(f"planner processing: {enhanced_text[:200]}...")
            
            # extract follow-up questions from enhanced query
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
            
            # create research prompt for react agent
            research_prompt = f"""
Research these questions about "{original_query}":

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(followups[:6]))}

WORKFLOW:
1. Search question 1 with serper_search_tool
2. Search question 2 with serper_search_tool  
3. Continue until all questions are searched
4. After all searches, review all URLs found
5. Select 3-6 best URLs for comprehensive coverage
6. Use exa_crawl_urls with your selected URLs

CRITICAL:
- Search questions ONE BY ONE (don't try to search multiple at once)
- Only call exa_crawl_urls ONCE at the very end
- Choose URLs that complement each other, avoid duplicates
- Prioritize authoritative sources

Start with question 1 now.
"""
            
            # invoke react agent
            messages = [HumanMessage(content=research_prompt)]
            response = react_agent.invoke({"messages": messages})
            
            # removed duplicate logging - tools already print when they execute
            
            # extract final response from agent
            final_message = response["messages"][-1].content
            
            # try to extract json from response
            json_match = re.search(r'\[.*\]', final_message, re.DOTALL)
            if json_match:
                json_output = json_match.group(0)
            else:
                # fallback: create simple json from response
                json_output = json.dumps([{
                    "question": original_query,
                    "search_result": final_message,
                    "source": None
                }], ensure_ascii=False, indent=2)
            
            print(f"planner completed research")
            
            return {
                **state,
                "llm_response": json_output,
                "step_info": "Planner Agent (React with tools)",
            }

        except Exception as e:
            print(f"planner error: {e}")
            return {
                **state,
                "llm_response": f"Error: {e}",
                "step_info": "Planner Agent error",
            }
    
    return planner_agent
