import os
from langchain.tools import tool
from app.tools.products import search_products
from app.tools.mcp_client import get_mcp_tools
from app.tools.consortium import (
    search_consortium,
    evaluate_consortium_affordability,
    evaluate_consortium_suitability,
    simulate_consortium_payment,
)
from app.rag.retriever import search_documents, format_search_results
from app.rag.pgvector_store import (
    search_documents_pgvector,
    format_search_results_pgvector
)
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "pgvector")  # Default to pgvector if not set

# Not currently in use
@tool
def search_product_db(product_type: str | None = None) -> list[dict]:
    """
    Search active product options from the product database:

    Options:
    - credit_card
    - personal_loan
    - certificate_of_deposit
    - auto_loan
    - payroll_loan
    - mortgage
    - overdraft
    """
    return search_products(product_type)

# Using MCP version
@tool
def search_consortium_db(consortium_type: str | None = None) -> list[dict]:
    """
    Search the bank's internal PostgreSQL database for active consortium options.

    Use this tool whenever the user asks about:
    - available consortium options
    - specific consortium plans
    - product listings
    - credit ranges
    - administration fees
    - reserve fund fees
    - maximum terms
    - minimum income
    - estimated monthly payment ranges

    The consortium_type argument is optional.
    Use None to list all active consortium options.

    Valid consortium_type values include:
    - automobile
    - motorcycle
    - real estate
    - services

    This tool is the source of truth for the bank's available consortium products.
    """
    return search_consortium(consortium_type)

@tool
def check_consortium_affordability(
    monthly_income: float,
    monthly_existing_debts: float,
    estimated_consortium_payment: float,
) -> dict:
    """
    Evaluate whether a consortium installment appears affordable based on income and debts.

    Use this tool whenever the user asks about:
    - whether they can afford a consortium
    - whether a consortium is suitable for their financial situation

    This is not credit approval.
    """
    return evaluate_consortium_affordability(
        monthly_income=monthly_income,
        monthly_existing_debts=monthly_existing_debts,
        estimated_consortium_payment=estimated_consortium_payment,
    )

@tool
def check_consortium_suitability(
    objective: str,
    urgency_months: int | None,
    has_bid_amount: bool,
    wants_predictable_acquisition_date: bool,
) -> dict:
    """
    Evaluate whether a consortium is conceptually suitable for the user's goal.

    Use this tool whenever the user asks about:
    - whether a consortium is suitable for their objective
    - whether a consortium is a good option for their situation
    - whether a consortium is worth it for their goal
    - whether a consortium is a good investment

    Consortiums may not be ideal when the user needs immediate possession
    or needs a guaranteed acquisition date.

    This is not credit approval and does not guarantee participation, contemplation, or suitability.
    """
    return evaluate_consortium_suitability(
        objective=objective,
        urgency_months=urgency_months,
        has_bid_amount=has_bid_amount,
        wants_predictable_acquisition_date=wants_predictable_acquisition_date,
    )

@tool
def consortium_installment_simulation(
    credit_amount: float,
    term_months: int,
    total_admin_fee_rate: float,
    reserve_fund_rate: float,
    membership_fee: float,
) -> dict:
    """
    Simulate an estimated consortium installment.

    Use this tool whenever the user asks about:
    - estimated monthly payment for a consortium
    - estimated installment for a consortium
    - estimated payment for a consortium 

    Rules:
    - When using this tool utilize the data specified by the client or the standard data present in the database, utilized by the most fitting option.
    - Show the user the estimated monthly payment, total fees, and total cost of the consortium, and also specify what consortium option was selected or resembles the user's needs and specified information.
    - Explain the basics of the calculation so the user understands how the estimated monthly payment was derived.
    - Do not just return the estimated monthly payment and other numbers. Provide a detailed explanation of the scenario calculated and the factors that influence it.
    - Always model the calculations on the best available consortium option from the database, so use the search_consortium_db tool to check the available options.

    Format the answer in Markdown, including:
        - Selected consortium option: Automobile, Motorcycle, Real Estate, or Services
        - Credit amount
        - Term in months
        - Administrative fee
        - Reserve fund, if available
        - Estimated total cost
        - Estimated monthly payment
        - Short calculation formula
    
    Use clean Markdown. Do not output broken bold markers, missing spaces, or unformatted numbers.

    This is only an estimate. Real installments may vary.
    """
    return simulate_consortium_payment(
        credit_amount=credit_amount,
        term_months=term_months,
        total_admin_fee_rate=total_admin_fee_rate,
        reserve_fund_rate=reserve_fund_rate,
        membership_fee=membership_fee,
    ) 

# Using MCP version
@tool 
def search_consortium_documents(query: str) -> str:
    """
    Search internal consortium documents, manuals, FAQs, and policies.

    Use this tool for questions about:
    - how consortiums work
    - contemplation rules
    - bid offers
    - cancellation
    - missed payments
    - default/inadimplência
    - risks
    - suitability guidelines
    - policy explanations
    - required documents after contemplation

    Do not use this tool for exact product options, fees, terms,
    minimum income, or credit ranges. For product data, use the
    PostgreSQL consortium database tool.
    """

    if VECTOR_STORE_TYPE == "pgvector":
        results = search_documents_pgvector(query=query, k=4)
        return format_search_results_pgvector(results)
    
    else:
        results = search_documents(query=query, k=4)
        return format_search_results(results)
    
async def get_salesman_tools():
    mcp_tools = await get_mcp_tools()

    allowed_mcp_tool_names = {
        "search_consortium_products",
        "simulate_consortium_payment",
        "search_consortium_documents",
        "search_public_web",
    }

    filtered_mcp_tools = [
        tool for tool in mcp_tools
        if tool.name in allowed_mcp_tool_names
    ]

    return [
        #search_consortium_db,
        consortium_installment_simulation,
        #search_consortium_documents,
        *filtered_mcp_tools,
    ]


async def get_consultant_tools():
    mcp_tools = await get_mcp_tools()

    allowed_mcp_tool_names = {
        "search_consortium_products",
        "simulate_consortium_payment",
        "search_consortium_documents",
        "search_public_web",
    }

    filtered_mcp_tools = [
        tool for tool in mcp_tools
        if tool.name in allowed_mcp_tool_names
    ]

    return [
        #search_consortium_db,
        check_consortium_affordability,
        check_consortium_suitability,
        consortium_installment_simulation,
        #search_consortium_documents,
        *filtered_mcp_tools,
    ]

async def get_specialist_tools():
    mcp_tools = await get_mcp_tools()

    allowed_mcp_tool_names = {
        "simulate_consortium_payment",
    }

    filtered_mcp_tools = [
        tool for tool in mcp_tools
        if tool.name in allowed_mcp_tool_names
    ]

    return [
        check_consortium_affordability,
        check_consortium_suitability,
        consortium_installment_simulation,
        *filtered_mcp_tools,
    ]

async def get_collector_tools():
    mcp_tools = await get_mcp_tools()

    allowed_mcp_tool_names = {
        "search_consortium_products",
        "search_consortium_documents",
        "search_public_web",
    }

    collector_tools = {
        tool.name: tool for tool in mcp_tools if tool.name in allowed_mcp_tool_names
    }

    return collector_tools

"""
salesman_tools = [
    search_consortium_db, 
    search_product_db, 
    consortium_installment_simulation,
    search_consortium_documents
]

consultant_tools = [
    search_consortium_db, 
    search_product_db, 
    consortium_installment_simulation,
    check_consortium_affordability,
    check_consortium_suitability,
    search_consortium_documents
]
"""