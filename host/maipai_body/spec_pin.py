"""Shared commons spec source pin consumed by runtime and repository tooling."""

SPEC_VERSION = "v0.1.208"
SPEC_TAG = f"spec-{SPEC_VERSION}"
SPEC_CHECKOUT = f"commons-tags/spec-{SPEC_TAG}/spec"


def spec_root():
    """The shared spec directory: MAIPAI_SPEC_DIR, then the copy shipped inside the
    installed package, then the vendored snapshot in a checkout, then the pinned
    commons checkout beside the repository."""
    import os
    from pathlib import Path

    configured = os.environ.get("MAIPAI_SPEC_DIR")
    if configured:
        return Path(configured)
    here = Path(__file__).resolve().parent
    for candidate in (here / "_spec", here.parent / "spec-vendor" / "spec"):
        if (candidate / "vocab").is_dir():
            return candidate
    return here.parents[2] / SPEC_CHECKOUT
