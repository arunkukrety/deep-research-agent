from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

def init_groq(model: str = "openai/gpt-oss-120b", temperature: float = 0.7):
    # init groq llm for fast research
    return ChatGroq(
        model=model,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

def init_gemini(model: str = "gemini-2.5-flash", temperature: float = 0.7):
    # init gemini for final report writing
    return ChatGoogleGenerativeAI(
        model=model,
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
