from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
import re
import json

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    llm_response: str
    step_info: str

def create_planner_agent(serper_search_tool):
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
            
            # search each question and collect results
            raw_results = []
            
            for question in followups[:6]:  # limit to 6 to avoid too many api calls
                search_query = f'"{original_query}" {question}' if original_query else question
                
                try:
                    print(f"searching: {search_query}")
                    search_result = serper_search_tool.invoke({"query": search_query})
                    
                    # extract organic results
                    sources = []
                    organic_match = re.search(r"ORGANIC RESULTS:\n(.*?)(?:\n\nPEOPLE ALSO ASK|$)", search_result, re.DOTALL)
                    if organic_match:
                        organic_section = organic_match.group(1)
                        result_blocks = re.findall(r"(\d+)\. (.+?)\n   URL: (.+?)\n   Snippet: (.+?)(?=\n\d+\.|$)", organic_section, re.DOTALL)
                        for _, title, url, snippet in result_blocks[:3]:  # take first 3
                            sources.append({
                                "question": question,
                                "search_result": f"{title.strip()}: {snippet.strip()}",
                                "source": url.strip()
                            })
                    
                    if not sources:
                        sources.append({
                            "question": question,
                            "search_result": search_result[:500] + "..." if len(search_result) > 500 else search_result,
                            "source": None
                        })
                    
                    raw_results.extend(sources)
                    
                except Exception as search_error:
                    print(f"search error for '{question}': {search_error}")
                    raw_results.append({
                        "question": question,
                        "search_result": f"search error: {str(search_error)}",
                        "source": None
                    })
            
            json_output = json.dumps(raw_results, ensure_ascii=False, indent=2)
            print(f"returning {len(raw_results)} results as json")
            
            return {
                **state,
                "llm_response": json_output,
                "step_info": "Planner Agent (JSON output)",
            }

        except Exception as e:
            print(f"planner error: {e}")
            return {
                **state,
                "llm_response": f"Error: {e}",
                "step_info": "Planner Agent node",
            }
    
    return planner_agent
