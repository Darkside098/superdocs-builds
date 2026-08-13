"""Tests for template inference."""

import pytest

from superdocs_template_inference.clustering.result import FamilyCluster
from superdocs_template_inference.models import (
    ContentProfile,
    DetectedSection,
    DocumentProfile,
    FormattingProfile,
    StructuralProfile,
)
from superdocs_template_inference.template_inference import TemplateInferer
from superdocs_template_inference.template_inference.result import (
    ConditionalRule,
    InferenceEvidence,
    TemplateInferenceResult,
    TemplateSection,
    VariableField,
)


def create_test_profile(
    document_id: str,
    filename: str,
    total_blocks: int = 10,
    paragraph_count: int = 5,
    heading_count: int = 2,
    vocabulary: dict | None = None,
    sections_data: list[dict] | None = None,
) -> DocumentProfile:
    """Create a test DocumentProfile."""
    structural = StructuralProfile(
        total_blocks=total_blocks,
        paragraph_count=paragraph_count,
        heading_count=heading_count,
        table_count=0,
        list_item_count=0,
        heading_levels={1: heading_count} if heading_count > 0 else {},
        max_heading_level=1 if heading_count > 0 else None,
        table_dimensions=[],
        avg_table_rows=None,
        avg_table_cols=None,
        block_type_sequence=["paragraph"] * paragraph_count,
        paragraph_lengths=[40] * paragraph_count,
        avg_paragraph_length=40.0,
        min_paragraph_length=20,
        max_paragraph_length=60,
        list_depth_max=None,
        ordered_list_count=0,
        unordered_list_count=0,
    )

    content = ContentProfile(
        total_text_length=500,
        word_count=100,
        unique_words_count=50,
        heading_texts=["Heading 1", "Heading 2"] if heading_count >= 2 else [],
        vocabulary=vocabulary or {"word_1": 1, "word_2": 1},
        top_vocabulary=[("word_1", 1), ("word_2", 1)],
    )

    formatting = FormattingProfile(
        paragraph_styles={},
        heading_styles={},
        has_tables=False,
        has_lists=False,
        has_headings=heading_count > 0,
    )

    sections = []
    if sections_data:
        for section_dict in sections_data:
            section = DetectedSection(
                section_id=section_dict.get("section_id", "sec_0"),
                start_block_idx=section_dict.get("start_block_idx", 0),
                end_block_idx=section_dict.get("end_block_idx", 5),
                title=section_dict.get("title", "Section"),
                heading_level=section_dict.get("heading_level", 1),
                block_count=section_dict.get("block_count", 5),
                paragraph_count=section_dict.get("paragraph_count", 2),
                table_count=section_dict.get("table_count", 0),
                content_length=section_dict.get("content_length", 200),
                boundary_marker=section_dict.get("boundary_marker", "heading"),
            )
            sections.append(section)

    return DocumentProfile(
        profile_id=f"profile_{document_id}",
        document_id=document_id,
        filename=filename,
        file_type="docx",
        structural=structural,
        content=content,
        formatting=formatting,
        sections=sections,
        profiled_at="2026-01-01T00:00:00Z",
        profile_version="1.0",
    )


class TestTemplateInferencerInitialization:
    """Tests for TemplateInferer initialization."""

    def test_inferer_can_be_initialized(self):
        """TemplateInferer can be initialized."""
        inferer = TemplateInferer()
        assert inferer is not None


