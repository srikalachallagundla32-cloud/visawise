import os
import pandas as pd
from rapidfuzz import process, fuzz

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SCORES_PATH = os.path.join(PROCESSED_DIR, "company_scores.csv")
COMPANY_ROLES_PATH = os.path.join(PROCESSED_DIR, "company_roles.csv")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

# NAICS code groupings — broad industry buckets
NAICS_GROUPS = {
    "51": "tech",
    "52": "finance",
    "54": "consulting",
    "62": "healthcare",
    "61": "education",
    "33": "manufacturing",
    "42": "wholesale",
    "23": "construction",
    "44": "retail",
    "48": "transportation",
    "72": "hospitality",
    "81": "services",
    "56": "admin",
    "32": "manufacturing",
    "31": "manufacturing",
}

# Manual overrides for top private companies that fuzzy might miss
# Format: "USCIS NAME": "LCA NAME"
MANUAL_OVERRIDES = {
    "INFOSYS LIMITED": "INFOSYS LIMITED",
    "INFOSYS BPO AMERICA LLC": "INFOSYS LIMITED",
    "TATA CONSULTANCY SVCS LTD": "TATA CONSULTANCY SERVICES LIMITED",
    "TATA CONSULTANCY SERVICES": "TATA CONSULTANCY SERVICES LIMITED",
    "WIPRO LIMITED": "WIPRO LIMITED",
    "COGNIZANT TECHNOLOGY SOLUTIONS US": "COGNIZANT TECHNOLOGY SOLUTIONS US CORP",
    "COGNIZANT TECHNOLOGY SOLUTIONS US CORP": "COGNIZANT TECHNOLOGY SOLUTIONS US CORP",
    "AMAZON COM SERVICES LLC": "AMAZON.COM SERVICES LLC",
    "AMAZON.COM SERVICES LLC": "AMAZON.COM SERVICES LLC",
    "AMAZON WEB SERVICES INC": "AMAZON WEB SERVICES INC",
    "HCL AMERICA INC": "HCL AMERICA INC",
    "TECH MAHINDRA AMERICAS INC": "TECH MAHINDRA AMERICAS INC",
    "ERNST YOUNG US LLP": "ERNST & YOUNG US LLP",
    "FACEBOOK INC": "META PLATFORMS INC",
}


def get_naics_group(naics_code) -> str:
    """Get broad industry group from NAICS code."""
    code = str(naics_code)[:2] if naics_code else ""
    return NAICS_GROUPS.get(code, "other")


def normalize_name(name: str) -> str:
    """Normalize company name for better matching."""
    if not isinstance(name, str):
        return ""
    name = name.upper().strip()
    # Remove common suffixes that differ between datasets
    for suffix in [" LLC", " INC", " CORP", " LTD", " LP", " LLP",
                   " CO", " CORPORATION", " LIMITED", " COMPANY",
                   ".", ",", "&"]:
        name = name.replace(suffix, "")
    return name.strip()


def build_lca_lookup(company_roles: pd.DataFrame) -> dict:
    """Build a lookup dict of normalized LCA name -> original LCA name."""
    lookup = {}
    for _, row in company_roles.iterrows():
        employer = row["employer_clean"]
        normalized = normalize_name(employer)
        lookup[normalized] = employer
    return lookup


def fuzzy_match_company(
    uscis_name: str,
    lca_names: list,
    lca_lookup: dict,
    threshold: int = 85,
) -> str | None:
    """
    Find the best matching LCA company name for a USCIS company name.
    Returns the original LCA name if a match is found above threshold.
    """
    normalized_uscis = normalize_name(uscis_name)

    result = process.extractOne(
        normalized_uscis,
        lca_names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )

    if result:
        matched_normalized, score, _ = result
        return lca_lookup.get(matched_normalized)

    return None


def run():
    print("=== Entity Resolution Pipeline ===\n")

    print("Loading company scores...")
    scores = pd.read_csv(SCORES_PATH)
    scores["employer"] = scores["employer"].str.strip().str.upper()
    scores["naics_group"] = scores.get("naics", pd.Series([""] * len(scores))).apply(get_naics_group)
    print(f"  {len(scores):,} USCIS companies")

    print("Loading LCA company roles...")
    company_roles = pd.read_csv(COMPANY_ROLES_PATH)
    company_roles["employer_clean"] = company_roles["employer_clean"].str.strip().str.upper()
    print(f"  {len(company_roles):,} LCA companies")

    lca_lookup = build_lca_lookup(company_roles)
    normalized_lca_names = list(lca_lookup.keys())

    print("\nStep 1 — Applying manual overrides for top private companies...")
    manual_matches = 0
    match_map = {}

    for uscis_name, lca_name in MANUAL_OVERRIDES.items():
        if uscis_name in scores["employer"].values:
            match_map[uscis_name] = lca_name
            manual_matches += 1

    print(f"  Manual matches: {manual_matches}")

    print("\nStep 2 — Exact name matching after normalization...")
    exact_matches = 0
    for _, row in scores.iterrows():
        employer = row["employer"]
        if employer in match_map:
            continue
        normalized = normalize_name(employer)
        if normalized in lca_lookup:
            match_map[employer] = lca_lookup[normalized]
            exact_matches += 1

    print(f"  Exact matches: {exact_matches}")

    print("\nStep 3 — NAICS-filtered fuzzy matching (this takes a few minutes)...")
    fuzzy_matches = 0
    unmatched = scores[~scores["employer"].isin(match_map)].copy()
    print(f"  Companies to fuzzy match: {len(unmatched):,}")

    for i, (_, row) in enumerate(unmatched.iterrows()):
        employer = row["employer"]

        match = fuzzy_match_company(
            employer,
            normalized_lca_names,
            lca_lookup,
            threshold=88,
        )

        if match:
            match_map[employer] = match
            fuzzy_matches += 1

        if i % 1000 == 0:
            print(f"  Processed {i:,} / {len(unmatched):,}...")

    print(f"  Fuzzy matches: {fuzzy_matches}")

    print("\n=== Match Summary ===")
    total_matched = len(match_map)
    print(f"  Manual overrides:  {manual_matches:,}")
    print(f"  Exact matches:     {exact_matches:,}")
    print(f"  Fuzzy matches:     {fuzzy_matches:,}")
    print(f"  Total matched:     {total_matched:,} of {len(scores):,} ({total_matched/len(scores)*100:.1f}%)")

    print("\nJoining with LCA role and salary data...")
    scores["lca_match"] = scores["employer"].map(match_map)

    enriched = scores.merge(
        company_roles.rename(columns={"employer_clean": "lca_match"}),
        on="lca_match",
        how="left",
    )

    output_path = os.path.join(PROCESSED_DIR, "company_scores_enriched.csv")
    enriched.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")

    print("\n=== Sample matches ===")
    matched = enriched[enriched["lca_match"].notna()].head(10)
    for _, row in matched.iterrows():
        print(f"\n{row['employer']}")
        print(f"  Matched to: {row['lca_match']}")
        print(f"  Score: {row['sponsor_score']} | Salary: ${row.get('median_salary_all', 0):,.0f}")
        print(f"  Top roles: {row.get('top_roles', 'N/A')}")

    print("\nDone.")


if __name__ == "__main__":
    run()