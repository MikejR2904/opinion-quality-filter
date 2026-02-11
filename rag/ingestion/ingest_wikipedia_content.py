import requests
import os

## We are trying to find the Wikipedia page for a certain place query
## Reason is that Wikipedia is an objective place that we can use to fetch context (history etc.) with minimum effort (without scrapping)
## More elaborations in https://en.wikipedia.org/w/api.php

# Get the entire Wikipedia context
def get_wikipedia_text(query: str) -> str:
    url = "https://en.wikipedia.org/w/api.php"
    # Search for the most relevant page title
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }
    headers = {
        "User-Agent": "OpinionQualityFilter/1.0 (https://github.com/MikejR2904/opinion-quality-filter)"
    }
    search_resp = requests.get(url, params=search_params, headers=headers).json()
    search_results = search_resp.get("query", {}).get("search", [])
    if not search_results:
        print(f"No Wikipedia page found for: {query}")
        return ""
    best_title = search_results[0]["title"] # most suitable search result
    extract_params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "titles": best_title,
        "format": "json"
    }
    resp = requests.get(url, params=extract_params, headers=headers).json()
    pages = resp["query"]["pages"]
    page = next(iter(pages.values()))
    return page.get("extract", "")

# Save the extracted content to .txt format
def save_wiki_page(query: str, filepath: str = "rag/data/raw") -> None:
    text = get_wikipedia_text(query=query)
    filename = query.lower().replace(" ", "_") + ".txt"
    full_path = os.path.join(filepath, filename)
    if text.strip():
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully saved context to {filepath}")



