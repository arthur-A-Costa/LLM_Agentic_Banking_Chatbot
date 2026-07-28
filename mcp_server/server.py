from mcp.server.fastmcp import FastMCP
import os

from app.tools.consortium import search_consortium, search_consortium_cache
from app.tools.registry import consortium_installment_simulation
from app.rag.pgvector_store import search_documents_pgvector, format_search_results_pgvector
from app.tools.exa_web_search import search_web_exa, search_web_with_jina, search_web_with_cache

CACHE = os.getenv("CACHE", "false")

mcp = FastMCP(
    name="banking-consortium-mcp",
    host="0.0.0.0",
    port=8001,
)

@mcp.tool()
def health_check() -> str:
    """Check if the MCP server is running."""
    return "MCP server is running."

@mcp.tool()
def search_consortium_products(consortium_type: str | None = None) -> list[dict]:
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

    if CACHE == "true":
        return search_consortium_cache(consortium_type)
    else: 
        return search_consortium(consortium_type)


@mcp.tool()
def simulate_consortium_payment(
    credit_amount: float,
    term_months: int,
    admin_fee_percentage: float,
    reserve_fund_percentage: float,
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
    return consortium_installment_simulation.invoke(
        {
            "credit_amount": credit_amount,
            "term_months": term_months,
            "admin_fee_percentage": admin_fee_percentage,
            "reserve_fund_percentage": reserve_fund_percentage,
        }
    )


@mcp.tool()
def search_consortium_documents(query: str, k: int = 4) -> str:
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
    results = search_documents_pgvector(query=query, k=k)
    return format_search_results_pgvector(results)

@mcp.tool()
def search_public_web(query: str, k: int = 1) -> list[dict]:
    """
    Search the internet using Exa API.

    Use this only for external, public, current, or non-bank-internal information.
    Do not use this for internal consortium product names, fees, terms, or credit ranges.
    Internal product information must come from the PostgreSQL consortium tools.

    Examples of when to use this tool:
    - Current value of government specific rates, such as Selic, IPCA, CDI, etc.
    - Current value of the dollar, euro, or other currencies.
    - Current value of the stock market, such as Ibovespa, Nasdaq, S&P 500, etc.
    - Current news or events that may affect consortiums or financial markets. 
    - Current price of a specific car model.

    For questions and search requests that are not pertinent to banking and consortiums politely refuse to 
    answer and explain that you only have the ability to access the web to search for information and investigate
    when the it directly connects to the themes in question (banking, economy, consortiums).   
    """

    #return search_web_exa(query=query, k=k)

    if CACHE == "true":
        return search_web_with_cache(query=query, k=k)
    else:
        return search_web_exa(query=query, k=k)

if __name__ == "__main__":
    print("Starting MCP server on 0.0.0.0:8001...", flush=True)
    mcp.run(transport="streamable-http")