# Task 2 — Template Inference System

## 1. Objective

Build a production-oriented Template Inference system for SuperDocs.

The system receives a collection of finished documents in DOCX and/or PDF format and infers:

- document families
- shared document structure
- fixed sections
- variable fields
- section ordering
- conditional sections
- conditions associated with conditional sections

The system must work when the uploaded documents belong to one family or contain multiple document families.

The goal is to infer the underlying template from finished documents rather than relying on predefined templates.

---

## 2. Core Problem

Given a collection of completed documents:

    Uploaded Documents
            |
            v
    Document Profiling
            |
            v
    Family Compatibility
            |
       +----+----+
       |         |
    Compatible  Mixed
       |         |
       v         v
    Template   Cluster by
    Inference  Document Family
       |         |
       +----+----+
            |
            v
    Template Inference

The system must be able to distinguish documents that share a common underlying structure from documents belonging to different document families.

---

## 3. Supported Input

The system must support:

- `.docx`
- `.pdf`

Multiple documents may be supplied in one inference request.

The system must support:

1. documents from a single family
2. mixed documents from multiple families

---

## 4. Benchmark Corpus

The benchmark contains two document families.

### Family A — Employee Offer Letters

12 synthetic offer letters:

- offer_001 through offer_012
- DOCX and PDF versions

The corpus contains:

- shared offer-letter structure
- candidate-specific values
- position details
- compensation
- dates
- managers
- controlled wording variation
- conditional sections

### Family B — Employee Onboarding Letters

12 synthetic onboarding letters:

- onboarding_001 through onboarding_012
- DOCX and PDF versions

The corpus contains:

- shared onboarding structure
- employee-specific values
- work-mode variation
- department variation
- seniority variation
- equipment variation
- conditional sections

All benchmark information is fictional.

---

## 5. Ground Truth Separation

The ground-truth JSON files are evaluation-only resources.

They must NOT be provided to the inference pipeline as input.

Ground truth is used only after inference to evaluate the system.

The system must infer the template from the finished documents themselves.

---

## 6. Architecture

The system should be implemented as modular components.

### 6.1 Document Ingestion

Responsibilities:

- detect file type
- load DOCX
- load PDF
- normalize extracted content
- preserve structural information where possible

---

### 6.2 Document Profiling

Create a normalized profile for every document.

The profile may contain:

- document ID
- filename
- file type
- text blocks
- paragraphs
- headings
- tables
- lists
- section boundaries
- formatting signals
- structural statistics
- content signals

The profiler must provide useful evidence for downstream family detection and template inference.

---

### 6.3 Family Compatibility

Compare document profiles to determine whether documents are structurally/content-wise compatible.

Do not rely only on filenames.

Compatibility should consider evidence such as:

- section structure
- headings
- semantic content
- repeated patterns
- tables
- document length
- structural similarity
- meaningful vocabulary

---

### 6.4 Family Clustering

When mixed document families are provided, cluster compatible documents into document families.

Example:

    6 Offer Letters
    +
    6 Onboarding Letters

should produce:

    Family 1 → Offer Letters
    Family 2 → Onboarding Letters

Each family is then processed independently.

---

### 6.5 Template Inference

For each detected family, infer:

- fixed content
- variable fields
- section structure
- section order
- conditional sections
- conditional rules
- formatting characteristics where useful

---

### 6.6 Variable Detection

Identify values that change across documents and infer their semantic role.

Examples:

- employee_name
- employee_id
- job_title
- department
- manager
- salary
- start_date
- location
- work_mode

The system should infer semantic variable names rather than simply reporting changed strings.

---

### 6.7 Conditional Section Detection

Infer sections that appear only when specific document attributes apply.

Examples from the onboarding corpus:

- Remote Work Setup
- Office Access and Desk Setup
- department-specific systems onboarding
- Leadership Orientation
- Equipment Allocation

Examples from the offer corpus include conditional employment-related sections.

The system must infer the relationship between document attributes and conditional sections from the corpus.

---

## 7. Output

The inference result must be machine-readable.

The output should contain, at minimum:

- detected document families
- family confidence
- inferred section structure
- section ordering
- fixed sections
- variable fields
- conditional sections
- inferred conditions
- relevant confidence scores/evidence

The final schema will be defined before implementation.

---

## 8. Evaluation

