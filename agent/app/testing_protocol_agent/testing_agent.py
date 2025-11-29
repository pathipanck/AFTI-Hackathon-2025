import os
from dotenv import load_dotenv
from typing_extensions import Annotated, Literal
from langchain import tools
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent
from .tools import tavily_search, think_tool
from .prompts import TESTING_PROTOCOL_PROMPT

load_dotenv()

# Model Gemini
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

# agent = create_deep_agent(
#     system_prompt = TESTING_PROTOCOL_PROMPT,
#     model = model,
#     tools = [tavily_search, think_tool]
# )

test_protocol_agent = {
    "name": "test-protocol-agent",
    "description": "",
    "system_prompt": TESTING_PROTOCOL_PROMPT,
    "tools": [tavily_search, think_tool],
    "model": model,
}


