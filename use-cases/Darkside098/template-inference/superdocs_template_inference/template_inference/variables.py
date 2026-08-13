"""Variable detection and semantic role inference."""

import re
from collections import Counter
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


# M6 Enhancement Functions


def extract_variable_values(
    variable_candidates: dict[str, dict], profiles: list[DocumentProfile]
) -> dict[str, list[str]]:
    """Extract actual observed values for variable candidates from profiles.

    Args:
        variable_candidates: Dict mapping variable names to candidate info.
        profiles: List of DocumentProfile objects.

    Returns:
        Dict mapping {variable_name: [observed values from documents]}.
    """
    variable_values: dict[str, list[str]] = {}

    for var_name in variable_candidates.keys():
        values = []
        for profile in profiles:
            if var_name.lower() in profile.content.vocabulary:
                # The vocabulary key is the actual value observed
                values.append(var_name)
        variable_values[var_name] = sorted(list(set(values)))  # Deduplicate, sort for determinism

    return variable_values


def infer_variable_type(values: list[str]) -> tuple[str, dict]:
    """Infer type from observed values.

    Args:
        values: List of observed values for a variable.

    Returns:
        Tuple of (inferred_type, metadata_dict).
        Type: string|enum|date|datetime|time|currency|integer|email|phone|boolean
    """
    if not values:
        return "string", {"is_enum": False}

    # Patterns for type detection
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    # Phone: Must have 10+ digits and contain hyphens, dots, or parens (not just plain numbers)
    phone_pattern = r"^(\+[\d\s-]*|[\d\s().-]*\d[\d\s().-]*\d[\d\s().-]*\d[\d\s().-]*\d)$"
    date_pattern = r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$"
    datetime_pattern = r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}[\s]+\d{1,2}:\d{2}(:\d{2})?$"
    time_pattern = r"^\d{1,2}:\d{2}(:\d{2})?\s?(AM|PM|am|pm)?$"
    # Currency: requires dollar sign, comma, decimal, or explicit currency code
    currency_pattern = r"^\$[\d,]+\.?\d*$|^[\d,]+\.?\d+\s?(USD|GBP|EUR|INR)$"
    integer_pattern = r"^-?\d+$"
    boolean_values = {"true", "false", "yes", "no", "1", "0"}

    # Analyze all values
    all_emails = all(re.match(email_pattern, str(v)) for v in values)
    all_integers = all(re.match(integer_pattern, str(v)) for v in values if v)
    all_datetimes = all(re.match(datetime_pattern, str(v)) for v in values if v)
    all_dates = all(re.match(date_pattern, str(v)) for v in values if v)
    all_times = all(re.match(time_pattern, str(v)) for v in values if v)
    all_currency = all(re.match(currency_pattern, str(v)) for v in values if v)
    all_booleans = all(str(v).lower() in boolean_values for v in values)

    # Phone requires more than just digits: check formatting chars
    all_phones = False
    if not all_integers and len(values) > 0:
        # Only consider phone if values have formatting chars (-, ., parens, +, spaces)
        has_phone_formatting = any(c in "".join(values) for c in "-().+ ")
        all_phones = has_phone_formatting and all(re.match(phone_pattern, str(v)) for v in values if v)

    # Check for enum: limited set of distinct values
    unique_values = set(str(v).lower() for v in values)
    is_enum = len(unique_values) <= 10 and len(unique_values) > 0

    # Type inference (in priority order)
    if all_emails:
        return "email", {"is_enum": False}
    elif all_phones:
        return "phone", {"is_enum": False}
    elif all_datetimes:
        return "datetime", {"is_enum": False}
    elif all_dates:
        return "date", {"is_enum": False}
    elif all_times:
        return "time", {"is_enum": False}
    elif all_currency:
        return "currency", {"is_enum": False}
    elif all_integers:
        return "integer", {"is_enum": is_enum}
    elif all_booleans:
        return "boolean", {"is_enum": True, "enum_values": sorted(list(unique_values))}
    elif is_enum:
        return "enum", {"is_enum": True, "enum_values": sorted(list(unique_values))}
    else:
        return "string", {"is_enum": False}


def infer_variable_metadata(
    variable_name: str, values: list[str], profiles: list[DocumentProfile]
) -> dict:
    """Infer metadata about a variable.

    Args:
        variable_name: Name of the variable.
        values: List of observed values.
        profiles: List of DocumentProfile objects.

    Returns:
        Dict with metadata: frequency, unique_per_document, etc.
    """
    frequency = calculate_variable_frequency(variable_name, profiles)

    # Determine if unique per document
    value_counts = []
    for profile in profiles:
        if variable_name.lower() in profile.content.vocabulary:
            value_counts.append(1)

    unique_per_document = len(value_counts) == len(set(values))

    return {
        "frequency": frequency,
        "unique_per_document": unique_per_document,
        "observed_value_count": len(values),
        "observed_in_documents": len(value_counts),
    }


def link_variable_to_sections(
    variable_name: str, profiles: list[DocumentProfile], section_groups: dict
) -> list[str]:
    """Determine which sections contain a variable.

    Args:
        variable_name: Name of the variable.
        profiles: List of DocumentProfile objects.
        section_groups: Dict of aligned sections from section detection.

    Returns:
        List of section names/patterns containing the variable.
    """
    containing_sections = []

    # For each section group, check if any section contains vocabulary matching variable
    for section_pattern, sections_in_group in section_groups.items():
        # Simplified: check if variable appears in documents that have this section
        for profile in profiles:
            if variable_name.lower() in profile.content.vocabulary:
                # Check if this profile has any section in this group
                profile_section_titles = {
                    (s.title or "").lower() for s in profile.sections
                }
                if any(s.title and (s.title or "").lower() for s in sections_in_group):
                    # Found variable in document with this section
                    containing_sections.append(section_pattern)
                    break

    # Deduplicate and sort for determinism
    return sorted(list(set(containing_sections)))