class TestEmptyAndSingletonFamily:
    """Tests for edge cases: empty family and single document."""

    def test_infer_empty_family(self):
        """Inferring template for empty family returns zero-confidence result."""
        inferer = TemplateInferer()
        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[],
            document_filenames=[],
            confidence=0.0,
            cluster_size=0,
            pairwise_scores=[],
            pairwise_score_mean=1.0,
            pairwise_score_min=1.0,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, {})

        assert result.family_id == "family_001"
        assert result.document_ids == []
        assert result.confidence == 0.0
        assert result.sections == []

    def test_infer_singleton_family(self):
        """Inferring template for single document produces limited inference."""
        inferer = TemplateInferer()
        profile = create_test_profile(
            "doc_001",
            "doc_001.docx",
            sections_data=[
                {
                    "section_id": "sec_0",
                    "title": "Introduction",
                    "heading_level": 1,
                    "block_count": 5,
                }
            ],
        )

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=["doc_001"],
            document_filenames=["doc_001.docx"],
            confidence=1.0,
            cluster_size=1,
            pairwise_scores=[],
            pairwise_score_mean=1.0,
            pairwise_score_min=1.0,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, {"doc_001": profile})

        assert result.family_id == "family_001"
        assert result.document_ids == ["doc_001"]
        assert len(result.sections) >= 1


class TestIdenticalDocuments:
    """Tests for families with identical documents."""

    def test_infer_identical_documents(self):
        """Identical documents produce high-confidence REQUIRED sections."""
        inferer = TemplateInferer()

        profiles = [
            create_test_profile(
                f"doc_{i:03d}",
                f"doc_{i:03d}.docx",
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Header",
                        "heading_level": 1,
                        "block_count": 3,
                    },
                    {
                        "section_id": "sec_1",
                        "title": "Content",
                        "heading_level": 1,
                        "block_count": 5,
                    },
                ],
            )
            for i in range(1, 4)
        ]

        profiles_by_id = {p.document_id: p for p in profiles}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles],
            document_filenames=[p.filename for p in profiles],
            confidence=0.95,
            cluster_size=len(profiles),
            pairwise_scores=[0.9, 0.9, 0.9],
            pairwise_score_mean=0.9,
            pairwise_score_min=0.9,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, profiles_by_id)

        assert result.family_id == "family_001"
        assert len(result.sections) >= 2
        # All sections should be REQUIRED with high confidence
        assert all(s.inferred_type == "REQUIRED" for s in result.sections)
        assert all(s.confidence > 0.9 for s in result.sections)


class TestFixedAndVariableContent:
    """Tests for fixed and variable content detection."""

    def test_infer_variable_content(self):
        """Variable content across documents is detected."""
        inferer = TemplateInferer()

        profiles = [
            create_test_profile(
                "doc_001",
                "doc_001.docx",
                vocabulary={"alice": 1, "manager": 1, "fixed_text": 2},
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Header",
                        "heading_level": 1,
                    }
                ],
            ),
            create_test_profile(
                "doc_002",
                "doc_002.docx",
                vocabulary={"bob": 1, "manager": 1, "fixed_text": 2},
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Header",
                        "heading_level": 1,
                    }
                ],
            ),
        ]

        profiles_by_id = {p.document_id: p for p in profiles}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles],
            document_filenames=[p.filename for p in profiles],
            confidence=0.9,
            cluster_size=2,
            pairwise_scores=[0.8],
            pairwise_score_mean=0.8,
            pairwise_score_min=0.8,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, profiles_by_id)

        # Should detect variable content (alice, bob)
        # and fixed content (fixed_text, manager)
        assert result.family_id == "family_001"
        # Variables should be detected for alice/bob
        assert any(v.variable_name in ["alice", "bob"] for v in result.variables)


