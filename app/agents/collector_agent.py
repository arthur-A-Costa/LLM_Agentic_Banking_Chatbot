from typing import Literal
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from app.tools.registry import get_collector_tools
from app.llms.ollama import get_collector_llm 
from app.utils.evidence_extractor import relevant_data_extractor

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

def planner_creator(message: str) -> ToolPlanner:
    llm = get_collector_llm().with_structured_output(ToolPlanner)

    portuguese_collector_prompt = f"""
            Você é um agente planejador de evidências, especializado em decidir quais ferramentas devem ser usadas para coletar recursos e informações para outros agentes.

            Ao receber uma pergunta, você deve avaliá-la e decidir quais ferramentas precisam ser chamadas para coletar todas as informações necessárias para que o próximo agente consiga
            responder à solicitação do usuário com precisão e completude.

            - Lista de Ferramentas Disponíveis -
                Ferramentas de busca:
                    - search_consortium_products: busca no banco de dados de consórcios informações sobre opções e detalhes dos consórcios.
                    - search_consortium_documents: busca no banco vetorial documentos para responder perguntas relacionadas a consórcios.
                    - search_public_web: busca na web para responder perguntas sobre valores atuais, taxas e informações externas.
                    
            - Diretrizes e Exemplos de Uso das Ferramentas -

            1 - search_consortium_products:
            Dá acesso a informações e dados do banco de dados sobre as opções de consórcio disponíveis. Esta ferramenta deve ser usada quando o usuário perguntar
            quais opções de consórcio estão disponíveis, qual opção se encaixa melhor em um cenário, ou quais são os detalhes de um determinado consórcio.
                Exemplos de perguntas:
                - Quais opções de consórcio estão disponíveis?
                - Qual consórcio devo considerar se quero comprar uma casa?
                - Qual é o valor máximo de crédito que posso obter em um consórcio de automóvel?

            2 - search_consortium_documents:
            Dá acesso ao banco vetorial com documentos, FAQs, manuais, políticas e diretrizes sobre consórcios.
            Esta ferramenta deve ser usada para responder perguntas sobre como consórcios funcionam, políticas específicas e o que acontece em cenários específicos.
                Exemplos de perguntas:
                - como funcionam os consórcios
                - regras de contemplação
                - ofertas de lance
            
            3 - search_public_web:
            Dá acesso à web pública. Esta ferramenta deve ser usada para buscar valores, preços, taxas ou notícias atuais e atualizadas.
                Exemplos de perguntas:
                - taxa Selic atual
                - cotação atual do dólar em reais
                - preço médio atual de uma BMW X3 2026

            DIRETRIZES CRUCIAIS:
            - Com base na pergunta do usuário, decida quais ferramentas de busca devem ser chamadas.
            - Planeje o uso de todas as ferramentas necessárias para responder completamente à pergunta do usuário.
            - Nunca deduza ou chute informações, a menos que seja absolutamente necessário; se for necessário, utilize sempre o ano mais atualizado (2026) ou o modelo mais popular.

            AO CRIAR O PLANEJAMENTO:
            - Para cada ferramenta necessária, crie uma solicitação de ferramenta informando o nome da ferramenta e os argumentos necessários, e adicione essa solicitação ao campo required_tools.
            - No planejamento, liste quais ferramentas especializadas o próximo agente talvez precise chamar para responder completamente à pergunta do usuário.
            - Ao definir o tipo de consórcio da ferramenta ou do planejamento, responda unknown se não for possível identificar o tipo específico mencionado ou
              se informações de mais de um tipo forem necessárias.
            - No campo answer_requirements, adicione apenas o que deve ser respondido pelo próximo agente, não quais ferramentas devem ser usadas ou foram usadas.
            
            Mensagem do usuário:
            {message}
    """

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
            about what consortium options are available, better fit a scenario, or what are the specifics of a certain consortium.
                Examples of prompts:
                - What consortium options are available?
                - What consortium should I look into if I want to buy a house?
                - What is the maximum credit amount I can get with a automobile consortium?  

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