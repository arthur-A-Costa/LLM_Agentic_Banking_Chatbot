from typing import Literal
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from app.tools.registry import get_collector_tools
from app.llms.ollama import get_collector_llm 

SearchTools = Literal["search_consortium_products", "search_consortium_documents", "search_public_web"]
SpecialistTools = Literal["simulate_consortium_payment", "check_consortium_affordability", "check_consortium_suitability", "consortium_installment_simulation",]
ConsortiumTypes = Literal["automobile", "motorcycle", "real estate", "services", "unknown"]

class ToolRequest(BaseModel):
    tool_name: str
    reasoning: str
    query: str | None = None
    consortium_type: ConsortiumTypes = "unknown"

class ToolPlanner(BaseModel):
    requires_collection: bool
    required_tools: list[ToolRequest] = Field(default_factory=list)
    consortium_type: ConsortiumTypes = "unknown"
    answer_requirements: list[str]
    required_specialist_tools: list[SpecialistTools] = []

class ConsortiumEvidence(BaseModel):
    product_name: str
    consortium_type: str
    credit_range: str | None = None
    admin_fee: str | None = None
    reserve_fund: str | None = None
    minimum_income: str | None = None
    max_term: str | None = None
    average_monthly_payment: str | None = None
    contemplation_method: str | None = None
    risk_level: str | None = None
    notes: str | None = None

class ToolInformation(BaseModel):
    relevant_web_search_data: str | None=None
    relevant_consortium_database_data: list[ConsortiumEvidence] = Field(default_factory=list)
    relevant_document_data: str | None = None

def planner_creator(message: str) -> ToolPlanner:
    llm = get_collector_llm().with_structured_output(ToolPlanner)

    collector_prompt = f"""
            You are a evidence planner agent, specialized in deciding what tools must be used to gather resources and information for other agents.

            When receiving a query you should evaluate it and decide what tools must be called to gather all necessary information for the next agent to be able to 
            accurately answer the user's query to completion.

            - List of Available Tools -
                Search tools:
                    - search_consortium_products: search the consortium database for information regarding consortium options and details.
                    - search_consortium_documents: search vector database for documents to answer consortium related questions.
                    - search_public_web: search the web to answer questions regarding current values, rates and external information.
                    
            - Tool Guidelines and Examples -

            1 - search_consortium_products:
            Gives access to database information and data regarding the available consortium options. This tools should be used when the user asks
            about what consortium options are available, better fit a scenario, what are the specifics of a certain consortium, and to get standard/default data
            for user requested simulations.
                Examples of prompts:
                - What consortium options are available?
                - What consortium should I look into if I want to buy a house?
                - What is the maximum credit amount I can get with a automobile consortium?  
                - Considering x credit amount and x months, how much would be my monthly payment in standard automobile consortium? 

            2 - search_consortium_documents:
            Gives access to the vector database with consortium documents, FAQs, manuals, policies, and guidelines.
            This tool should be used to answer questions regarding how consortiums work, specefic policies, and what happens in specific scenarios.
                Examples of prompts:
                - how consortiums work
                - contemplation rules
                - bid offers
            
            3 - search_public_web:
            Gives access to the public web. This tool should be used to search for current and up to date values, prices, rates, or news.
                Examples of prompts:
                - current selic rate.
                - current conversion value of dolar($) to real(R$).
                - current average of a 2026 BMW X3.

            CRUCIAL GUIDELINES:
            - Based on the user's query decide what search tools must be called.
            - Plan the use of all tools necessary to completely answer the user's question.
            - Never infer or guess information unless it is absolutely necessary, and if necessary always utilize the most up-to-date year (2026) or popular model.

            WHEN CREATING THE PLANNER:
            - For each necessary tool create a tool request where you name the tool and give the necessary arguments, and add this request to the required_tools field.
            - In the tool planner list which specialist tools the next agent might need call to completely answer the user's question.
            - When defining the consortium type of the tool/planner answer unknown if you cannot identify the specific type referenced or
              if information from more than one type is needed. 
            - In the answer_requirements field add only what must be answered by the next agent, not what tool should or were used.
            
            User's Message:
            {message}
    """

    try:
        return llm.invoke(collector_prompt)

    except Exception as error:
        print(f"Evidence planner failed: {error}", flush=True)

        return ToolPlanner(
            requires_collection=False,
            required_tools=[],
            consortium_type="unknown",
            task_type="general_question",
            answer_requirements=[],
            required_specialist_tools=[],
        )
    
def context_creator(results: dict) -> str:
    formatted = []
    for tool, evidence in results.items():

        formatted.append(
             f"TOOL NAME: {tool}\n"
             f"STATUS: {evidence.get("status")}\n"
             f"REASONING: {evidence.get("reasoning")}\n"
             f"ARGUMENTS: {evidence.get("arguments")}\n"
             f"RESULT: {evidence.get("tool_result")}\n"
             f"ERROR: {evidence.get("error")}\n"
        )

    return "\n\n---\n\n".join(formatted)

