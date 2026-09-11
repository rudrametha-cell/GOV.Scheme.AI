"""
matcher.py
-----------
SchemeMatch AI - Matching Engine

This module implements a simple, EXPLAINABLE, rule-based weighted scoring
system that compares an entrepreneur's profile against a small prototype
database of government scheme records (schemes.csv).

IMPORTANT (read this before demo / jury questions):
This is NOT machine learning and it does NOT represent official government
eligibility rules. It is a transparent prototype scoring model built for
the Smart India Hackathon MVP, so every point awarded can be explained in
plain language to the user.

Scoring weights (total = 100):
    Category match          = 25 points
    Gender match             = 15 points
    Business type match      = 20 points
    State / location match   = 10 points
    Income compatibility     = 10 points
    Business stage match     = 10 points
    Funding compatibility    = 10 points
"""

import csv
import os

SCHEMES_FILE = os.path.join(os.path.dirname(__file__), "schemes.csv")

# Minimum score a scheme needs to be shown as a "match" at all.
MINIMUM_SCORE_THRESHOLD = 30


def load_schemes():
    """Read schemes.csv and return a list of scheme dictionaries."""
    schemes = []
    with open(SCHEMES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schemes.append(row)
    return schemes


def _values_list(raw_value):
    """Turn a comma-separated CSV cell into a clean list of values."""
    return [v.strip() for v in raw_value.split(",") if v.strip()]


def _safe_int(value, default=0):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def score_scheme(profile, scheme):
    """
    Compare a single scheme record against the user's profile.
    Returns (score, reasons, unmet) where:
        score   -> integer 0-100
        reasons -> list of short strings explaining points awarded
        unmet   -> list of short strings explaining points NOT awarded
    """
    score = 0
    reasons = []
    unmet = []

    # 1. Category match - 25 points
    scheme_categories = _values_list(scheme.get("category", "All"))
    if "All" in scheme_categories or profile["category"] in scheme_categories:
        score += 25
        reasons.append("Category appears compatible with this scheme")
    else:
        unmet.append("Category focus differs from this scheme")

    # 2. Gender match - 15 points
    scheme_genders = _values_list(scheme.get("gender", "All"))
    if "All" in scheme_genders or profile["gender"] in scheme_genders:
        score += 15
        reasons.append("Gender criteria is compatible")
    else:
        unmet.append("Gender-specific focus differs from your profile")

    # 3. Business type match - 20 points
    scheme_business_types = _values_list(scheme.get("business_type", "All"))
    if "All" in scheme_business_types or profile["business_type"] in scheme_business_types:
        score += 20
        reasons.append("Business activity is relevant to this scheme")
    else:
        unmet.append("Business activity is not a primary focus of this scheme")

    # 4. State / location match - 10 points
    scheme_states = _values_list(scheme.get("state", "All"))
    if "All" in scheme_states or profile["state"] in scheme_states:
        score += 10
        reasons.append("Available in your state")
    else:
        unmet.append("Primarily associated with a different state")

    # 5. Income compatibility - 10 points
    income_ceiling = _safe_int(scheme.get("income", 0))
    user_income = _safe_int(profile.get("income", 0))
    if income_ceiling == 0 or user_income <= income_ceiling:
        score += 10
        reasons.append("Income profile is within a compatible range")
    else:
        unmet.append("Annual income is higher than this scheme typically targets")

    # 6. Business stage match - 10 points
    scheme_stages = _values_list(scheme.get("business_stage", "All"))
    if "All" in scheme_stages or profile["business_stage"] in scheme_stages:
        score += 10
        reasons.append(f"{profile['business_stage']} profile is relevant")
    else:
        unmet.append("Business stage differs from this scheme's usual focus")

    # 7. Funding compatibility - 10 points
    funding_ceiling = _safe_int(scheme.get("funding_need", 0))
    user_funding = _safe_int(profile.get("funding_required", 0))
    if funding_ceiling == 0 or user_funding <= funding_ceiling:
        score += 10
        reasons.append("Funding requirement is compatible")
    else:
        unmet.append("Requested funding exceeds this scheme's typical support amount")

    return score, reasons, unmet


def _match_label(score):
    if score >= 80:
        return "Highly Relevant"
    if score >= 60:
        return "Good Match"
    return "Potential Match"


def get_recommendations(profile, top_n=6):
    """
    Main entry point used by the Flask app.
    profile: dict with keys age, gender, category, state, income,
             business_type, business_stage, funding_required
    Returns a list of scheme result dictionaries, ranked highest score first.
    """
    schemes = load_schemes()
    results = []

    for scheme in schemes:
        score, reasons, unmet = score_scheme(profile, scheme)
        if score < MINIMUM_SCORE_THRESHOLD:
            continue

        results.append({
            "id": scheme.get("id"),
            "scheme_name": scheme.get("scheme_name"),
            "match_score": score,
            "match_label": _match_label(score),
            "description": scheme.get("description", ""),
            "reasons": reasons,
            "unmet": unmet,
            "documents": _values_list(scheme.get("documents", "")),
            "official_source": scheme.get("official_source") or "Official source to be verified.",
        })

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results[:top_n]