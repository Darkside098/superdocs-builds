"""Section alignment, ordering, and presence inference."""

from superdocs_template_inference.models import DetectedSection, DocumentProfile


def align_sections(profiles: list[DocumentProfile]) -> dict[str, list[DetectedSection]]:
    """Align sections across profiles by normalized title/pattern.

    Args:
        profiles: List of DocumentProfile objects from a single family.

    Returns:
        Mapping {section_pattern: [DetectedSection, ...]} for aligned sections.
    """
    if not profiles:
        return {}

    # Normalize and group sections by title pattern
    section_groups: dict[str, list[DetectedSection]] = {}

    for profile in profiles:
        for section in profile.sections:
            # Normalize section title for comparison
            normalized_title = normalize_section_title(section.title or "")

            if normalized_title not in section_groups:
                section_groups[normalized_title] = []

            section_groups[normalized_title].append(section)

    return section_groups


def normalize_section_title(title: str | None) -> str:
    """Normalize section title for comparison.

    Args:
        title: Section title or heading text.

    Returns:
        Normalized title for comparison.
    """
    if not title:
        return "untitled"

    # Convert to lowercase and strip whitespace
    normalized = title.lower().strip()

    # Remove extra whitespace
    normalized = " ".join(normalized.split())

    return normalized


def infer_section_ordering(profiles: list[DocumentProfile]) -> list[str]:
    """Infer the dominant section order across documents.

    Args:
        profiles: List of DocumentProfile objects from a single family.

    Returns:
        Ordered list of normalized section titles.
    """
    if not profiles:
        return []

    # Collect all section orders
    orders = []

    for profile in profiles:
        section_order = [
            normalize_section_title(s.title or "") for s in profile.sections
        ]
        if section_order:
            orders.append(section_order)

    if not orders:
        return []

    # For simplicity, use the order from the first document
    # This is conservative and deterministic
    return orders[0]


def calculate_section_presence_frequency(
    section_pattern: str, profiles: list[DocumentProfile], section_groups: dict[str, list]
) -> float:
    """Calculate how frequently a section appears across documents.

    Args:
        section_pattern: Normalized section title.
        profiles: List of DocumentProfile objects from a single family.
        section_groups: Grouped sections by pattern.

    Returns:
        Frequency as 0.0–1.0.
    """
    if not profiles:
        return 0.0

    if section_pattern not in section_groups:
        return 0.0

    return len(section_groups[section_pattern]) / len(profiles)


def classify_section_presence(frequency: float) -> str:
    """Classify section presence based on frequency.

    Args:
        frequency: Presence frequency 0.0–1.0.

    Returns:
        "always" if frequency >= 0.95
        "usually" if frequency >= 0.6
        "optional" if frequency < 0.6
    """
    if frequency >= 0.95:
        return "always"
    if frequency >= 0.6:
        return "usually"
    return "optional"


def get_section_content_representation(sections: list[DetectedSection]) -> str:
    """Get a normalized content representation for aligned sections.

    Args:
        sections: List of DetectedSection objects at the same logical position.

    Returns:
        Summary representation of section content.
    """
    if not sections:
        return ""

    # Extract the most common title
    titles = [s.title for s in sections if s.title]
    if titles:
        return titles[0]

    return f"Section (blocks: {sections[0].block_count if sections else 0})"
