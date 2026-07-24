import os
from exa_py import Exa
import requests

jina_auth_key = os.getenv("JINA_AUTH_KEY")
Jina = os.getenv("JINA")

def get_exa_client() -> Exa:
    api_key = os.getenv("EXA_API_KEY")

    if not api_key:
        raise ValueError("EXA_API_KEY is not set.")

    return Exa(api_key=api_key)

def jina_read_url(url: str, timeout: int = 20) -> dict:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Authorization": f"Bearer {jina_auth_key}",
        "Accept": "application/json"
    }

    response = requests.get(jina_url, headers=headers, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    content = data["data"]["content"]
    title = data["data"]["title"]

    return {
        "url": url,
        "title": title,
        "content": content[:6000], 
    }

def compact_page(page: dict, max_char: int = 2500) -> dict:
    content = page.get("content")

    return {
        "title": page.get("title"),
        "url": page.get("url"),
        "content_preview": content[:max_char],
    }

def search_web_exa(query: str, k: int = 3) -> list[dict]:
    exa_client = get_exa_client()

    response = exa_client.search(query, num_results=k, contents={"highlights": True, "text": {"max_characters": 1200}},)
    clean_response = []

    # Without Jina
    for result in response.results:
        highlights = getattr(result, "highlights", None)
        text = getattr(result, "text", None)
        clean_response.append(
            {
                "title": getattr(result, "title", None),
                "url": getattr(result, "url", None),
                "published_date": getattr(result, "published_date", None),
                "author": getattr(result, "author", None),
                "highlights": highlights,
                "text_preview": text[:1200] if text else None,
            }
        )

    return clean_response

def search_web_with_jina(query: str, k: int = 2) -> dict:
    print("=== search_web_with_jina CALLED ===", flush=True)
    search_results = search_web_exa(query=query, k=k)
    jina_pages = []

    for result in search_results:
        url = result.get("url")

        if not url:
            continue

        try:
            page = jina_read_url(url=url)
            jina_pages.append(compact_page(page))

        except Exception as error:
            jina_pages.append(
                {
                    "title": result.get("title"),
                    "url": url,
                    "text_preview": result.get("text_preview"),
                    "error": str(error),
                }
            )
        
    return {
        "query": query,
        "search_results": search_results,
        "jina_pages": jina_pages,
    }
