"""Variable detection and semantic role inference."""

import re
from superdocs_template_inference.models import DocumentProfile


def detect_variables(profiles: list[DocumentProfile]) -> dict[str, dict]:
    """Detect candidate variables from content variations across profiles.

    Args:
        profiles: List of DocumentProfile objects from a single family.

    Returns:
        Mapping {variable_name: {section, values, frequency, confidence}}.
    """
    if len(profiles) < 2:
        # Singleton or empty family: no variation to detect
        return {}

    candidates: dict[str, dict] = {}

    # For each profile, extract content variation
    # This is a simplified approach: compare vocabularies across profiles
    for i, profile_a in enumerate(profiles):
        for profile_b in profiles[i + 1 :]:
            # Find vocabulary differences
            vocab_a = set(profile_a.content.vocabulary.keys())
            vocab_b = set(profile_b.content.vocabulary.keys())

            # Words unique to each profile may indicate variables
            unique_to_a = vocab_a - vocab_b
            unique_to_b = vocab_b - vocab_a

            # Record candidates
            for word in unique_to_a | unique_to_b:
                if word not in candidates:
                    candidates[word] = {
                        "section": "unknown",
                        "values": [],
                        "frequency": 0.0,
                        "confidence": 0.0,
                    }

                if word in unique_to_a and word not in candidates[word]["values"]:
                    candidates[word]["values"].append(word)
                if word in unique_to_b and word not in candidates[word]["values"]:
                    candidates[word]["values"].append(word)

    return candidates


def infer_semantic_role(variable_name: str, context_words: list[str]) -> str:
    """Infer semantic role for a variable using pattern matching.

    Args:
        variable_name: The variable name or value.
        context_words: Surrounding words for context.

    Returns:
        Semantic role string such as "person_name", "salary", "unknown", etc.
    """
    # Convert to lowercase for matching
    var_lower = variable_name.lower()
    context_lower = " ".join(w.lower() for w in context_words)

    # Email pattern
    if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", var_lower):
        return "email"

    # Phone pattern
    if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", var_lower):
        return "phone"

    # Salary/amount pattern (numbers with common currency symbols or context)
    if re.search(r"\$\d+|salary|compensation", context_lower):
        if re.search(r"\d{4,}", var_lower):
            return "salary"

    # Date pattern
    if re.search(
        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        var_lower,
    ):
        return "date"

    # ID pattern
    if re.search(r"^[a-z]?_?id$|employee_id|emp_id", var_lower) or re.search(
        r"\d{4,}", var_lower
    ):
        return "employee_id"

    # Person name context (common first/last names in context or title)
    if re.search(r"name|manager|employee|person", context_lower):
        if len(var_lower.split()) <= 2 and not re.search(r"\d", var_lower):
            return "person_name"

    # Organization/department
    if re.search(r"department|team|organization|company|division", context_lower):
        return "department"

    # Job title
    if re.search(r"title|position|role|job", context_lower):
        return "job_title"

    # Work mode
    if re.search(r"remote|on-site|hybrid|work.mode|location", context_lower):
        return "work_mode"

    # Location
    if re.search(r"location|city|office|address|building", context_lower):
        return "location"

    # Manager
    if re.search(r"manager|supervisor|lead", context_lower):
        return "manager"

    # Default: unknown
    return "unknown"


def calculate_variable_frequency(
    variable_name: str, profiles: list[DocumentProfile]
) -> float:
    """Calculate how frequently a variable appears across documents.

    Args:
        variable_name: The variable name or key value.
        profiles: List of DocumentProfile objects from a single family.

    Returns:
        Frequency as 0.0–1.0.
    """
    if not profiles:
        return 0.0

    count = 0

    for profile in profiles:
        if variable_name.lower() in profile.content.vocabulary:
            count += 1

    return count / len(profiles)
