import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

def get_available_years() -> list:
    """Automatically detect which years have data in data/raw/."""
    import glob
    files = glob.glob(os.path.join(RAW_DIR, "h1b_*.csv"))
    years = []
    for f in files:
        basename = os.path.basename(f)
        try:
            year = int(basename.replace("h1b_", "").replace(".csv", ""))
            years.append(year)
        except ValueError:
            pass
    return sorted(years)


def load_raw(year: int) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, f"h1b_{year}.csv")
    print(f"  Loading {year}...")
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["fiscal_year"] = year
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to a standard schema across all years."""

    # Print columns so we can see what we're working with
    print(f"  Columns: {list(df.columns)}")

    # Common column name mappings across USCIS file versions
    rename_map = {
        "employer_(petitioner)_name": "employer",
        "petitioner_name": "employer",
        "employer_name": "employer",
        "case_status": "status",
        "initial_approval": "initial_approvals",
        "initial_denial": "initial_denials",
        "continuing_approval": "continuing_approvals",
        "continuing_denial": "continuing_denials",
        "state_(of_employment)": "state",
        "city_(of_employment)": "city",
        "zip_code": "zip",
        "naics_code": "naics",
        "tax_id": "tax_id",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the dataframe."""

    # Standardize employer names
    if "employer" in df.columns:
        df["employer"] = (
            df["employer"]
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)
        )

    # Fill numeric columns with 0
    numeric_cols = [
        "initial_approvals", "initial_denials",
        "continuing_approvals", "continuing_denials"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Standardize state to uppercase
    if "state" in df.columns:
        df["state"] = df["state"].str.strip().str.upper()

    return df


def compute_sponsor_score(group: pd.DataFrame) -> float:
    """
    Score a company's H1B sponsorship reliability from 0-100.

    Formula:
    - Approval rate (60%): approvals / (approvals + denials)
    - Volume score (25%): log scale of total petitions filed
    - Consistency score (15%): number of years with filings
    """
    import math

    total_approvals = (
        group["initial_approvals"].sum() +
        group["continuing_approvals"].sum()
    )
    total_denials = (
        group["initial_denials"].sum() +
        group["continuing_denials"].sum()
    )
    total = total_approvals + total_denials

    if total == 0:
        return 0.0

    # Approval rate score (0-60)
    approval_rate = total_approvals / total
    approval_score = approval_rate * 60

    # Volume score (0-25) — log scale, capped at 1000 petitions
    volume_score = min(math.log10(total + 1) / math.log10(1001), 1.0) * 25

    # Consistency score (0-15) — years with filings out of 5
    years_active = group["fiscal_year"].nunique()
    consistency_score = (years_active / 5) * 15

    return round(approval_score + volume_score + consistency_score, 1)


def build_company_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate by employer and compute sponsor score."""
    print("  Computing sponsor scores...")

    records = []
    for employer, g in df.groupby("employer"):
        state_mode = g["state"].dropna().mode()
        city_mode = g["city"].dropna().mode()
        records.append({
            "employer": employer,
            "total_approvals": (
                g.get("initial_approvals", pd.Series([0])).sum() +
                g.get("continuing_approvals", pd.Series([0])).sum()
            ),
            "total_denials": (
                g.get("initial_denials", pd.Series([0])).sum() +
                g.get("continuing_denials", pd.Series([0])).sum()
            ),
            "years_active": g["fiscal_year"].nunique(),
            "latest_year": g["fiscal_year"].max(),
            "state": state_mode.iloc[0] if len(state_mode) > 0 else "",
            "city": city_mode.iloc[0] if len(city_mode) > 0 else "",
            "sponsor_score": compute_sponsor_score(g),
        })

    agg = pd.DataFrame(records)
    agg["total_petitions"] = agg["total_approvals"] + agg["total_denials"]
    agg["approval_rate"] = (
        agg["total_approvals"] / agg["total_petitions"].replace(0, 1)
    ).round(3)

    agg = agg[agg["total_petitions"] >= 5].copy()
    agg = agg.sort_values("sponsor_score", ascending=False).reset_index(drop=True)

    return agg
    
def run():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    print("=== Loading raw data ===")
    frames = []
    years = get_available_years()
    print(f"  Found data for years: {years}")
    for year in years:
        try:
            df = load_raw(year)
            df = normalize(df)
            df = clean(df)
            frames.append(df)
        except Exception as e:
            print(f"  WARNING: Could not load {year}: {e}")

    if not frames:
        print("No data loaded. Check your data/raw/ folder.")
        return

    print(f"\n=== Combining {len(frames)} years of data ===")
    combined = pd.concat(frames, ignore_index=True)
    print(f"  Total rows: {len(combined):,}")

    # Save combined raw
    combined_path = os.path.join(PROCESSED_DIR, "h1b_combined.csv")
    combined.to_csv(combined_path, index=False)
    print(f"  Saved: {combined_path}")

    print("\n=== Building company sponsor scores ===")
    scores = build_company_scores(combined)
    print(f"  Scored {len(scores):,} companies")

    scores_path = os.path.join(PROCESSED_DIR, "company_scores.csv")
    scores.to_csv(scores_path, index=False)
    print(f"  Saved: {scores_path}")

    print("\n=== Top 20 H1B sponsors ===")
    top = scores.head(20)[["employer", "sponsor_score", "total_petitions", "approval_rate", "state"]]
    print(top.to_string(index=False))

    print("\nDone.")


if __name__ == "__main__":
    run()