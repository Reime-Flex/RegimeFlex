# engine/price_source_check.py
from __future__ import annotations
from typing import Dict, Any


def check_price_source(crumbs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal, assumption-free check of price_source metadata.

    We deliberately DO NOT assume any particular keys inside price_source.
    We only check:

    - Is price_source present in crumbs?
    - Is it a non-empty dict?

    Returns:
      {
        "ok": bool,
        "reason": str | None,
      }
    """
    ps = crumbs.get("price_source", None)

    if ps is None:
        return {
            "ok": False,
            "reason": "price_source missing from breadcrumbs",
        }

    if not isinstance(ps, dict):
        return {
            "ok": False,
            "reason": f"price_source is not a dict (type={type(ps).__name__})",
        }

    if not ps:
        return {
            "ok": False,
            "reason": "price_source dict is empty",
        }

    # If we got here, we only assert that it's a non-empty dict.
    return {
        "ok": True,
        "reason": None,
    }


