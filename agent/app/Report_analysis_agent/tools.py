import os
from langchain_core.tools import tool
from langchain_community.tools.google_finance import GoogleFinanceQueryRun
from langchain_community.utilities.google_finance import GoogleFinanceAPIWrapper


@tool
def calculate_defect_cost_impact(
    batch_size: int,
    defect_rate: float,
    unit_cost: float,
    rework_cost_per_unit: float = 0.0,
    is_scrap: bool = True
) -> str:
    """
    Calculates the financial impact of PCB defects based on production data.
    Args:
        batch_size: Total PCBs in batch.
        defect_rate: Defect rate (0.0 - 1.0).
        unit_cost: Cost per unit.
        rework_cost_per_unit: Cost to repair (if applicable).
        is_scrap: True if scrap (total loss), False if reworkable.
    """
    affected_units = int(batch_size * defect_rate)
    if is_scrap:
        total_loss = affected_units * unit_cost
        action = "SCRAP (Total Loss)"
    else:
        total_loss = affected_units * rework_cost_per_unit
        action = "REWORK"

    return f"Action: {action}, Affected: {affected_units}, Est. Loss: ${total_loss:,.2f}"


@tool
def check_material_market_price(query: str) -> str:
    """
    Checks real-time market prices of PCB raw materials (Copper, Gold, Silver, Tin) using Google Finance.
    
    Args:
        query: The material name or ticker symbol to search (e.g., "Copper price", "Gold price", "LME Copper").
    """
    # ตรวจสอบ API Key
    if not os.environ.get("SERPAPI_API_KEY"):
        return "Error: SERPAPI_API_KEY not found in environment variables."
    
    try:
        # เรียกใช้ Google Finance Tool ของ LangChain
        api_wrapper = GoogleFinanceAPIWrapper()
        tool = GoogleFinanceQueryRun(api_wrapper=api_wrapper)
        
        # รันคำสั่ง
        result = tool.run(query)
        return result
    except Exception as e:
        return f"Error fetching market data: {str(e)}"