from typing import Literal, TypedDict, Annotated
import uuid
from pydantic import BaseModel

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AnyMessage, AIMessage

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from app.utils.router import route_message
from app.agents.salesman_agent import create_salesman_agent
from app.agents.consultant_agent import create_consultant_agent
from app.agents.router_agent import router_message
from app.agents.reviewer_agent import create_reviewer_agent
from app.agents.editor_agent import create_editor_agent
from app.agents.collector_agent import planner_creator, planner_executor, information_extractor

import os

ENABLE_REVIEW_AGENT = os.getenv("ENABLE_REVIEW_AGENT", "true").lower() == "true"
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres_user:postgres_password@postgres:5432/postgres")

# Creation of the class that works as the state - memory of the AI application
class ChatGraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    selected_agent: str
    router_reason: str
    draft_response: str
    response: str
    used_tools: list[str]
    tool_results: dict
    tool_context: str
    answer_requirements: list[str]
    db_data: str
    doc_data: str
    web_data: str
    review_action: str
    review_text: list[str]

# Can be used in the future for structured review responses
class ReviewResult(BaseModel):
    passed: bool
    severity: Literal["none", "minor", "major"]
    issues: list[str]
    recommended_action: Literal["return", "edit", "redo"]

# salesmas_agent = create_salesman_agent()
# consultant_agent = create_consultant_agent()
# reviewer_agent = create_reviewer_agent()

def get_latest_user_message(state: ChatGraphState) -> str:
    for message in reversed(state["messages"]):
        if message.type == "human":
            return message.content
    return ""

def router_node(state: ChatGraphState) -> ChatGraphState:
    latest_message = get_latest_user_message(state)
    
    decision = router_message(latest_message)

    return{
        **state,
        "selected_agent": decision.selected_agent,
        "router_reason": decision.reason, 
    }

def choose_next_node(
    state: ChatGraphState,
) -> Literal["salesman", "consultant", "human_support"]:
    selected_agent = state["selected_agent"]

    #if selected_agent == "human_support":
    #    return "human_support"

    if selected_agent == "salesman":
        return "salesman"

    return "consultant"

async def collector_node(state: ChatGraphState) -> ChatGraphState:
    latest_message = get_latest_user_message(state)
    planner = planner_creator(latest_message)
    evidence = await planner_executor(planner, latest_message)
    results = evidence["tool_context"]
    requirements = evidence["answer_requirements"]
    used_tools = evidence["used_tools"]
    clean_evidence = information_extractor(tool_results=results, message=latest_message, answer_requirements=requirements, used_tools=used_tools)

    return {
        "db_data": clean_evidence.relevant_consortium_database_data,
        "doc_data": clean_evidence.relevant_document_data,
        "web_data": clean_evidence.relevant_web_search_data,
        "answer_requirements": requirements,
        "tool_context": results,
        "used_tools": used_tools
    }

async def salesman_node(state: ChatGraphState) -> ChatGraphState:
    messages = state["messages"]
    evidence = state["tool_context"]
    used_tools = state["used_tools"]
    db_data = state["db_data"]
    doc_data = state["doc_data"]
    web_data = state["web_data"]
    latest_message = get_latest_user_message(state)
    answer_requirements = state["answer_requirements"]
    
    salesman_agent = await create_salesman_agent()
    result = await salesman_agent.ainvoke(
        {
              "messages": [
                  {
                      "role": "user",
                      "content": (
                            "You are the salesman agent."
                            "All the necessary evidence from the searching tools has already been collected for you.\n"
                            "Utilize the evidence already collected as you only source of truth, and analyze the user's last message "
                            "to create an answer that completely answers the prompt. Each tool's output will be shown separately."
                            "Utilize the answer requiremens section to understand what you must add in your final output and what information "
                            "you must extract from the evidence collected.\n"
                            "You have access to simulation tools that you can use in case the user requests simulated information, "
                            "calculations, or evaluations. Utilize both consortium database data and user given data for the simulations.\n"
                            "Guidelines:\n"
                            "- Do not use or create any information that is not in the evidence you receive.\n"
                            "- Do not use model memory for facts covered by the evidence.\n"
                            "- Do not mention years, prices, fees, or plans that are not present in the evidence.\n"
                            f"User message: \n{latest_message}\n\n"
                            f"Used tools: \n{used_tools}\n\n"
                            f"Answer requirements: \n{answer_requirements}\n\n"
                            "Evidence collected: \n"
                            f"Database search data: \n{db_data}\n\n"
                            f"Web search data: \n{web_data}\n\n"
                            f"Document search data: \n{doc_data}\n\n"
                            "Write a complete answer in the same language as the prompt."
                      )
                  }
              ]
        }
    )

    final_message = result["messages"][-1].content

    return {
         "messages": [AIMessage(content=final_message)],
         "draft_response": final_message,
         "response": final_message
    }

