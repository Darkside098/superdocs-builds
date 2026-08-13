"""Template inference engine."""

from superdocs_template_inference.clustering.result import FamilyCluster
from superdocs_template_inference.models import DocumentProfile
from superdocs_template_inference.template_inference.conditionals import (
    infer_conditional_rules,
)
from superdocs_template_inference.template_inference.result import (
    ConditionalRule,
    InferenceEvidence,
    TemplateInferenceResult,
    TemplateSection,
    VariableField,
)
from superdocs_template_inference.template_inference.sections import (
    align_sections,
    calculate_section_presence_frequency,
    classify_section_presence,
    get_section_content_representation,
    infer_section_ordering,
    normalize_section_title,
)
from superdocs_template_inference.template_inference.variables import (
    calculate_variable_frequency,
    detect_variables,
    infer_semantic_role,
    extract_variable_values,
    infer_variable_type,
    infer_variable_metadata,
    link_variable_to_sections,
)


class TemplateInferer:
    """Infer templates for document families."""

    def __init__(self):
        """Initialize template inferer."""
        pass

    def infer(
        self, family_cluster: FamilyCluster, profiles_by_id: dict[str, DocumentProfile]
    ) -> TemplateInferenceResult:
        """Infer template for a family cluster.

        Args:
            family_cluster: FamilyCluster containing family membership.
            profiles_by_id: Mapping of document_id to DocumentProfile.

        Returns:
            TemplateInferenceResult with inferred template data.
        """
        # Extract profiles for this family
        family_profiles = [
            profiles_by_id[doc_id] for doc_id in family_cluster.document_ids
        ]

        # Handle edge cases
        if not family_profiles:
            return TemplateInferenceResult(
                family_id=family_cluster.family_id,
                document_ids=family_cluster.document_ids,
                confidence=0.0,
            )

        # Initialize result
        result = TemplateInferenceResult(
            family_id=family_cluster.family_id,
            document_ids=family_cluster.document_ids,
            confidence=family_cluster.confidence,
        )

        # 1. Align sections across family
        section_groups = align_sections(family_profiles)

        # 2. Infer section ordering
        section_order = infer_section_ordering(family_profiles)

        # 3. Build template sections
        inferred_sections = []
        optional_section_names = []

        for idx, normalized_title in enumerate(section_order):
            if normalized_title not in section_groups:
                continue

            sections = section_groups[normalized_title]
            frequency = calculate_section_presence_frequency(
                normalized_title, family_profiles, section_groups
            )
            presence_type = classify_section_presence(frequency)

            if presence_type != "always":
                optional_section_names.append(normalized_title)

            # Determine presence classification
            if frequency >= 0.95:
                inferred_type = "REQUIRED"
            else:
                inferred_type = "OPTIONAL"

            section = TemplateSection(
                section_id=f"section_{idx}",
                title_or_pattern=normalized_title,
                inferred_type=inferred_type,
                order=idx,
                presence_frequency=frequency,
                presence_type=presence_type,
                content_representation=get_section_content_representation(sections),
                confidence=frequency,
                evidence=[
                    InferenceEvidence(
                        evidence_type="section_alignment",
                        source_document_ids=[
                            family_profiles[i].document_id
                            for i in range(len(family_profiles))
                            if any(
                                normalize_section_title(s.title or "")
                                == normalized_title
                                for s in family_profiles[i].sections
                            )
                        ],
                        related_section=normalized_title,
                        observation=f"Section appears in {len(sections)}/{len(family_profiles)} documents",
                        confidence_contribution=frequency,
                    )
                ],
            )

            inferred_sections.append(section)

        result.sections = inferred_sections

        # 4. Detect variables
        candidate_variables = detect_variables(family_profiles)

        # M6: Extract actual values for each variable candidate
        variable_values = extract_variable_values(candidate_variables, family_profiles)

        inferred_variables = []

        for var_name, var_info in candidate_variables.items():
            # Calculate frequency
            frequency = calculate_variable_frequency(var_name, family_profiles)

            # Skip variables that don't vary much
            if frequency < 0.2 or frequency > 0.95:
                continue

            # Infer semantic role
            semantic_role = infer_semantic_role(var_name, [])

            # M6: Extract observed values
            observed_values = variable_values.get(var_name, [])

            # M6: Infer variable type
            inferred_type, type_metadata = infer_variable_type(observed_values)

            # M6: Infer variable metadata
            var_metadata = infer_variable_metadata(var_name, observed_values, family_profiles)

            # M6: Link variable to sections
            section_links = link_variable_to_sections(var_name, family_profiles, section_groups)
            section_context = section_links[0] if section_links else "unknown"

            # Build evidence list
            evidence_list = [
                InferenceEvidence(
                    evidence_type="value_variance",
                    source_document_ids=family_cluster.document_ids,
                    related_variable=var_name,
                    observation=f"Variable appears in {frequency:.1%} of documents",
                    confidence_contribution=frequency,
                )
            ]

            # Add type inference evidence
            if inferred_type != "string":
                evidence_list.append(
                    InferenceEvidence(
                        evidence_type="semantic_pattern_match",
                        source_document_ids=[
                            family_profiles[i].document_id
                            for i in range(len(family_profiles))
                            if var_name.lower() in family_profiles[i].content.vocabulary
                        ],
                        related_variable=var_name,
                        observation=f"Variable values match {inferred_type} pattern",
                        confidence_contribution=0.3,
                    )
                )

            # Confidence calculation
            base_confidence = 0.6 if semantic_role != "unknown" else 0.4
            type_boost = 0.2 if inferred_type != "string" else 0.0
            confidence = min(1.0, base_confidence + type_boost)

            variable = VariableField(
                variable_name=var_name,
                semantic_role=semantic_role,
                section_context=section_context,
                observed_values=observed_values,
                frequency=frequency,
                confidence=confidence,
                evidence=evidence_list,
                # M6 fields
                inferred_type=inferred_type,
                is_enum=type_metadata.get("is_enum", False),
                enum_values=type_metadata.get("enum_values", []),
                unique_per_document=var_metadata.get("unique_per_document", False),
            )

            inferred_variables.append(variable)

        result.variables = inferred_variables

        # 5. Infer conditional rules
        conditional_rules_dict = infer_conditional_rules(
            family_profiles, optional_section_names
        )

        inferred_conditionals = []

        for section_name, rule_data in conditional_rules_dict.items():
            condition = rule_data.get("condition", {})
            evidence_data = rule_data.get("evidence", {})

            conditional = ConditionalRule(
                target_section=section_name,
                condition=condition,
                supporting_evidence=[
                    InferenceEvidence(
                        evidence_type="conditional_correlation",
                        source_document_ids=evidence_data.get(
                            "docs_with_section", []
                        ),
                        related_section=section_name,
                        observation=f"Section presence correlates with condition",
                        confidence_contribution=rule_data.get("confidence", 0.7),
                    )
                ],
                confidence=rule_data.get("confidence", 0.7),
                status=rule_data.get("status", "inferred"),
            )

            inferred_conditionals.append(conditional)

        result.conditional_rules = inferred_conditionals

        # 6. Calculate family-level confidence
        if result.sections:
            avg_section_confidence = sum(s.confidence for s in result.sections) / len(
                result.sections
            )
            result.confidence = (
                0.7 * family_cluster.confidence + 0.3 * avg_section_confidence
            )
        else:
            result.confidence = family_cluster.confidence

        return result
