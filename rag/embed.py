import os
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
SCORES_PATH = os.path.join(PROCESSED_DIR, "company_scores.csv")


def get_chroma_client():
    """Get a persistent Chroma client."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_collection(client: chromadb.PersistentClient):
    """Get or create the companies collection."""
    ef = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(
        name="visawise_companies",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def company_to_document(row: pd.Series) -> str:
    """Convert a company row to a rich text document for embedding."""
    risk = row.get("risk_level", "unknown")
    approval_rate = round(float(row.get("approval_rate", 0)) * 100, 1)

    risk_label = {
        "very_safe": "very safe",
        "safe": "safe",
        "moderate": "moderate risk",
        "risky": "risky",
    }.get(risk, "unknown")

    return f"""
Company: {row['employer']}
Location: {row.get('city', '').title()}, {row.get('state', '')}
H1B Sponsor Score: {row['sponsor_score']} out of 100
Risk Level: {risk_label}
Total H1B Petitions Filed: {int(row['total_petitions'])}
Total Approvals: {int(row['total_approvals'])}
Total Denials: {int(row['total_denials'])}
Approval Rate: {approval_rate}%
Years Active: {int(row['years_active'])} years of H1B filing history
Latest Filing Year: {int(row['latest_year'])}
""".strip()


def get_risk_level(score: float) -> str:
    if score >= 90:
        return "very_safe"
    elif score >= 75:
        return "safe"
    elif score >= 50:
        return "moderate"
    return "risky"


def embed_companies(limit: int = None):
    """Embed company scores into Chroma vector database."""
    print("Loading company scores...")
    df = pd.read_csv(SCORES_PATH)
    df["employer"] = df["employer"].str.strip().str.upper()
    df["risk_level"] = df["sponsor_score"].apply(get_risk_level)

    if limit:
        df = df.head(limit)
        print(f"  Limited to {limit} companies for testing")

    print(f"  Loaded {len(df):,} companies")

    client = get_chroma_client()
    collection = get_collection(client)

    existing = collection.count()
    if existing > 0:
        print(f"  Collection already has {existing:,} documents.")
        ans = input("  Re-embed? This will reset the collection. (y/n): ")
        if ans.lower() == "y":
            client.delete_collection("visawise_companies")
            collection = get_collection(client)
        else:
            print("  Skipping embedding.")
            return

    print("Embedding companies into Chroma...")

    batch_size = 100
    total = len(df)

    for i in range(0, total, batch_size):
        batch = df.iloc[i : i + batch_size]

        documents = [company_to_document(row) for _, row in batch.iterrows()]
        ids = [f"company_{row['employer'].replace(' ', '_')}" for _, row in batch.iterrows()]
        metadatas = [
            {
                "employer": row["employer"],
                "state": str(row.get("state", "")),
                "city": str(row.get("city", "")).title(),
                "sponsor_score": float(row["sponsor_score"]),
                "risk_level": str(row["risk_level"]),
                "total_petitions": int(row["total_petitions"]),
                "approval_rate": float(row.get("approval_rate", 0)),
                "years_active": int(row["years_active"]),
                "latest_year": int(row["latest_year"]),
            }
            for _, row in batch.iterrows()
        ]

        collection.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

        pct = min(i + batch_size, total)
        print(f"  Embedded {pct:,} / {total:,} companies...")

    print(f"\nDone. {collection.count():,} companies in Chroma.")


if __name__ == "__main__":
    embed_companies()