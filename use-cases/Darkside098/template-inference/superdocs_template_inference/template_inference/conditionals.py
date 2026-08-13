"""Conditional section and rule inference."""

from __future__ import annotations

from superdocs_template_inference.models import DocumentProfile


def _normalize_condition_value(value: str) -> str:
    """Normalize value strings for deterministic comparison."""
    return " ".join(str(value).strip().lower().split())


def _section_tokens(section_name: str) -> set[str]:
    """Extract normalized token set from a section title for noise filtering."""
    if not section_name:
        return set()
    return {_normalize_condition_value(token) for token in section_name.split()}


def _is_generic_condition_token(token: str) -> bool:
    """Filter obvious section-title noise words from conditional candidates."""
    generic = {
        "section",
        "sections",
        "work",
        "setup",
        "details",
        "summary",
        "information",
        "content",
        "header",
        "document",
        "general",
        "addendum",
        "custom",
        "notes",
        "info",
        "overview",
        "details",
    }
    return token in generic


def infer_conditional_rules(
    profiles: list[DocumentProfile], optional_sections: list[str]
) -> dict[str, dict]:
    """Infer conditional rules for optional sections.

    A section is only promoted to conditional when an observed field/value pattern
    is repeated in documents containing the section and absent from those without it.
    """
    conditional_rules: dict[str, dict] = {}

    if not optional_sections or len(profiles) < 2:
        return conditional_rules

    for section_name in sorted(set(optional_sections), key=lambda s: s.lower()):
        docs_with_section = []
        docs_without_section = []

        for profile in profiles:
            has_section = any(
                s.title and _normalize_condition_value(s.title) == _normalize_condition_value(section_name)
                for s in profile.sections
            )
            if has_section:
                docs_with_section.append(profile)
            else:
                docs_without_section.append(profile)

        if not docs_with_section or not docs_without_section:
            continue

        condition = find_section_condition(
            docs_with_section, docs_without_section, section_name
        )
        if not condition:
            continue

        conditional_rules[section_name] = {
            "condition": {
                "field": condition["field"],
                "operator": condition["operator"],
                "value": condition["value"],
            },
            "evidence": {
                "docs_with_section": [d.document_id for d in docs_with_section],
                "docs_without_section": [d.document_id for d in docs_without_section],
                "observed_field": condition["field"],
                "observed_value": condition["value"],
                "with_frequency": condition["with_frequency"],
                "without_frequency": condition["without_frequency"],
            },
            "confidence": float(condition["confidence"]),
            "status": "inferred",
        }

    return conditional_rules


def find_section_condition(
    docs_with_section: list[DocumentProfile],
    docs_without_section: list[DocumentProfile],
    section_name: str,
) -> dict | None:
    """Try to find a strong, evidence-backed condition that predicts section presence.

    Returns a dict with field/operator/value and confidence when a deterministic
    pattern is observed; otherwise returns None.
    """
    if not docs_with_section or not docs_without_section:
        return None

    section_tokens = _section_tokens(section_name)
    candidate_scores: list[tuple[float, str, int, int, float, float, str]] = []
    seen_terms: set[str] = set()

    for profile in docs_with_section + docs_without_section:
        for term in profile.content.vocabulary:
            normalized = _normalize_condition_value(term)
            if not normalized:
                continue
            if normalized in section_tokens and _is_generic_condition_token(normalized):
                continue
            if normalized in seen_terms:
                continue
            seen_terms.add(normalized)

            with_count = sum(
                1 for p in docs_with_section if normalized in p.content.vocabulary
            )
            without_count = sum(
                1 for p in docs_without_section if normalized in p.content.vocabulary
            )
            with_total = len(docs_with_section)
            without_total = len(docs_without_section)

            with_ratio = with_count / with_total if with_total else 0.0
            without_ratio = without_count / without_total if without_total else 0.0

            # Require repeated evidence: strong presence in docs with the section,
            # and weak presence in docs without it.
            if with_count < max(1, with_total // 2):
                continue
            if with_ratio < 0.6 or without_ratio > 0.35:
                continue

            # Score combines predictive strength and support.
            score = (
                0.55 * (with_ratio - without_ratio)
                + 0.25 * with_ratio
                + 0.20 * (1.0 - without_ratio)
            )
            if score < 0.35:
                continue

            operator = "contains" if " " in normalized else "equals"
            candidate_scores.append(
                (score, normalized, with_count, without_count, with_ratio, without_ratio, operator)
            )

    if not candidate_scores:
        return None

    # Deterministic tie-break: highest score, then higher support, then lexical order.
    candidate_scores.sort(
        key=lambda item: (
            item[0],
            item[2],
            -item[3],
            item[1],
        ),
        reverse=True,
    )
    score, value, with_count, without_count, with_ratio, without_ratio, operator = candidate_scores[0]

    confidence = min(0.99, max(0.5, round(score, 3)))
    return {
        "field": "variable_observation",
        "operator": operator,
        "value": value,
        "with_frequency": round(with_ratio, 3),
        "without_frequency": round(without_ratio, 3),
        "confidence": confidence,
    }
