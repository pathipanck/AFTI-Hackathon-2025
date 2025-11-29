"""Testing Protocol Tools.

This module provides external search and strategic planning utilities 
for the Testing Protocol Agent, using Tavily for external context discovery
and internal reflection for quality assurance planning.
"""
import os
import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool
from markdownify import markdownify
from tavily import TavilyClient
from typing import Literal

load_dotenv()

# Initialize Tavily Client
# ตรวจสอบให้แน่ใจว่าได้ set env TAVILY_API_KEY แล้ว หรือใส่ key ตรงนี้ (ไม่แนะนำสำหรับ prod)
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch and convert webpage content to markdown.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Webpage content as markdown or error message
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        # แปลง HTML เป็น Markdown เพื่อให้อ่านง่ายและประหยัด Token
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching content from {url}: {str(e)}"


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> str:
    """Search the web for supplementary external context, emerging best practices, 
    or industry news related to PCB testing and standards compliance.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.
    This tool should be used for information not available in internal QA documents.

    Args:
        query: Search query to execute.
        max_results: Maximum number of results to return (default: 5).
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general').

    Returns:
        Formatted search results with full webpage content.
    """
    try:
        # Use Tavily to discover URLs
        search_results = tavily_client.search(
            query,
            max_results=max_results,
            topic=topic,
        )
    except Exception as e:
        return f"Error connecting to search engine: {str(e)}"

    result_texts = []
    
    # Loop through results safely using .get()
    for result in search_results.get("results", []):
        url = result.get("url")
        title = result.get("title", "No Title")

        if url:
            # Fetch webpage content
            content = fetch_webpage_content(url)

            result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
            result_texts.append(result_text)

    # Handle case where no results are found
    if not result_texts:
        return f"No results found for query: '{query}'."

    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}' (External Context):

{chr(10).join(result_texts)}"""

    return response


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on testing protocol design and decision-making.

    Use this tool after each step (e.g., after finding IPC standards or searching external context) 
    to analyze findings, assess gaps, and plan the next mandatory testing steps systematically.
    This ensures quality and completeness in the final testing protocol.

    Reflection should address:
    1. Analysis of current findings - What mandatory standards (IPC) or external best practices have I gathered?
    2. Gap assessment - What crucial testing steps or compliance checks are still missing?
    3. Quality evaluation - Is the current protocol robust enough for the PCB class?
    4. Strategic decision - Should I use RAG, use external search, or finalize the protocol?

    Args:
        reflection: Your detailed reflection on protocol progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for strategic decision-making
    """
    return f"Reflection recorded for Protocol Agent: {reflection}"