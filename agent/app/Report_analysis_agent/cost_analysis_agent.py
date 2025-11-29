import os 
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent
from .tools import calculate_defect_cost_impact, check_material_market_price
from .prompts import COST_ANALYSIS_PROMPT

load_dotenv()

# Model Gemini 
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

# agent = create_deep_agent(
#     system_prompt = COST_ANALYSIS_PROMPT,
#     model = model,
#     tools = [calculate_defect_cost_impact, check_material_market_price]
# )

cost_analysis_agent = {
    "name": "cost-analysis-agent",
    "description": "",
    "system_prompt": COST_ANALYSIS_PROMPT,
    "tools": [calculate_defect_cost_impact, check_material_market_price],
    "model": model
}