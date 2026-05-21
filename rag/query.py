import os
import anthropic
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")


def get_collection():
    """Connect to the existing Chroma collection."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = embedding_functions.DefaultEmbeddingFunction()
    return client.get_collection(
        name="visawise_companies",
        embedding_function=ef,
    )


def search_companies(question: str, n_results: int = 10) -> list[dict]:
    """
    Search Chroma for companies relevant to the user's question.
    Returns a list of matching company metadata + documents.
    """
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    companies = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        companies.append({
            "document": doc,
            "metadata": meta,
            "relevance_score": round(1 - dist, 3),
        })

    return companies


def build_context(companies: list[dict]) -> str:
    """Turn retrieved companies into a context string for Claude."""
    lines = []
    for i, c in enumerate(companies, 1):
        lines.append(f"--- Company {i} ---")
        lines.append(c["document"])
        lines.append("")
    return "\n".join(lines)


def ask_visawise(question: str, n_results: int = 10) -> str:
    """
    Full RAG pipeline:
    1. Search Chroma for relevant companies
    2. Build context from results
    3. Ask Claude to answer using that context
    """
    print(f"\nSearching for: {question}")

    companies = search_companies(question, n_results=n_results)
    print(f"Found {len(companies)} relevant companies")

    context = build_context(companies)

    system_prompt = """You are Visawise, an H1B visa intelligence assistant.
You help job seekers on H1B visas find companies that are safe to apply to.

You have access to real USCIS H1B petition data from 2019-2023.
Always base your answers on the company data provided to you.
Be specific, practical, and honest. If the data shows a company is risky, say so.
Format your response clearly with company names, scores, and reasons.
Always remind users that visa decisions depend on many factors beyond sponsorship history."""

    user_message = f"""Based on the following H1B company data, please answer this question:

Question: {question}

Company Data:
{context}

Please give a helpful, specific answer based on this data."""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )

    return response.content[0].text


if __name__ == "__main__":
    test_questions = [
        "Which companies in California are very safe for H1B sponsorship?",
        "Is Goldman Sachs safe for H1B visa holders?",
        "Which tech companies have the highest approval rates?",
    ]

    for question in test_questions:
        print("\n" + "=" * 60)
        print(f"Q: {question}")
        print("=" * 60)
        answer = ask_visawise(question)
        print(f"A: {answer}")