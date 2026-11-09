"""Download the Upworthy Research Archive samples used in this project from OSF
and verify their checksums.

Usage: python scripts/download_data.py
The holdout sample is deliberately not downloaded.
"""
import urllib.request

from abtest.data import OSF_URLS, RAW_DIR, SHA256, raw_path, sha256


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for sample, url in OSF_URLS.items():
        dest = raw_path(sample)
        if not dest.exists():
            print(f"downloading {sample} sample -> {dest.name}")
            tmp = dest.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(dest)
        digest = sha256(dest)
        if digest != SHA256[sample]:
            raise SystemExit(f"{dest.name}: checksum mismatch\n  got      {digest}\n  expected {SHA256[sample]}")
        print(f"verified {dest.name} ({dest.stat().st_size / 1e6:.1f} MB, sha256 {digest[:12]}…)")


if __name__ == "__main__":
    main()
