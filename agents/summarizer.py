from typing import TypedDict, Annotated
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from utils.prompts import SUMMARIZER_PROMPT

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    llm_response: str
    step_info: str

def create_summarizer_agent(gemini: ChatGoogleGenerativeAI):
    def summarizer_agent(state: GraphState) -> GraphState:
        # takes raw json data and makes a nice professional report
        try:
            raw_json_data = state["llm_response"]
            original_query = state.get("user_input", "")
            
            print(f"summarizer processing json data: {raw_json_data[:200]}...")
            
            messages = [
                SystemMessage(content=SUMMARIZER_PROMPT),
                HumanMessage(content=f"Original Query: {original_query}\n\nRAW_RESEARCH_DATA:\n{raw_json_data}")
            ]
            
            response = gemini.invoke(messages)
            
            return {
                **state,
                "llm_response": response.content,
                "step_info": "Summarizer Agent (Gemini)",
            }
            
        except Exception as e:
            print(f"summarizer error: {e}")
            return {**state, "llm_response": f"Error: {e}", "step_info": "Summarizer Agent"}
    
    return summarizer_agent
