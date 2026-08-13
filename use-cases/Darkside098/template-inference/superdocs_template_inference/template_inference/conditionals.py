"""Conditional section and rule inference."""

from superdocs_template_inference.models import DocumentProfile


def infer_conditional_rules(
    profiles: list[DocumentProfile], optional_sections: list[str]
) -> dict[str, dict]:
    """Infer conditional rules for optional sections.

    A section should only be labeled conditional if there is evidence
    connecting presence/absence to an observable variable/condition.

    Args:
        profiles: List of DocumentProfile objects from a single family.
        optional_sections: List of section titles that are optional (varying presence).

    Returns:
        Mapping {section_name: {condition, evidence, confidence}}.
    """
    conditional_rules: dict[str, dict] = {}

    if not optional_sections or len(profiles) < 2:
        return conditional_rules

    # For each optional section, check if presence correlates with variables
    for section_name in optional_sections:
        # Determine which documents have this section
        docs_with_section = []
        docs_without_section = []

        for profile in profiles:
            has_section = any(
                s.title and s.title.lower() == section_name.lower()
                for s in profile.sections
            )
            if has_section:
                docs_with_section.append(profile)
            else:
                docs_without_section.append(profile)

        # If section is present in 0 or all documents, skip
        if not docs_with_section or not docs_without_section:
            continue

        # Check for correlation with observable differences
        condition = find_section_condition(
            docs_with_section, docs_without_section, section_name
        )

        if condition:
            conditional_rules[section_name] = {
                "condition": condition,
                "evidence": {
                    "docs_with_section": [d.document_id for d in docs_with_section],
                    "docs_without_section": [
                        d.document_id for d in docs_without_section
                    ],
                },
                "confidence": 0.7,  # Conservative default
                "status": "inferred",
            }

    return conditional_rules


def find_section_condition(
    docs_with_section: list[DocumentProfile],
    docs_without_section: list[DocumentProfile],
    section_name: str,
) -> dict | None:
    """Try to find an observable condition that explains section presence.

    Args:
        docs_with_section: Profiles that have the section.
        docs_without_section: Profiles that lack the section.
        section_name: The section name being investigated.

    Returns:
        A condition dict {field, operator, value} or None if no clear condition found.
    """
    if not docs_with_section or not docs_without_section:
        return None

    # Collect vocabulary differences
    vocab_with = set()
    for profile in docs_with_section:
        vocab_with.update(profile.content.vocabulary.keys())

    vocab_without = set()
    for profile in docs_without_section:
        vocab_without.update(profile.content.vocabulary.keys())

    # Find words that appear mainly in docs_with but rarely in docs_without
    potential_condition_words = []

    for word in vocab_with:
        with_count = sum(
            1 for p in docs_with_section if word in p.content.vocabulary
        )
        without_count = sum(
            1 for p in docs_without_section if word in p.content.vocabulary
        )

        # Strong signal if word appears in most docs_with and few/none docs_without
        if with_count >= len(docs_with_section) * 0.7 and without_count < len(
            docs_without_section
        ) * 0.3:
            potential_condition_words.append((word, with_count, without_count))

    # Use the strongest signal as the condition
    if potential_condition_words:
        best_word = max(potential_condition_words, key=lambda x: x[1] - x[2])[0]

        return {
            "field": "document_attribute",
            "operator": "contains",
            "value": best_word,
        }

    return None