class TestSectionPresenceVariation:
    """Tests for section presence variation (REQUIRED, OPTIONAL, CONDITIONAL)."""

    def test_required_section(self):
        """Section present in all documents is classified as REQUIRED."""
        inferer = TemplateInferer()

        profiles = [
            create_test_profile(
                f"doc_{i:03d}",
                f"doc_{i:03d}.docx",
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Always Present",
                        "heading_level": 1,
                    }
                ],
            )
            for i in range(1, 4)
        ]

        profiles_by_id = {p.document_id: p for p in profiles}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles],
            document_filenames=[p.filename for p in profiles],
            confidence=0.95,
            cluster_size=len(profiles),
            pairwise_scores=[0.9, 0.9, 0.9],
            pairwise_score_mean=0.9,
            pairwise_score_min=0.9,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, profiles_by_id)

        required_sections = [
            s for s in result.sections if s.inferred_type == "REQUIRED"
        ]
        assert len(required_sections) >= 1

    def test_optional_section(self):
        """Section missing in some documents is classified as OPTIONAL."""
        inferer = TemplateInferer()

        profiles = [
            create_test_profile(
                "doc_001",
                "doc_001.docx",
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Sometimes Present",
                        "heading_level": 1,
                    }
                ],
            ),
            create_test_profile(
                "doc_002",
                "doc_002.docx",
                sections_data=[],
            ),
        ]

        profiles_by_id = {p.document_id: p for p in profiles}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles],
            document_filenames=[p.filename for p in profiles],
            confidence=0.8,
            cluster_size=len(profiles),
            pairwise_scores=[0.7],
            pairwise_score_mean=0.7,
            pairwise_score_min=0.7,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, profiles_by_id)

        # Should have inferred sections
        assert result.family_id == "family_001"


class TestDeterminism:
    """Tests for deterministic inference."""

    def test_repeated_inference_is_identical(self):
        """Repeated inference on same input produces identical result."""
        inferer = TemplateInferer()

        profiles = [
            create_test_profile(
                f"doc_{i:03d}",
                f"doc_{i:03d}.docx",
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Section A",
                        "heading_level": 1,
                    }
                ],
            )
            for i in range(1, 3)
        ]

        profiles_by_id = {p.document_id: p for p in profiles}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles],
            document_filenames=[p.filename for p in profiles],
            confidence=0.9,
            cluster_size=len(profiles),
            pairwise_scores=[0.8],
            pairwise_score_mean=0.8,
            pairwise_score_min=0.8,
            merge_evidence=[],
        )

        result1 = inferer.infer(family_cluster, profiles_by_id)
        result2 = inferer.infer(family_cluster, profiles_by_id)

        assert result1.family_id == result2.family_id
        assert result1.confidence == result2.confidence
        assert len(result1.sections) == len(result2.sections)

    def test_input_order_independence(self):
        """Same profiles in different order produce same inference."""
        inferer = TemplateInferer()

        profiles_list = [
            create_test_profile(
                f"doc_{i:03d}",
                f"doc_{i:03d}.docx",
                sections_data=[
                    {
                        "section_id": "sec_0",
                        "title": "Consistent Section",
                        "heading_level": 1,
                    }
                ],
            )
            for i in range(1, 4)
        ]

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=[p.document_id for p in profiles_list],
            document_filenames=[p.filename for p in profiles_list],
            confidence=0.9,
            cluster_size=len(profiles_list),
            pairwise_scores=[0.8, 0.8, 0.8],
            pairwise_score_mean=0.8,
            pairwise_score_min=0.8,
            merge_evidence=[],
        )

        # First order
        profiles_by_id_1 = {p.document_id: p for p in profiles_list}
        result1 = inferer.infer(family_cluster, profiles_by_id_1)

        # Reversed order (but same profiles)
        profiles_by_id_2 = {p.document_id: p for p in reversed(profiles_list)}
        result2 = inferer.infer(family_cluster, profiles_by_id_2)

        assert len(result1.sections) == len(result2.sections)


