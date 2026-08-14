"""Regeneration utilities for source-specific DOCX output from inferred templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docx import Document

from superdocs_template_inference.models import Document as NormalizedDocument, ParagraphBlock, TableBlock
from superdocs_template_inference.template_inference.result import (
    ConditionalRule,
    TemplateInferenceResult,
    TemplateSection,
)


@dataclass
class RegenerationResult:
    """Structured outcome for a DOCX regeneration operation."""

    output_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    included_sections: list[str] = field(default_factory=list)
    omitted_conditional_sections: list[str] = field(default_factory=list)
    substituted_variables: dict[str, str] = field(default_factory=dict)
    succeeded: bool = False


class DocxRegenerator:
    """Generate a source-specific DOCX from an inferred template."""

    def regenerate(
        self,
        template: TemplateInferenceResult,
        values: dict[str, Any],
        *,
        source_document: NormalizedDocument | None = None,
        output_path: str | None = None,
    ) -> RegenerationResult:
        """Regenerate a DOCX using the inferred template and explicit values.

        The regeneration layer is intentionally conservative: if the inferred template
        does not contain enough safe content for a section, the section is skipped and
        a warning is recorded rather than inventing content.
        """
        result = RegenerationResult(output_path=output_path)

        if not template:
            result.errors.append("Template inference result is missing.")
            return result

        ordered_sections = sorted(template.sections, key=lambda section: section.order)
        if not ordered_sections:
            result.errors.append("Template has no sections to regenerate.")
            return result

        if output_path is None:
            output_path = str(Path.cwd() / "regenerated_document.docx")
            result.output_path = output_path

        doc = Document()
        included_sections: list[str] = []
        omitted_conditional_sections: list[str] = []

        for section in ordered_sections:
            if section.inferred_type == "CONDITIONAL" or section.presence_type == "conditional":
                should_include = self._should_include_conditional_section(section, template.conditional_rules, values)
                if not should_include:
                    omitted_conditional_sections.append(section.title_or_pattern)
                    continue

            try:
                rendered = self._render_section(section, values, source_document=source_document)
            except ValueError as exc:
                result.errors.append(f"Missing variable value for section '{section.title_or_pattern}': {exc}")
                continue

            if rendered is None:
                result.warnings.append(
                    f"Section '{section.title_or_pattern}' has insufficient information for safe regeneration; "
                    "the template lacks safe content and regeneration cannot proceed without inventing details."
                )
                continue

            if rendered:
                self._add_rendered_content(doc, rendered)
                included_sections.append(section.title_or_pattern)

        if result.warnings and not included_sections:
            result.errors.append("No safe content could be regenerated from the template.")
        if not result.errors and not included_sections:
            result.errors.append("No sections were regenerated from the template.")

        doc.save(output_path)
        result.included_sections = included_sections
        result.omitted_conditional_sections = omitted_conditional_sections

        if result.warnings and included_sections:
            result.errors.append("Regeneration completed with warnings; some content was skipped due to insufficient or unsafe template information.")

        result.succeeded = not result.errors

        if Path(output_path).exists() is False:
            result.errors.append(f"Regenerated DOCX could not be saved to '{output_path}'.")
            result.succeeded = False

        return result

    def _render_section(
        self,
        section: TemplateSection,
        values: dict[str, Any],
        *,
        source_document: NormalizedDocument | None,
    ) -> str | None:
        """Render a single section into source-safe text."""
        if section.content_representation:
            content = section.content_representation
            rendered = self._substitute_variables(content, values)
            if rendered is not None:
                return rendered

        fallback_text = self._extract_source_section_text(section, source_document)
        if fallback_text:
            return self._substitute_variables(fallback_text, values)

        return None

    def _safe_to_render(self, section: TemplateSection) -> bool:
        """Only render sections whose content can be represented safely."""
        if section.content_representation is None:
            return False
        if not str(section.content_representation).strip():
            return False
        return True

    def _extract_source_section_text(
        self,
        section: TemplateSection,
        source_document: NormalizedDocument | None,
    ) -> str | None:
        """Best-effort source extraction from a matching heading when available."""
        if source_document is None:
            return None

        target_title = self._normalize_section_label(section.title_or_pattern)
        if not target_title:
            return None

        collected: list[str] = []
        found_heading = False
        for block in source_document.blocks:
            if not isinstance(block, ParagraphBlock):
                continue
            paragraph_text = (block.text or "").strip()
            if not paragraph_text:
                continue

            if block.is_heading:
                normalized_heading = self._normalize_section_label(paragraph_text)
                if normalized_heading == target_title:
                    found_heading = True
                    continue
                if found_heading:
                    break
                continue

            if found_heading:
                if paragraph_text:
                    collected.append(paragraph_text)

        if collected:
            return "\n".join(collected)
        return None

    def _substitute_variables(self, text: str, values: dict[str, Any]) -> str | None:
        """Replace {{variable_name}} tokens with supplied values."""
        if text is None:
            return None

        token_pattern = re.compile(r"\{\{\s*([A-Za-z0-9_\-]+)\s*\}\}")
        missing = []

        def replacer(match: re.Match[str]) -> str:
            variable_name = match.group(1)
            if variable_name not in values:
                missing.append(variable_name)
                return match.group(0)
            value = str(values[variable_name])
            return value

        substituted = token_pattern.sub(replacer, text)
        if missing:
            missing_names = ", ".join(sorted(set(missing)))
            raise ValueError(f"Missing variable value(s): {missing_names}")
        return substituted

    def _should_include_conditional_section(
        self,
        section: TemplateSection,
        rules: list[ConditionalRule],
        values: dict[str, Any],
    ) -> bool:
        """Evaluate a section's conditional rule against supplied values."""
        section_key = self._normalize_section_label(section.title_or_pattern)
        for rule in rules:
            if not rule.condition:
                continue
            rule_key = self._normalize_section_label(rule.target_section)
            if rule_key and rule_key != section_key:
                continue

            field = rule.condition.get("field")
            operator = rule.condition.get("operator", "==")
            expected = rule.condition.get("value")
            if field is None:
                continue

            actual = values.get(field)
            if field not in values:
                return False

            return self._evaluate_operator(actual, operator, expected)

        if section.conditional_info and section.conditional_info.get("condition"):
            condition = section.conditional_info["condition"]
            field = condition.get("field")
            operator = condition.get("operator", "==")
            expected = condition.get("value")
            if field is not None and field in values:
                return self._evaluate_operator(values.get(field), operator, expected)
            return False

        return False

    def _evaluate_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a simple condition against the provided value."""
        actual_text = str(actual).strip().lower()
        expected_text = str(expected).strip().lower()

        op = (operator or "").lower()
        if op in {"==", "=", "equals"}:
            return actual_text == expected_text
        if op in {"!=", "not_equals", "notequals"}:
            return actual_text != expected_text
        if op in {"contains", "in"}:
            return expected_text in actual_text
        if op in {"not_contains", "notin"}:
            return expected_text not in actual_text
        return False

    def _normalize_section_label(self, value: str | None) -> str:
        """Normalize section labels to their canonical slug form."""
        if not value:
            return ""
        normalized = value.strip().lower()
        normalized = normalized.replace("/", " ")
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
        normalized = normalized.strip("_")
        return normalized

    def _add_rendered_content(self, doc: Document, rendered: str) -> None:
        """Add paragraph text to a docx document while preserving simple text blocks."""
        for line in str(rendered).splitlines():
            clean_line = line.strip()
            if clean_line:
                doc.add_paragraph(clean_line)


__all__ = ["DocxRegenerator", "RegenerationResult"]
