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