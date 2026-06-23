# AI-Assisted Screening and Extraction Pipeline for the Scoping Review

## Overview

This repository contains the scripts used to support the scoping review:

**Artificial Intelligence for Preterm Birth Prediction in Prenatal Care: A Scoping Review**

The workflow combines AI-assisted screening, PDF text extraction, structured information extraction, and dataset harmonization. All AI-generated outputs were reviewed and validated by the lead reviewer before inclusion in the final dataset.

---

## Repository Structure

```text
.
├── Preterm_Birth_Screening.ipynb
├── extract_scoping_pdf_text.py
├── extract_papers.py
├── build_scoping_csv.py
├── Metadata/
│   └── rayyan_resolved_duplicates.csv
├── All_final_scoping_articles/
│   └── *.pdf
├── Screening/
│   └── ...
├── Extracted_papers/
│   └── ...
├── outputs/
│   └── ...
└── README.md
```

---

## Requirements

### Python

- Python 3.10+
- pandas
- numpy
- requests
- tqdm
- pypdf
- pymupdf (fitz)
- jupyter

Install dependencies:

```bash
pip install pandas numpy requests tqdm pypdf pymupdf jupyter
```

### Local LLM

The screening and extraction workflow was developed using:

```text
Ollama
Qwen3:8b
```

Example:

```bash
ollama serve
ollama pull qwen3:8b
```

---

# Workflow

## Step 1 – AI-Assisted Screening

### Input

```text
Metadata/rayyan_resolved_duplicates.csv
```

### Run

```bash
jupyter notebook Preterm_Birth_Screening.ipynb
```

### Purpose

- Import records exported from Rayyan
- Perform AI-assisted title and abstract screening
- Generate structured inclusion/exclusion decisions
- Support Stage 1 and Stage 2 screening

### Output

```text
Screening/
```

### Screening Criteria

Studies were screened according to the eligibility criteria reported in the manuscript.

The AI model was used as a decision-support tool only. Final inclusion decisions remained under human review.

---

## Step 2 – PDF Text Extraction

### Input

```text
All_final_scoping_articles/
```

### Run

```bash
python extract_scoping_pdf_text.py
```

### Purpose

- Extract full text from included PDFs
- Identify metadata
- Detect article sections
- Capture DOI and publication information
- Generate structured text digests

### Output

```text
outputs/
```

---

## Step 3 – AI-Assisted Full-Text Extraction

### Run

```bash
python extract_papers.py
```

### Purpose

- Extract study characteristics
- Identify datasets
- Identify AI methods
- Extract outcomes
- Summarize key findings

### Output

```text
Extracted_papers/
```

The extraction process is intended to support evidence synthesis and was reviewed manually before inclusion in the final dataset.

---

## Step 4 – Dataset Harmonization

### Run

```bash
python build_scoping_csv.py
```

### Purpose

- Consolidate extracted study information
- Harmonize study names
- Resolve duplicate records
- Standardize fields used in analysis and reporting

### Output

```text
outputs/final_scoping_review_dataset.csv
```

This dataset was used to support descriptive analyses and evidence mapping.

---

# Reproducibility Statement

This repository is provided to enhance transparency and reproducibility of the AI-assisted review workflow.

The scripts support:

- Screening assistance
- Information extraction
- Dataset construction

All screening decisions, eligibility assessments, extracted variables, and synthesized findings were reviewed and verified by the lead reviewer before inclusion in the final review.

The repository should therefore be interpreted as an AI-assisted research workflow rather than a fully automated evidence synthesis pipeline.

---

# Citation

If you use this repository, please cite:

**Besrour S, et al. _Artificial Intelligence for Preterm Birth Prediction in Prenatal Care: A Scoping Review_.**