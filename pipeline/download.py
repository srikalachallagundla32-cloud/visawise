import os
import requests
from tqdm import tqdm

# USCIS H1B disclosure data is public and free.
# Source: https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub
# These are direct CSV links for fiscal years 2020-2024.

USCIS_FILES = {
    "2024": "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-2024.csv",
    "2023": "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-2023.csv",
    "2022": "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-2022.csv",
    "2021": "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-2021.csv",
    "2020": "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-2020.csv",
}

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def download_file(url: str, dest_path: str) -> bool:
    """Download a file with a progress bar. Returns True if successful."""
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        filename = os.path.basename(dest_path)

        with open(dest_path, "wb") as f, tqdm(
            desc=filename,
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error downloading {url}: {e}")
        return False


def download_all(years: list = None):
    """Download USCIS H1B data for the given years (default: all)."""
    os.makedirs(RAW_DIR, exist_ok=True)

    targets = {y: u for y, u in USCIS_FILES.items() if years is None or y in years}

    print(f"Downloading {len(targets)} USCIS H1B file(s) to {RAW_DIR}\n")

    results = {}
    for year, url in sorted(targets.items(), reverse=True):
        dest = os.path.join(RAW_DIR, f"h1b_{year}.csv")

        if os.path.exists(dest):
            print(f"  {year} already downloaded, skipping.")
            results[year] = True
            continue

        print(f"  Downloading {year}...")
        results[year] = download_file(url, dest)

    print("\nDownload summary:")
    for year, ok in sorted(results.items(), reverse=True):
        status = "OK" if ok else "FAILED"
        print(f"  {year}: {status}")

    return results

if __name__ == "__main__":
    # Check which files are already manually downloaded
    os.makedirs(RAW_DIR, exist_ok=True)
    print(f"Checking {RAW_DIR} for existing files...\n")
    for year in sorted(USCIS_FILES.keys(), reverse=True):
        path = os.path.join(RAW_DIR, f"h1b_{year}.csv")
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  {year}: found ({size:.1f} MB)")
        else:
            print(f"  {year}: MISSING — download from uscis.gov/archive/h-1b-employer-data-hub-files")