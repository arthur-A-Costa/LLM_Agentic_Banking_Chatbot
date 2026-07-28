from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from app.tools.registry import get_salesman_tools, get_specialist_tools
from app.prompts.prompts import salesman_agent_prompt, new_salesman_agent_prompt
from app.llms.ollama import get_salesman_llm

async def create_salesman_agent ():
    llm = get_salesman_llm()
    tools = await get_salesman_tools()
    specialist_tools = await get_specialist_tools()

    return create_agent(
        model = llm,
        tools = specialist_tools,
        system_prompt = new_salesman_agent_prompt,

    )