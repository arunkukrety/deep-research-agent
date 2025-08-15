from typing import TypedDict, Annotated
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from utils.prompts import QUERY_ENHANCER_PROMPT

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    llm_response: str
    step_info: str

def create_query_enhancer_agent(llm: ChatGroq):
    def query_enhancer_node(state: GraphState) -> GraphState:
        # takes user query and makes it better for research
        messages = [
            SystemMessage(content=QUERY_ENHANCER_PROMPT),
            HumanMessage(content=f"Original user query (preserve terms verbatim): \"{state['user_input']}\""),
        ]

        response = llm.invoke(messages)

        return {
            **state,
            "llm_response": response.content,
            "step_info": "Query Enhancer node",
        }
    
    return query_enhancer_node
