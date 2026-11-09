"""Download the Upworthy Research Archive samples used in this project from OSF.

Usage: python scripts/download_data.py
The holdout sample is deliberately not downloaded.
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from abtest.data import OSF_URLS, RAW_DIR  # noqa: E402


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for sample, url in OSF_URLS.items():
        dest = RAW_DIR / f"upworthy-{sample}.csv"
        if dest.exists():
            print(f"already present: {dest.name}")
            continue
        print(f"downloading {sample} sample -> {dest.name}")
        urllib.request.urlretrieve(url, dest)
        print(f"  {dest.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
