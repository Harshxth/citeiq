import requests
import time

TOPICS = [
    "sepsis treatment",
    "septic shock management", 
    "diabetes mellitus type 2",
    "hypertension management",
    "antibiotic resistance",
    "acute kidney injury",
    "heart failure treatment",
    "pneumonia clinical"
]

def fetch_abstracts(topic, max_results=15):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    search_params = {
        "db": "pubmed",
        "term": topic,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    
    search_resp = requests.get(search_url, params=search_params)
    ids = search_resp.json()["esearchresult"]["idlist"]
    
    if not ids:
        return []
    
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "abstract",
        "retmode": "text"
    }
    
    fetch_resp = requests.get(fetch_url, params=fetch_params)
    return fetch_resp.text

def main():
    all_abstracts = []
    
    for topic in TOPICS:
        print(f"Fetching: {topic}...")
        abstracts = fetch_abstracts(topic, max_results=10)
        if abstracts:
            all_abstracts.append(f"\n\n{'='*60}\nTOPIC: {topic.upper()}\n{'='*60}\n")
            all_abstracts.append(abstracts)
        time.sleep(0.5)
    
    with open("data/pubmed_abstracts.txt", "w", encoding="utf-8", errors="ignore") as f:
        f.writelines(all_abstracts)
    
    print("Done. Saved to data/pubmed_abstracts.txt")

if __name__ == "__main__":
    main()