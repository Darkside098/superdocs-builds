"""Variable detection and semantic role inference."""

import re
from collections import Counter
from superdocs_template_inference.models import DocumentProfile

_COMMON_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "he", "her", "his", "in", "is", "it", "its", "of", "on", "or", "our", "she",
    "that", "the", "their", "them", "there", "they", "this", "to", "we", "were",
    "with", "you", "your", "us", "i", "me", "my", "mine", "was", "will", "would",
    "all", "about", "after", "before", "between", "into", "over", "under", "through",
    "during", "while", "than", "then", "more", "most", "some", "such", "same", "out",
    "off", "up", "down", "also", "just", "not", "no", "yes", "but", "if", "so",
    "too", "very", "much", "many", "make", "made", "offer", "letter", "employment",
    "acceptance", "conditions", "benefits", "details", "work", "welcome", "company",
    "date", "time", "service", "document", "addition", "aboard", "acquisition",
    "affecting", "appropriate", "assistance", "based", "behalf", "support", "value",
    "views", "impact", "people", "issues", "annual", "local", "regional", "global",
    "business"
}

_GENERIC_SECTION_WORDS = {
    "offer", "letter", "employment", "acceptance", "position", "role", "company",
    "technologies", "details", "conditions", "benefits", "welcome", "team", "date",
    "time", "work", "your", "we", "you", "our", "there", "they", "their", "document",
    "support", "service"
}

_FIELD_CONTEXT_HINTS = {
    "name", "email", "phone", "mobile", "telephone", "tel", "title", "role", "position",
    "manager", "supervisor", "reporting", "department", "team", "division",
    "salary", "compensation", "package", "bonus", "benefit", "location", "address",
    "city", "state", "country", "office", "remote", "hybrid", "start", "joining",
    "hire", "commencement", "work", "mode", "type", "level", "employee", "candidate",
    "status", "contract", "period", "approval", "benefits"
}

_VALUE_LIKE_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b"),
    re.compile(r"\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b"),
    re.compile(r"^\$\d|\d+\s*(usd|eur|gbp|inr)$", re.IGNORECASE),
    re.compile(r"^(true|false|yes|no|remote|office|hybrid|full-time|part-time|permanent|temporary)$", re.IGNORECASE),
)


def _normalize_token(value: str) -> str:
    """Normalize a token from vocabulary or heading text."""
    if value is None:
        return ""
    token = str(value).strip().lower()
    token = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", token)
    return token


def _token_in_context(token: str, context_text: str) -> bool:
    """Check for token as a standalone word in a context string."""
    if not token or not context_text:
        return False
    return re.search(rf"\b{re.escape(token)}\b", context_text, flags=re.IGNORECASE) is not None


def _has_value_pattern(token: str) -> bool:
    """Return True for tokens with actual value-like structure."""
    return any(pattern.search(token) for pattern in _VALUE_LIKE_PATTERNS)


def _is_name_like(token: str) -> bool:
    """Return True for likely document-value names rather than common vocabulary."""
    if not token or len(token) < 3 or len(token) > 40:
        return False
    if not token.isalpha():
        return False
    if token in _COMMON_WORDS or token in _GENERIC_SECTION_WORDS:
        return False
    if token.endswith(("ing", "ed", "ly", "tion", "ment", "ness")):
        return False
    return True


def _is_noise_candidate(token: str) -> bool:
    """Reject common English words, generic section labels and boilerplate."""
    if not token or len(token) <= 2:
        return True
    if token.isdigit():
        return True
    if token in _COMMON_WORDS:
        return True
    if token in _GENERIC_SECTION_WORDS:
        return True
    if token.endswith(("ing", "ed", "ly", "tion", "ment", "ness")) and token not in {"remote", "office", "hybrid"}:
        return True
    return False


def _context_supports_variable(profile: DocumentProfile, token: str) -> tuple[bool, str]:
    """Return context evidence for a document field candidate."""
    section_titles = [
        (section.title or "").strip() for section in profile.sections if getattr(section, "title", None)
    ]
    context_text = " ".join(profile.content.heading_texts + section_titles).lower()

    if token in _FIELD_CONTEXT_HINTS:
        return True, "token matches field context keyword"

    if _has_value_pattern(token):
        return True, "token matches value-like pattern"

    if _is_name_like(token):
        return True, "token looks like a document-specific value name"

    if context_text:
        context_words = set(re.findall(r"[a-z][a-z-]+", context_text))
        if any(field_word in context_words for field_word in _FIELD_CONTEXT_HINTS) and token not in _GENERIC_SECTION_WORDS:
            return True, "token appears in field-like section context"

    return False, "no contextual evidence for field-like token"


def _candidate_evidence_for_profile(profile: DocumentProfile, token: str) -> list[str]:
    """Return evidence strings explaining why a token is a supported candidate."""
    supported, reason = _context_supports_variable(profile, token)
    if not supported:
        return []

    evidence = [reason]
    section_titles = [
        (section.title or "").strip() for section in profile.sections if getattr(section, "title", None)
    ]
    context_text = " ".join(profile.content.heading_texts + section_titles)
    if context_text:
        evidence.append(f"context={context_text[:120]}")
    if _has_value_pattern(token):
        evidence.append("value_pattern")
    return evidence