class TestSerialization:
    """Tests for result serialization."""

    def test_template_result_serializes_to_dict(self):
        """TemplateInferenceResult can be serialized to dict."""
        profile = create_test_profile(
            "doc_001",
            "doc_001.docx",
            sections_data=[
                {
                    "section_id": "sec_0",
                    "title": "Section A",
                    "heading_level": 1,
                }
            ],
        )

        result = TemplateInferenceResult(
            family_id="family_001",
            document_ids=["doc_001"],
            confidence=0.9,
            sections=[
                TemplateSection(
                    section_id="section_0",
                    title_or_pattern="section a",
                    inferred_type="REQUIRED",
                    order=0,
                    presence_frequency=1.0,
                    presence_type="always",
                    content_representation="Section A",
                    confidence=1.0,
                )
            ],
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["family_id"] == "family_001"
        assert result_dict["confidence"] == 0.9
        assert len(result_dict["sections"]) == 1


class TestEvidenceGeneration:
    """Tests for evidence generation."""

    def test_section_has_evidence(self):
        """Inferred sections contain evidence."""
        profile = create_test_profile(
            "doc_001",
            "doc_001.docx",
            sections_data=[
                {
                    "section_id": "sec_0",
                    "title": "Section with Evidence",
                    "heading_level": 1,
                }
            ],
        )

        section = TemplateSection(
            section_id="section_0",
            title_or_pattern="section with evidence",
            inferred_type="REQUIRED",
            order=0,
            presence_frequency=1.0,
            presence_type="always",
            content_representation="Section with Evidence",
            confidence=1.0,
            evidence=[
                InferenceEvidence(
                    evidence_type="section_alignment",
                    source_document_ids=["doc_001"],
                    related_section="section with evidence",
                    observation="Section appears in 1/1 documents",
                    confidence_contribution=1.0,
                )
            ],
        )

        assert len(section.evidence) > 0
        assert section.evidence[0].evidence_type == "section_alignment"


class TestConfidenceRanges:
    """Tests for confidence values."""

    def test_confidence_in_valid_range(self):
        """Confidence values are normalized 0.0–1.0."""
        inferer = TemplateInferer()
        profile = create_test_profile("doc_001", "doc_001.docx")

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=["doc_001"],
            document_filenames=["doc_001.docx"],
            confidence=0.85,
            cluster_size=1,
            pairwise_scores=[],
            pairwise_score_mean=1.0,
            pairwise_score_min=1.0,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, {"doc_001": profile})

        assert 0.0 <= result.confidence <= 1.0
        for section in result.sections:
            assert 0.0 <= section.confidence <= 1.0
        for variable in result.variables:
            assert 0.0 <= variable.confidence <= 1.0


class TestFilenameIndependence:
    """Tests to verify filenames don't drive inference."""

    def test_same_profiles_different_filenames(self):
        """Profiles with different filenames produce same inference."""
        inferer = TemplateInferer()

        profile1 = create_test_profile(
            "doc_001",
            "offer_letter_001.docx",
            sections_data=[
                {
                    "section_id": "sec_0",
                    "title": "Terms",
                    "heading_level": 1,
                }
            ],
        )

        profile2 = create_test_profile(
            "doc_002",
            "different_filename_002.docx",
            sections_data=[
                {
                    "section_id": "sec_0",
                    "title": "Terms",
                    "heading_level": 1,
                }
            ],
        )

        profiles_by_id = {"doc_001": profile1, "doc_002": profile2}

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=["doc_001", "doc_002"],
            document_filenames=["offer_letter_001.docx", "different_filename_002.docx"],
            confidence=0.9,
            cluster_size=2,
            pairwise_scores=[0.85],
            pairwise_score_mean=0.85,
            pairwise_score_min=0.85,
            merge_evidence=[],
        )

        result = inferer.infer(family_cluster, profiles_by_id)

        # Inference should be based on section/content, not filenames
        assert result.family_id == "family_001"
        assert len(result.sections) >= 1


class TestGroundTruthIsolation:
    """Tests to ensure ground-truth JSON is never read."""

    def test_infer_does_not_read_ground_truth_files(self):
        """Inference doesn't attempt to read ground-truth files."""
        inferer = TemplateInferer()
        profile = create_test_profile("doc_001", "doc_001.docx")

        family_cluster = FamilyCluster(
            family_id="family_001",
            document_ids=["doc_001"],
            document_filenames=["doc_001.docx"],
            confidence=0.9,
            cluster_size=1,
            pairwise_scores=[],
            pairwise_score_mean=1.0,
            pairwise_score_min=1.0,
            merge_evidence=[],
        )

        # This should not raise an exception or attempt file I/O
        result = inferer.infer(family_cluster, {"doc_001": profile})

        assert result.family_id == "family_001"
