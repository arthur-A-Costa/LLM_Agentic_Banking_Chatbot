from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from app.tools.registry import get_consultant_tools, get_specialist_tools
from app.prompts.prompts import consultant_agent_prompt, new_consultant_agent_prompt
from app.llms.ollama import get_consultant_llm 

async def create_consultant_agent ():
    llm = get_consultant_llm()
    tools = await get_consultant_tools()
    specialist_tools = await get_specialist_tools()

    return create_agent(
        model = llm,
        tools = specialist_tools,
        system_prompt = new_consultant_agent_prompt,
    )