async def consultant_node(state: ChatGraphState) -> ChatGraphState:
    messages = state["messages"]
    evidence = state["tool_context"]
    used_tools = state["used_tools"]
    db_data = state["db_data"]
    doc_data = state["doc_data"]
    web_data = state["web_data"]
    latest_message = get_latest_user_message(state)
    answer_requirements = state["answer_requirements"]
    
    consultant_agent = await create_consultant_agent()
    result = await consultant_agent.ainvoke(
        {
              "messages": [
                  {
                      "role": "user",
                      "content": (
                          "You are the consultant agent."
                          "All the necessary evidence from the searching tools has already been collected for you.\n"
                          "Utilize the evidence already collected as you only source of truth, and analyze the user's last message "
                          "to create an answer that completely answers the prompt."
                          "Utilize the answer requiremens section to understand what you must add in your final output and what information "
                          "you must extract from the evidence collected.\n"
                          "You have access to simulation tools that you can use in case the user requests simulated information, "
                          "calculations, or evaluations. Utilize both consortium database data and user given data for the simulations.\n"
                          "Guidelines:\n"
                          "- Do not use or create any information that is not in the evidence you receive.\n"
                          "- Do not use model memory for facts covered by the evidence.\n"
                          "- Do not mention years, prices, fees, or plans that are not present in the evidence.\n"
                          f"User message: \n{latest_message}\n\n"
                          f"Used tools: \n{used_tools}\n\n"
                          f"Answer requirements: \n{answer_requirements}\n\n"
                          "Evidence Collected: \n"
                          f"Database search data: \n{db_data}\n\n"
                          f"Web search data: \n{web_data}\n\n"
                          f"Document search data: \n{doc_data}\n\n"
                          "Write a complete answer in the same language as the prompt."
                      )
                  }
              ]
        }
    )

    final_message = result["messages"][-1].content

    return {
         "messages": [AIMessage(content=final_message)],
         "draft_response": final_message,
         "response": final_message
    }

async def reviewer_node(state: ChatGraphState) -> ChatGraphState:
    draft_response = state["draft_response"]
    latest_user_message = get_latest_user_message(state)

    reviewer_agent = await create_reviewer_agent()
    # "Return structured output in the form of Json that utilizes the following values (following the respective data type):\n"
    result = await reviewer_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Review and analyze the following draft answer before it is shown "
                        "to the customer and make sure it completely answers the users last message "
                        "and contains no gramatical mistakes or other issues.\n\n"
                        "Return one of the following actions:\n"
                        "- return\n"
                        "- edit\n"
                        "Choose 'return' if the answer is acceptable and meets all requirements\n"
                        "Choose 'edit' in cases such as:\n"
                        "- The text is not in the same language as the question\n"
                        "- The grammar or formatting is poor or incorrect\n"
                        "- The answer needs to be refined or made clearer\n"
                        "- The response cites internal functions, product codes, or other information that should be hidden from the public\n\n"
                        f"Last user message:\n{latest_user_message}\n\n"
                        f"Draft answer:\n{draft_response}\n\n"
                        "Response Format:\n"
                        "passed: <True or False>\n"
                        "severity: <none , minor, medium, major> based on amount of errors and issues\n"
                        "issues:  <short list of issues or none>\n"
                        "recommended_action: <return or edit>"
                    ),
                }
            ]
        }
    )

    reviewer_message = result["messages"][-1].content.strip()
    lower = reviewer_message.lower()
    if "recommended_action: edit" in lower:
        review_action = "edit"
    else:
        review_action = "return"

    return {
        "review_action": review_action,
        "review_text": [reviewer_message],
    }

def review_decision_node(state):
    review = state["review_action"]

    if review == "return":
        return "final"

    if review == "edit":
        return "editor"

    #if review.recommended_action == "redo" and state["redo_count"] < 1:
    #    return "redo_specialist"

    return "final"

async def editor_node(state: ChatGraphState) -> ChatGraphState:
    draft_response = state["draft_response"]
    latest_user_message = get_latest_user_message(state)
    review_issues = state["review_text"]

    editor_agent = await create_editor_agent()
    result = await editor_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Edit and reformat the following draft answer before it is shown "
                        "to the customer.\n"
                        "Follow the issues found by the reviwer as a guideline of possible issues to fix\n\n"
                        "User question:\n"
                        f"{latest_user_message}\n\n"
                        "Reviewer issues:\n"
                        f"{review_issues}\n\n"
                        "Draft answer:\n"
                        f"{draft_response}"
                    ),
                }
            ]
        }
    )

    edited_message = result["messages"][-1]
    edited_text = edited_message.content

    return {
         "messages": [AIMessage(content=edited_text)],
         "response": edited_text,
    }

def final_response_node(state: ChatGraphState) -> dict:
    return {
        "response": state["draft_response"]
    }

# Function that builds the graph - framework that defines the order in which agents/nodes are executed 
def build_graph(checkpointer):
    agent_builder = StateGraph(ChatGraphState)

    agent_builder.add_node("router", router_node)
    agent_builder.add_node("salesman", salesman_node)
    agent_builder.add_node("consultant", consultant_node)
    agent_builder.add_node("reviewer", reviewer_node)
    agent_builder.add_node("editor", editor_node)
    agent_builder.add_node("final_response", final_response_node)
    agent_builder.add_node("evidence_collector", collector_node)

    agent_builder.add_edge(START, "router")
    agent_builder.add_edge("router", "evidence_collector")
    agent_builder.add_conditional_edges(
        "evidence_collector",
        choose_next_node,
        {
            "salesman": "salesman",
            "consultant": "consultant"
        },
    )
    if ENABLE_REVIEW_AGENT:
        agent_builder.add_edge("salesman", "reviewer")
        agent_builder.add_edge("consultant", "reviewer")
        agent_builder.add_conditional_edges(
            "reviewer", 
            review_decision_node,
            {
                "final": "final_response",
                "editor": "editor",
            }
        )
        agent_builder.add_edge("final_response", END)
        agent_builder.add_edge("editor", END)

    else:
        agent_builder.add_edge("salesman", END)
        agent_builder.add_edge("consultant", END)

    return agent_builder.compile(checkpointer=checkpointer)

async def create_chat_graph(postgres_pool: AsyncConnectionPool):

    checkpointer = AsyncPostgresSaver(postgres_pool)
    await checkpointer.setup()

    chat_graph = build_graph(checkpointer=checkpointer)
    return chat_graph, postgres_pool