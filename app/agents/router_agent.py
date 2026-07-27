from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from typing import Literal
from pydantic import BaseModel, Field
from app.llms.ollama import get_router_llm

class RouterDecision(BaseModel):
    selected_agent: Literal["salesman", "consultant"] = Field(
        description="The agent that should handle the user message."
    )
    reason: str = Field(
        description="Short explanation for the routing decision."
    )

def router_message (message: str) -> RouterDecision:
    llm = get_router_llm().with_structured_output(RouterDecision)

    prompt = f"""
    You are a routing agent for a banking chatbot focused on consortium products.

    Your task is to choose exactly one destination:
    - salesman
    - consultant

    Routing rules:

    1. Route to consultant when the user asks about:
    - suitability
    - affordability
    - whether they should join
    - whether it is worth it
    - risks
    - financial situation
    - income
    - salary
    - debts
    - existing obligations
    - urgency
    - needing the asset immediately
    - comparing consortium with financing
    - investment decision
    - payment capacity
    - monthly payment plus personal income/debt analysis

    Important priority rule:
    If the user asks for product information AND also asks for suitability, affordability, risk, income analysis, debt analysis, or recommendation, route to consultant.

    Examples that must route to consultant:
    - "Can I afford this consortium with my income?"
    - "Is this real estate consortium suitable for me?"
    - "I earn 18,000 and have 4,000 in debt. Should I join?"
    - "Calculate the payment and tell me if it makes sense."
    - "I want a property consortium for investment. Is it worth it?"
    - "I need the car immediately. Is consortium a good idea?"
    - "Compare consortium and financing for my situation."

    2. Route to salesman when the user only asks about:
    - available consortium options
    - product features
    - credit ranges
    - fees
    - terms
    - plan descriptions
    - general explanation of how consortium works
    - showing available automobile, motorcycle, real estate, or services consortium plans

    Examples that must route to salesman:
    - "Show me automobile consortium options."
    - "What real estate consortium plans are available?"
    - "Explain how a consortium works."
    - "What is the admin fee for the standard automobile plan?"
    - "What credit ranges do you offer?"

    Final instruction:
    Return only the structured routing decision. Do not answer the user's question.

    User Message:
    {message}
    """

    return llm.invoke(prompt)