def detect_variables(profiles: list[DocumentProfile]) -> dict[str, dict]:
    """Detect contextual semantic candidates from profile evidence.

    A candidate must have strong field-like evidence from section/heading context or
    actual value patterns. Ordinary vocabulary words and generic nouns are rejected.
    """
    if len(profiles) < 2:
        return {}

    candidate_scores: dict[str, dict] = {}

    for profile in profiles:
        for token, _ in sorted(profile.content.vocabulary.items(), key=lambda item: (-item[1], item[0])):
            normalized = _normalize_token(token)
            if not normalized:
                continue
            if _is_noise_candidate(normalized):
                continue

            supported, _ = _context_supports_variable(profile, normalized)
            if not supported:
                continue

            evidence = _candidate_evidence_for_profile(profile, normalized)
            if not evidence:
                continue

            if normalized not in candidate_scores:
                candidate_scores[normalized] = {
                    "section": "unknown",
                    "values": set(),
                    "frequency": 0.0,
                    "confidence": 0.0,
                    "evidence": set(),
                }

            candidate_scores[normalized]["values"].add(normalized)
            candidate_scores[normalized]["evidence"].update(evidence)
            candidate_scores[normalized]["frequency"] = max(
                candidate_scores[normalized]["frequency"],
                1.0 / len(profiles),
            )

            context_score = 0.6 if normalized in _FIELD_CONTEXT_HINTS or _has_value_pattern(normalized) or _is_name_like(normalized) else 0.35
            candidate_scores[normalized]["confidence"] = max(
                candidate_scores[normalized]["confidence"],
                min(1.0, 0.35 + context_score),
            )

    filtered_candidates: dict[str, dict] = {}
    for name, info in sorted(candidate_scores.items(), key=lambda item: (-item[1]["confidence"], item[0])):
        if info["confidence"] < 0.45:
            continue
        filtered_candidates[name] = {
            "section": "heading_or_section_context",
            "values": sorted(info["values"]),
            "frequency": round(info["frequency"], 3),
            "confidence": round(info["confidence"], 3),
            "evidence": sorted(info["evidence"]),
        }

    return filtered_candidates


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

    This stays conservative: ordinary words do not become enums, and weakly evidenced
    values remain string unless they clearly match a bounded categorical field.
    """
    if not values:
        return "string", {"is_enum": False}

    cleaned_values = [str(v).strip() for v in values if str(v).strip()]
    if not cleaned_values:
        return "string", {"is_enum": False}

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    phone_pattern = r"^(\+[\d\s-]*|[\d\s().-]*\d[\d\s().-]*\d[\d\s().-]*\d[\d\s().-]*\d)$"
    date_pattern = r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$"
    datetime_pattern = r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}[\s]+\d{1,2}:\d{2}(:\d{2})?$"
    time_pattern = r"^\d{1,2}:\d{2}(:\d{2})?\s?(AM|PM|am|pm)?$"
    currency_pattern = r"^\$[\d,]+\.?\d*$|^[\d,]+\.?\d+\s?(USD|GBP|EUR|INR)$"
    integer_pattern = r"^-?\d+$"
    boolean_values = {"true", "false", "yes", "no", "1", "0"}
    enum_values = {
        "remote", "office", "hybrid", "full-time", "part-time", "permanent",
        "temporary", "contract", "fulltime", "parttime", "on-site", "onsite",
        "off-site", "offsite", "yes", "no", "true", "false"
    }

    unique_values = sorted({str(v).lower() for v in cleaned_values})
    normalized_unique = {str(v).lower() for v in cleaned_values}

    all_emails = all(re.match(email_pattern, str(v)) for v in cleaned_values)
    all_integers = all(re.match(integer_pattern, str(v)) for v in cleaned_values)
    all_datetimes = all(re.match(datetime_pattern, str(v)) for v in cleaned_values)
    all_dates = all(re.match(date_pattern, str(v)) for v in cleaned_values)
    all_times = all(re.match(time_pattern, str(v)) for v in cleaned_values)
    all_currency = all(re.match(currency_pattern, str(v)) for v in cleaned_values)
    all_booleans = all(str(v).lower() in boolean_values for v in cleaned_values)

    all_phones = False
    if len(cleaned_values) > 0:
        has_phone_formatting = any(c in "".join(cleaned_values) for c in "-().+ ")
        all_phones = has_phone_formatting and all(re.match(phone_pattern, str(v)) for v in cleaned_values)

    if all_booleans:
        return "boolean", {"is_enum": True, "enum_values": unique_values}

    if len(normalized_unique) <= 8 and normalized_unique and normalized_unique.issubset(enum_values):
        return "enum", {"is_enum": True, "enum_values": unique_values}

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
        return "integer", {"is_enum": False}
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