async def planner_executor(planner: ToolPlanner, user_message: str) -> dict:
    tool_results = {}
    used_tools = []

    if not planner.requires_collection:
        return {
            "used_tools": [],
            "tool_results": {}
        }
    
    # Resquest structure
    # class ToolRequest(BaseModel):
    #     tool_name: str
    #     reasoning: str
    #     query: str | None = None
    #     consortium_type: ConsortiumTypes = None

    # Planner structure
    # class ToolPlanner(BaseModel):
    #     requires_collection: bool
    #     required_tools: list[ToolRequest]
    #     consortium_type: ConsortiumTypes = None
    #     answer_requirements: list[str]
    #     required_specialist_tools: list[SpecialistTools] = []

    # Tools to be checked for
    # ["search_consortium_products", "search_consortium_documents", "search_public_web"]

    mcp_tools = await get_collector_tools()

    for request in planner.required_tools:
        tool_name = request.tool_name
        evidence_record = {
            "status": "pending",
            "reasoning": request.reasoning,
            "arguments": {},
            "tool_result": None,
        }

        try:
            if tool_name == "search_consortium_products":
                consortium_type = request.consortium_type

                if (consortium_type.lower() == "unknown"):
                    consortium_type = planner.consortium_type

                if (consortium_type.lower() == "unknown"):
                    consortium_type = None    

                args = {
                    "consortium_type": consortium_type
                }

                result = await mcp_tools["search_consortium_products"].ainvoke(args)

            elif tool_name == "search_consortium_documents":
                query = request.query

                args = {
                    "query": query or user_message
                }

                result = await mcp_tools["search_consortium_documents"].ainvoke(args)

            elif tool_name == "search_public_web":
                query = request.query

                args = {
                    "query": query or user_message
                }

                result = await mcp_tools["search_public_web"].ainvoke(args)
            
            else:
                raise ValueError(f"Not Supported Tool: {tool_name}")
            
            evidence_record["status"] = "success"
            evidence_record["arguments"] = args
            evidence_record["tool_result"] = result
            used_tools.append(tool_name)
            
        except Exception as error:
            evidence_record["status"] = "error"
            evidence_record["error"] = error

        tool_results[tool_name] = evidence_record

    return {
        "used_tools": used_tools,
        "tool_results": tool_results,
        "tool_context": context_creator(tool_results),
        "answer_requirements": planner.answer_requirements,
        #"clean_evidence": relevant_data_extractor(tool_results)
        #"required_specialist_tools": planner.required_specialist_tools
    }

# class ToolInformation(BaseModel):
#     relevant_web_search_data: str | None=None
#     relevant_consortium_database_data: list[ConsortiumEvidence] = Field(default_factory=list)
#     relevant_document_data: str | None = None

# class ConsortiumEvidence(BaseModel):
#     product_name: str
#     consortium_type: str
#     credit_range: str | None = None
#     admin_fee: str | None = None
#     reserve_fund: str | None = None
#     minimum_income: str | None = None
#     max_term: str | None = None
#     average_monthly_payment: str | None = None
#     contemplation_method: str | None = None
#     risk_level: str | None = None
#     notes: str | None = None

def information_extractor(tool_results: dict, message: str, answer_requirements: list, used_tools: list):
    llm = get_collector_llm().with_structured_output(ToolInformation)

    prompt = f"""
        You are an evidence extraction and normalization agent for a banking chatbot specialized in consortium products.

        Your job is to read raw tool results and transform them into a clean, structured evidence brief that can be used by the next agent.

        You must NOT answer the final user.
        You must NOT make final recommendations.
        You must NOT add information that is not present in the tool results.

        Objective:
        - Extract only the essential information needed to answer the user's question.
        - Disconsider noise such as menus, cookie notices, website navigation, HTML fragments, duplicated content, irrelevant IDs, and unrelated text.
        - Preserve numeric values exactly as they appear in the evidence.
        - Preserve product names, years, prices, fees, terms, credit ranges, minimum income requirements, and URLs when available.
        - Organize the information clearly for the consultant or sales agent.

        Mandatory rules:
        - Do not invent prices, years, fees, terms, credit ranges, minimum income requirements, requirements, or product names.
        - Do not use the model's own knowledge.
        - Use only information present in the tool results.
        - If internal bank product information is present, preserve the essential product details.
        - If irrelevant data appears, remove it or place it under "Removed irrelevant data".
        - Do not mention tool calls, raw JSON, LangChain internal IDs, or implementation details.
        - The output must be in English.

        User Message:
        {message}

        Answer requirements defined by the planner:
        {answer_requirements}

        Tools used:
        {used_tools}

        Raw tool results:
        {tool_results}

        Respond with the following structure:

        ## Relevent web search data:
        Fill this field with any information from the web search that is crucial for the next agent to answer the user's question. 

        ## Relevant internal consortium products:
        List only the internal products relevant to the user's question.
        - For each product, include:
            - Product name
            - Consortium type
            - Credit range
            - Administration fee
            - Reserve fund
            - Minimum income
            - Maximum term
            - Estimated average monthly payment
            - Contemplation method
            - Risk level

        - Be aware that these are all of the consortium categories available:
            - real estate
            - automobile
            - motorcycle
            - services

        ## Relevent consortium document data:
        Fill this field with any information from the internal documents that is crucial for the next agent to answer the user's question. 

        If any of these tools were not called or come empty leave their field in the outpit empty.
    """

    try:
        return llm.invoke(prompt)

    except Exception as error:
        print(f"Data Extractor failed: {error}", flush=True)

        return ToolInformation(
            relevant_web_search_data= "",
            relevant_document_data= "",
            relevant_consortium_database_data= []
        )