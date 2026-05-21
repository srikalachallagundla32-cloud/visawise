import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

LCA_PATH = os.path.join(RAW_DIR, "lca_2023.xlsx")
SCORES_PATH = os.path.join(PROCESSED_DIR, "company_scores.csv")

# Map SOC codes to friendly role categories
ROLE_CATEGORIES = {
    "15-": "Software & IT",
    "17-": "Engineering",
    "19-": "Data & Research",
    "11-": "Management",
    "13-": "Finance & Business",
    "29-": "Healthcare",
    "25-": "Education",
    "23-": "Legal",
    "27-": "Design & Media",
    "41-": "Sales",
}

# Map common job titles to clean role names
TITLE_MAP = {
    "software engineer": "Software Engineer",
    "software developer": "Software Engineer",
    "senior software engineer": "Software Engineer",
    "swe": "Software Engineer",
    "data scientist": "Data Scientist",
    "data engineer": "Data Engineer",
    "machine learning engineer": "ML Engineer",
    "ml engineer": "ML Engineer",
    "product manager": "Product Manager",
    "program manager": "Program Manager",
    "project manager": "Project Manager",
    "business analyst": "Business Analyst",
    "data analyst": "Data Analyst",
    "financial analyst": "Financial Analyst",
    "systems analyst": "Systems Analyst",
    "network engineer": "Network Engineer",
    "devops engineer": "DevOps Engineer",
    "cloud engineer": "Cloud Engineer",
    "full stack": "Full Stack Engineer",
    "frontend engineer": "Frontend Engineer",
    "backend engineer": "Backend Engineer",
    "research scientist": "Research Scientist",
    "physician": "Physician",
    "registered nurse": "Registered Nurse",
    "accountant": "Accountant",
    "consultant": "Consultant",
    "architect": "Solutions Architect",
    "qa engineer": "QA Engineer",
    "test engineer": "QA Engineer",
    "security engineer": "Security Engineer",
    "hardware engineer": "Hardware Engineer",
}


def normalize_title(title: str) -> str:
    """Map a raw job title to a clean standardized role name."""
    if not isinstance(title, str):
        return "Other"
    t = title.lower().strip()
    for key, clean in TITLE_MAP.items():
        if key in t:
            return clean
    return title.title()[:40]


def get_role_category(soc_code: str) -> str:
    """Map SOC code prefix to a role category."""
    if not isinstance(soc_code, str):
        return "Other"
    for prefix, category in ROLE_CATEGORIES.items():
        if soc_code.startswith(prefix):
            return category
    return "Other"


def normalize_wage(row: pd.Series) -> float:
    """Convert wage to annual salary."""
    wage = row.get("WAGE_RATE_OF_PAY_FROM", 0)
    unit = str(row.get("WAGE_UNIT_OF_PAY", "Year")).lower()

    try:
        wage = float(wage)
    except (ValueError, TypeError):
        return 0.0

    if "hour" in unit:
        return wage * 2080
    elif "week" in unit:
        return wage * 52
    elif "month" in unit:
        return wage * 12
    elif "bi-week" in unit:
        return wage * 26
    else:
        return wage


def load_lca() -> pd.DataFrame:
    """Load and clean the LCA Excel file."""
    print("Loading LCA data (this takes a minute)...")
    df = pd.read_excel(LCA_PATH, engine="openpyxl")
    print(f"  Loaded {len(df):,} LCA records")

    df = df[df["CASE_STATUS"] == "Certified"].copy()
    print(f"  Certified records: {len(df):,}")

    df["employer_clean"] = (
        df["EMPLOYER_NAME"]
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )

    df["job_title_clean"] = df["JOB_TITLE"].apply(normalize_title)
    df["role_category"] = df["SOC_CODE"].apply(get_role_category)
    df["annual_salary"] = df.apply(normalize_wage, axis=1)

    df = df[df["annual_salary"] > 20000].copy()
    print(f"  Records with valid salary: {len(df):,}")

    return df


def build_role_salary_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-company per-role salary summary."""
    print("Building role + salary summary per company...")

    summary = (
        df.groupby(["employer_clean", "job_title_clean"])
        .agg(
            count=("annual_salary", "count"),
            median_salary=("annual_salary", "median"),
            min_salary=("annual_salary", "min"),
            max_salary=("annual_salary", "max"),
            role_category=("role_category", "first"),
            state=("WORKSITE_STATE", lambda x: x.mode()[0] if len(x) > 0 else ""),
        )
        .reset_index()
    )

    summary = summary[summary["count"] >= 2].copy()
    summary["median_salary"] = summary["median_salary"].round(0).astype(int)
    summary["min_salary"] = summary["min_salary"].round(0).astype(int)
    summary["max_salary"] = summary["max_salary"].round(0).astype(int)

    print(f"  Built {len(summary):,} company-role combinations")
    return summary


def build_company_roles(df: pd.DataFrame) -> pd.DataFrame:
    """Build a summary of top roles per company."""
    print("Building top roles per company...")

    company_roles = (
        df.groupby("employer_clean")
        .apply(
            lambda g: pd.Series({
                "top_roles": ", ".join(
                    g["job_title_clean"].value_counts().head(5).index.tolist()
                ),
                "median_salary_all": int(g["annual_salary"].median()),
                "total_lca_filings": len(g),
                "role_category": g["role_category"].mode()[0] if len(g) > 0 else "",
            })
        )
        .reset_index()
    )

    return company_roles


def enrich_company_scores(scores: pd.DataFrame, company_roles: pd.DataFrame) -> pd.DataFrame:
    """Join USCIS scores with LCA role and salary data."""
    print("Joining USCIS scores with LCA data...")

    enriched = scores.merge(
        company_roles,
        left_on="employer",
        right_on="employer_clean",
        how="left",
    )

    matched = enriched["top_roles"].notna().sum()
    print(f"  Matched {matched:,} of {len(scores):,} companies with LCA data")

    return enriched


def run():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    df_lca = load_lca()

    role_salary = build_role_salary_summary(df_lca)
    role_salary_path = os.path.join(PROCESSED_DIR, "role_salary.csv")
    role_salary.to_csv(role_salary_path, index=False)
    print(f"  Saved: {role_salary_path}")

    company_roles = build_company_roles(df_lca)
    company_roles_path = os.path.join(PROCESSED_DIR, "company_roles.csv")
    company_roles.to_csv(company_roles_path, index=False)
    print(f"  Saved: {company_roles_path}")

    scores = pd.read_csv(SCORES_PATH)
    scores["employer"] = scores["employer"].str.strip().str.upper()

    enriched = enrich_company_scores(scores, company_roles)
    enriched_path = os.path.join(PROCESSED_DIR, "company_scores_enriched.csv")
    enriched.to_csv(enriched_path, index=False)
    print(f"  Saved: {enriched_path}")

    print("\n=== Sample enriched companies ===")
    sample = enriched[enriched["top_roles"].notna()].head(5)
    for _, row in sample.iterrows():
        print(f"\n{row['employer']}")
        print(f"  Score: {row['sponsor_score']} | Salary: ${row.get('median_salary_all', 0):,.0f}")
        print(f"  Top roles: {row.get('top_roles', 'N/A')}")

    print("\nDone.")


if __name__ == "__main__":
    run()