The system must be evaluated against the ground-truth datasets.

Evaluation should measure, where applicable:

- document family detection
- clustering accuracy
- section detection
- section ordering
- variable detection
- conditional-section detection
- conditional-rule inference
- overall inference quality

The evaluation layer must remain separate from the inference pipeline.

---

## 9. API

The system should expose an API for template inference.

The API must support multiple uploaded DOCX/PDF documents.

The exact endpoint and request/response schema will be finalized before implementation.

---

## 10. Testing

Tests must cover:

- document ingestion
- DOCX parsing
- PDF parsing
- document profiling
- family compatibility
- family clustering
- template inference
- variable detection
- conditional-section detection
- evaluation
- API behavior

Both single-family and mixed-family inputs must be tested.

---

## 11. Engineering Requirements

The implementation should be:

- modular
- maintainable
- testable
- explainable
- deterministic where practical
- robust to document variation

Avoid implementing the project as one large script.

Do not hard-code the benchmark's ground-truth answers into the inference logic.

Do not use filenames as the primary mechanism for identifying document families.

Do not expose API keys or secrets in source code.

Do not commit `.env` or `.venv`.

---

## 12. LLM Usage

An LLM may be used where semantic reasoning improves the inference process.

However:

- the LLM must not receive ground-truth JSON
- the system must not simply ask an LLM to produce the entire answer without structured processing
- document parsing, profiling, comparison, inference, and evaluation should remain modular
- model output should be validated and normalized before becoming part of the final result

The system should demonstrate engineering around the model rather than being only an LLM wrapper.

---

## 13. Development Strategy

Implementation will be incremental.

Order:

1. repository/project setup
2. corpus integration
3. document ingestion
4. document profiling
5. family compatibility
6. family clustering
7. template inference
8. variable detection
9. conditional logic inference
10. evaluation
11. API
12. tests
13. documentation
14. final integration

Each stage must be tested before moving to the next stage.

---

## 14. Important Constraint

The inference system must discover the underlying template from finished documents.

It must not be given:

- the original generation prompts
- ground-truth JSON
- manually encoded conditional rules
- manually encoded variable mappings
- predefined family labels

These resources may only be used for evaluation.

---

## 15. Current Status

Repository:
`superdocs-builds`

Use-case:
`use-cases/Darkside098/template-inference`

Branch:
`task/template-inference`

Benchmark corpus:
- Offer Letter Corpus — prepared
- Employee Onboarding Letter Corpus — prepared

Architecture:
Locked

Next implementation stage:
Project structure and document ingestion

---

## 16. Inference Output Contract

The inference engine must return a structured, machine-readable result.

The result must represent four major areas:

1. detected document families
2. inferred template structure
3. inferred variable fields
4. inferred conditional sections and rules

The output must also contain confidence/evidence where appropriate.

### 16.1 Top-Level Result

Conceptual structure:

```json
{
  "run_id": "string",
  "documents": [],
  "families": [],
  "inference": [],
  "metadata": {}
}
```

### 16.2 Document Information

Each processed document should have:

