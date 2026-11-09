"""Run provenance: enough context to say exactly what produced a result."""
from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata

from .data import RAW_DIR, ROOT, SHA256, raw_path

PACKAGES = ["numpy", "pandas", "scipy", "statsmodels", "matplotlib"]


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect(samples=("exploratory",), seeds: dict | None = None) -> dict:
    """Git state, environment and input checksums for a results file.

    The checksums recorded are the *expected* ones; ``data.load_packages``
    refuses to load a file that does not match, so they describe what ran."""
    status = _git("status", "--porcelain")
    return {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(status) if status is not None else None,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {p: metadata.version(p) for p in PACKAGES},
        "inputs": {s: {"file": str(raw_path(s).relative_to(RAW_DIR.parent.parent)), "sha256": SHA256[s]}
                   for s in samples},
        "seeds": seeds or {},
    }
