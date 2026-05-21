import os
import math
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Visawise API",
    description="H1B sponsor intelligence platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SCORES_PATH = os.path.join(PROCESSED_DIR, "company_scores_enriched.csv")
COMBINED_PATH = os.path.join(PROCESSED_DIR, "h1b_combined.csv")

# Load data once at startup
print("Loading company scores...")
df_scores = pd.read_csv(SCORES_PATH)
df_scores["employer"] = df_scores["employer"].str.strip().str.upper()

print("Loading combined H1B data...")
df_combined = pd.read_csv(COMBINED_PATH)
df_combined["employer"] = df_combined["employer"].str.strip().str.upper()

print(f"Ready — {len(df_scores):,} companies loaded.")


def company_to_dict(row: pd.Series) -> dict:
    return {
        "employer": row["employer"].title(),
        "sponsor_score": round(float(row["sponsor_score"]), 1),
        "total_petitions": int(row["total_petitions"]),
        "total_approvals": int(row["total_approvals"]),
        "total_denials": int(row["total_denials"]),
        "approval_rate": round(float(row["approval_rate"]) * 100, 1),
        "years_active": int(row["years_active"]),
        "latest_year": int(row["latest_year"]),
        "state": str(row["state"]),
        "city": str(row["city"]).title(),
        "risk_level": get_risk_level(float(row["sponsor_score"])),
        "median_salary": int(row["median_salary_all"]) if pd.notna(row.get("median_salary_all")) else None,
        "top_roles": str(row["top_roles"]).split(", ")[:5] if pd.notna(row.get("top_roles")) else [],
        "total_lca_filings": int(row["total_lca_filings"]) if pd.notna(row.get("total_lca_filings")) else None,
    }


def get_risk_level(score: float) -> str:
    if score >= 90:
        return "very_safe"
    elif score >= 75:
        return "safe"
    elif score >= 50:
        return "moderate"
    else:
        return "risky"


def get_yearly_history(employer: str) -> list:
    emp_data = df_combined[df_combined["employer"] == employer.upper()]
    if emp_data.empty:
        return []

    # Aggregate all columns by year to remove duplicates
    numeric_cols = ["initial_approvals", "initial_denials", 
                    "continuing_approvals", "continuing_denials",
                    "initial_approval", "initial_denial",
                    "continuing_approval", "continuing_denial"]
    
    existing_cols = [c for c in numeric_cols if c in emp_data.columns]
    
    agg_dict = {c: "sum" for c in existing_cols}
    yearly = emp_data.groupby("fiscal_year").agg(agg_dict).reset_index()

    history = []
    for _, row in yearly.sort_values("fiscal_year").iterrows():
        approvals = int(sum(row.get(c, 0) for c in ["initial_approvals", "initial_approval", "continuing_approvals", "continuing_approval"] if c in row))
        denials = int(sum(row.get(c, 0) for c in ["initial_denials", "initial_denial", "continuing_denials", "continuing_denial"] if c in row))
        total = approvals + denials
        history.append({
            "year": int(row["fiscal_year"]),
            "approvals": approvals,
            "denials": denials,
            "total": total,
            "approval_rate": round(approvals / total * 100, 1) if total > 0 else 0,
        })
    return history

@app.get("/")
def root():
    return {
        "name": "Visawise API",
        "version": "1.0.0",
        "companies": len(df_scores),
        "endpoints": ["/companies/top", "/companies/search", "/companies/{name}"],
    }


@app.get("/companies/top")
def top_companies(
    limit: int = Query(default=20, ge=1, le=100),
    state: str = Query(default=None),
    min_petitions: int = Query(default=10),
):
    """Get top H1B sponsoring companies by sponsor score."""
    filtered = df_scores[df_scores["total_petitions"] >= min_petitions].copy()

    if state:
        filtered = filtered[filtered["state"].str.upper() == state.upper()]

    top = filtered.head(limit)

    if top.empty:
        return {"companies": [], "total": 0}

    return {
        "companies": [company_to_dict(row) for _, row in top.iterrows()],
        "total": len(filtered),
    }


@app.get("/companies/search")
def search_companies(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Search companies by name."""
    mask = df_scores["employer"].str.contains(q.upper(), na=False)
    results = df_scores[mask].head(limit)

    if results.empty:
        return {"companies": [], "query": q, "total": 0}

    return {
        "companies": [company_to_dict(row) for _, row in results.iterrows()],
        "query": q,
        "total": int(mask.sum()),
    }


@app.get("/companies/{name}")
def get_company(name: str):
    """Get full sponsor profile for a company including yearly history."""
    name_upper = name.strip().upper()
    mask = df_scores["employer"] == name_upper
    matches = df_scores[mask]

    if matches.empty:
        # Try partial match
        mask = df_scores["employer"].str.contains(name_upper, na=False)
        matches = df_scores[mask]
        if matches.empty:
            raise HTTPException(status_code=404, detail=f"Company '{name}' not found")

    row = matches.iloc[0]
    company = company_to_dict(row)
    company["yearly_history"] = get_yearly_history(row["employer"])

    return company


@app.get("/stats")
def global_stats():
    """Global stats about the dataset."""
    return {
        "total_companies": len(df_scores),
        "total_petitions": int(df_scores["total_petitions"].sum()),
        "total_approvals": int(df_scores["total_approvals"].sum()),
        "avg_approval_rate": round(float(df_scores["approval_rate"].mean()) * 100, 1),
        "years_covered": sorted(df_combined["fiscal_year"].unique().tolist()),
        "risk_breakdown": {
            "very_safe": int((df_scores["sponsor_score"] >= 90).sum()),
            "safe": int(((df_scores["sponsor_score"] >= 75) & (df_scores["sponsor_score"] < 90)).sum()),
            "moderate": int(((df_scores["sponsor_score"] >= 50) & (df_scores["sponsor_score"] < 75)).sum()),
            "risky": int((df_scores["sponsor_score"] < 50).sum()),
        },
    }