```json
{
  "document_id": "string",
  "filename": "string",
  "file_type": "docx|pdf",
  "profile_id": "string"
}

### 16.3 Document Family

Each detected family should contain:

{
  "family_id": "string",
  "family_name": "string|null",
  "document_ids": [],
  "confidence": 0.0,
  "evidence": []
}

family_name may initially be null when the system cannot confidently assign a semantic family name.

The system must not assume that filenames determine family membership.

### 16.4 Inferred Template

Each detected family should produce an inferred template:

{
  "family_id": "string",
  "template": {
    "sections": [],
    "variables": [],
    "conditional_sections": []
  }
}
### 16.5 Section

Each inferred section should contain:

{
  "section_id": "string",
  "name": "string",
  "type": "fixed|variable|conditional",
  "order": 0,
  "confidence": 0.0,
  "evidence": []
}

order represents the inferred relative section position.

### 16.6 Variable Field

Each inferred variable should contain:

{
  "name": "string",
  "semantic_type": "string",
  "confidence": 0.0,
  "evidence": [],
  "observed_values": []
}

Examples of possible semantic types:

person_name
person_id
job_title
department
date
time
location
salary
email
phone
manager_name
organization_name

The system may introduce additional semantic types when justified by document evidence.

Variable names must be semantic and reusable rather than based only on literal values.

### 16.7 Conditional Section

Each conditional section should contain:

{
  "section_name": "string",
  "condition": {
    "field": "string",
    "operator": "equals|not_equals|in|not_in|contains|exists",
    "value": "string|number|boolean|array|null"
  },
  "confidence": 0.0,
  "evidence": []
}

The system may support compound conditions later if the evidence requires them.

### 16.8 Evidence

Evidence should explain why an inference was made.

Examples:

{
  "type": "repeated_structure",
  "document_ids": ["doc_001", "doc_002"]
}

or:

{
  "type": "conditional_correlation",
  "section": "Remote Work Setup",
  "observed_with": {
    "field": "work_mode",
    "value": "Remote"
  }
}

Evidence must be derived from the processed documents and must not use ground-truth files.

### 16.9 Confidence

Confidence values must be normalized between:

0.0 and 1.0

Confidence must represent the system's confidence in the inference, not simply the presence of a value.

### 16.10 Ground Truth Isolation

The inference result must never depend directly on:

offer_ground_truth.json
onboarding_ground_truth.json

These files are evaluation-only.

The inference pipeline must operate correctly when those files are completely absent.

### 16.11 Explainability Requirement

The final result should make it possible to understand:

why documents were grouped together
why a section was considered fixed
why a value was considered variable
why a section was considered conditional
why a particular conditional rule was inferred

This evidence should be generated from document observations.

---

## 17. Initial Implementation Scope — Milestone 1

The first implementation milestone establishes the application foundation and document ingestion layer.

### Milestone 1 Goals

Implement only:

1. Modular Python application package structure
2. Configuration management
3. Normalized document representation
4. Document ingestion abstraction
5. DOCX document loader
6. Basic document structural extraction
7. Unit tests for the ingestion layer

### 17.1 Application Structure

Create a clean modular structure that separates:

- configuration
- document ingestion
- document models/schemas
- future profiling
- tests

Do not place all functionality in a single Python file.

### 17.2 Configuration

Configuration must support environment variables.

Secrets must never be hard-coded.

The existing `.env` file must not be committed.

The implementation should use the project's existing environment configuration approach where appropriate.

### 17.3 Normalized Document Representation

Create an internal representation that can later support both DOCX and PDF documents.

At minimum, the representation should be capable of storing:

- document ID
- filename
- file type
- paragraphs
- headings when detectable
- tables
- lists when detectable
- basic structural metadata

The representation must be independent of the source file format.

### 17.4 Document Ingestion Abstraction

Create an abstraction/interface for document loaders.

The architecture should allow:

```text
Document
   |
   +-- DOCX Loader
   |
   +-- PDF Loader (future milestone)

### 17.5 DOCX Loader

For Milestone 1, implement only the DOCX loader.

Do not implement the PDF loader yet.

The DOCX loader should:

- accept a DOCX file
- extract useful document content
- preserve paragraph order
- identify headings when reasonably detectable
- extract tables
- preserve useful list information when detectable
- return the normalized document representation

The loader must not perform template inference.

### 17.6 Tests

Create focused unit tests covering:

- successful DOCX loading
- normalized document creation
- paragraph extraction
- table extraction
- basic heading/structure detection
- invalid or missing file handling

Tests should use small fixtures where practical rather than depending on the entire benchmark corpus for every unit test.

At least one integration-style test should load one real benchmark DOCX and verify that the normalized representation contains expected structural information.

### 17.7 Explicitly Out of Scope for Milestone 1

Do NOT implement:

- document family detection
- family compatibility scoring
- clustering
- template inference
- variable detection
- conditional-section inference
- LLM calls
- embedding generation
- vector databases
- evaluation against ground truth
- API endpoints
- frontend/UI

These belong to later milestones.

### 17.8 Milestone 1 Completion Criteria

Milestone 1 is complete only when:

- the application structure is modular
- configuration loads successfully
- a DOCX can be loaded through the ingestion abstraction
- the normalized document representation is produced successfully
- paragraphs and tables are extracted
- basic headings/structure are detected where reasonably possible
- useful list information is preserved where detectable
- tests pass
- no ground-truth file is used by ingestion
- no benchmark-specific answers are hard-coded
- `.env` remains ignored
- `.venv` remains ignored
- the benchmark corpus remains unchanged