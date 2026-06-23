#!/usr/bin/env python3
"""
Paper Extraction & Synthesis Pipeline
======================================
Loads PDFs from a folder, extracts text, and uses Ollama (qwen3:8b) to:
  1. Extract per-paper: context, problem, AI/ML tools, contribution, results
  2. Cluster papers into thematic groups
  3. Identify cross-cutting limitations and improvement directions

OUTPUTS:
  - papers_extracted.csv      → one row per paper with all extracted fields
  - synthesis_report.md       → thematic clusters, limitations, future directions

USAGE:
  1. Place all PDFs in a folder (e.g. ./pdfs/)
  2. Run: python extract_papers.py
  3. When prompted, enter the path to PDF folder

REQUIREMENTS:
  - Ollama running locally: ollama serve
  - Model pulled:           ollama pull qwen3:8b
  - Python packages:        pip install pypdf pdfplumber requests
"""

import os
import sys
import json
import re
import time
import csv
import requests
import pdfplumber
from pathlib import Path
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
OLLAMA_URL       = "http://localhost:11434/api/generate"
MODEL            = "qwen3:8b"
MAX_TEXT_CHARS   = 6000   # chars sent to model per paper (~1500 tokens)
SLEEP_BETWEEN    = 0.5    # seconds between API calls
os.makedirs("Extracted_papers", exist_ok=True)
CHECKPOINT_FILE  = "Extracted_papers/extraction_checkpoint.json"
OUTPUT_CSV       = "Extracted_papers/papers_extracted.csv"
OUTPUT_MD        = "Extracted_papers/synthesis_report.md"

# ── PROMPTS ───────────────────────────────────────────────────────────────────
EXTRACTION_SYSTEM = (
    "You are a research analyst extracting structured information from academic papers "
    "on artificial intelligence for preterm birth prediction. "
    "Respond ONLY with valid compact JSON. No markdown. No preamble. No explanation."
)

EXTRACTION_TEMPLATE = """Extract structured information from the academic paper text below.

CRITICAL: Respond with ONLY a raw JSON object. No markdown. No ```json. No explanation. Start your response with {{ and end with }}.
All values must be plain strings (no nested objects). Keep each value under 100 words.

Paper text:
{text}

JSON format (copy this exactly, fill in the values):
{{"context":"clinical background in 2-3 sentences","problem":"specific gap or problem addressed in 1-2 sentences","ai_tools":"ML/DL methods used e.g. XGBoost, LSTM, SVM - list them","contribution":"what the paper proposes or builds that is new in 2-3 sentences","results":"key metrics: AUC=X, sensitivity=X, specificity=X, accuracy=X etc","dataset":"dataset name, size, source","data_modality":"input data type: EHR, EHG, biomarkers, imaging, microbiome etc","gestational_timing":"when prediction is made e.g. first trimester, 20-24 weeks","population":"sample size, country, parity, risk level","limitations":"limitations stated by authors"}}"""

SYNTHESIS_SYSTEM = (
    "You are a senior systematic review researcher synthesizing findings "
    "from a scoping review on AI for preterm birth prediction. "
    "Write in clear academic prose suitable for a Methods/Discussion section."
)

SYNTHESIS_TEMPLATE = """Below is structured data extracted from {n} papers on AI/ML for preterm birth prediction.

{summaries}

Write a comprehensive synthesis report in Markdown with the following sections:

## 1. Thematic Clusters
Group the papers into 4-7 thematic clusters based on shared patterns 
(data modality, method type, clinical context, etc.). 
For each cluster:
- Give it a descriptive name
- List which papers belong to it (by title)
- Describe what they have in common
- Summarize their collective contributions

## 2. AI/ML Methods Landscape
Summarize the range of methods used across all papers. 
Identify the most common approaches, emerging methods, and any notable trends.

## 3. Cross-Cutting Limitations
Identify the most important limitations that appear repeatedly across multiple papers. 
Be specific. Cite examples from the papers.

## 4. Gaps and Future Directions
Based on the limitations and gaps you identified, what are the most important 
areas for future research? Be specific and actionable.

## 5. Key Findings Summary
3-5 bullet points summarizing the most important takeaways from this body of literature."""


# ── HELPERS ──────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level}: {msg}")


def extract_pdf_text(pdf_path: str) -> tuple[str, str]:
    """Extract text from PDF. Returns (title_guess, text)."""
    text = ""
    title = Path(pdf_path).stem  # fallback title = filename

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages):
                if i > 15:  # cap at 15 pages - abstracts/intro/methods is enough
                    break
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = "\n".join(pages_text)

            # Try to get title from first page
            if pages_text:
                first_lines = pages_text[0].split("\n")[:5]
                # Heuristic: longest line in first 5 lines is likely the title
                candidate = max(first_lines, key=len, default="")
                if len(candidate) > 20:
                    title = candidate.strip()

    except Exception as e:
        log(f"pdfplumber failed for {pdf_path}: {e} - trying pypdf", "WARN")
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            # Try metadata title
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title
            pages_text = []
            for i, page in enumerate(reader.pages):
                if i > 15:
                    break
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = "\n".join(pages_text)
        except Exception as e2:
            log(f"pypdf also failed for {pdf_path}: {e2}", "ERROR")

    # Truncate to MAX_TEXT_CHARS
    text = text[:MAX_TEXT_CHARS]
    return title, text


def call_ollama(system: str, prompt: str, max_tokens: int = 800) -> str:
    """Call Ollama and return response text."""
    full_prompt = system + "\n\n" + prompt
    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
            "think": False        # disables Qwen3 thinking mode natively
        }
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    raw = resp.json()["response"].strip()
    # Strip <think> blocks
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    return raw


def parse_json_response(raw: str) -> dict:
    """Robustly parse JSON from model response - 4 fallback attempts."""
    # Strip <think> blocks (Qwen3 reasoning traces)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Strip markdown fences
    raw = re.sub(r"```json", "", raw)
    raw = re.sub(r"```", "", raw)
    raw = raw.strip()

    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: find outermost { } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Attempt 3: fix trailing commas before } or ]
    try:
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        match2 = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match2:
            return json.loads(match2.group())
    except Exception:
        pass

    # Attempt 4: regex field extraction from key: "value" pairs
    result = {}
    fields = ["context", "problem", "ai_tools", "contribution", "results",
              "dataset", "data_modality", "gestational_timing", "population", "limitations"]
    for field in fields:
        m = re.search(
            rf'"{field}"\s*:\s*"(.*?)"(?=\s*[,}}])',
            raw, re.DOTALL
        )
        if m:
            result[field] = m.group(1).replace('\\"', '"').strip()
    if result:
        return result

    log("All JSON parse attempts failed", "WARN")
    return {}


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {}


def save_checkpoint(data: dict):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_pdfs(folder: str) -> list[str]:
    folder = Path(folder)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        # Also try recursive
        pdfs = sorted(folder.rglob("*.pdf"))
    return [str(p) for p in pdfs]


# MAIN EXTRACTION
def extract_all_papers(pdf_folder: str) -> list[dict]:
    pdfs = find_pdfs(pdf_folder)
    if not pdfs:
        log(f"No PDFs found in {pdf_folder}", "ERROR")
        sys.exit(1)

    log(f"Found {len(pdfs)} PDFs in {pdf_folder}")

    # Test Ollama connection
    log("Testing Ollama connection...")
    try:
        test = call_ollama("You are helpful.", "Say OK in one word.", max_tokens=5)
        log(f"Ollama OK - response: {test.strip()[:20]}")
    except Exception as e:
        log(f"Cannot reach Ollama: {e}", "ERROR")
        log("Make sure Ollama is running: ollama serve", "ERROR")
        log("And model is pulled: ollama pull qwen3:8b", "ERROR")
        sys.exit(1)

    checkpoint = load_checkpoint()
    results = []

    for i, pdf_path in enumerate(pdfs):
        pdf_key = Path(pdf_path).name
        log(f"[{i+1}/{len(pdfs)}] Processing: {pdf_key}")

        # Resume from checkpoint
        if pdf_key in checkpoint:
            log(f"  Skipping (already extracted)")
            results.append(checkpoint[pdf_key])
            continue

        # Extract text
        title, text = extract_pdf_text(pdf_path)
        log(f"  Extracted {len(text)} chars | Title: {title[:60]}")

        if len(text) < 200:
            log(f"  WARNING: very little text extracted - may be scanned PDF", "WARN")

        # Call model with up to 2 retries
        try:
            prompt = EXTRACTION_TEMPLATE.format(text=text)
            extracted = {}
            for attempt in range(3):
                raw = call_ollama(EXTRACTION_SYSTEM, prompt, max_tokens=1500)
                extracted = parse_json_response(raw)
                if extracted:
                    break
                log(f"  Retry {attempt+1}/3 for JSON parsing...", "WARN")
                time.sleep(1)

            record = {
                "filename":          pdf_key,
                "title":             extracted.get("context", title)[:200] if not extracted.get("title") else title,
                "extracted_title":   title,
                "context":           extracted.get("context", "Not extracted"),
                "problem":           extracted.get("problem", "Not extracted"),
                "ai_tools":          extracted.get("ai_tools", "Not extracted"),
                "contribution":      extracted.get("contribution", "Not extracted"),
                "results":           extracted.get("results", "Not extracted"),
                "dataset":           extracted.get("dataset", "Not reported"),
                "data_modality":     extracted.get("data_modality", "Not reported"),
                "gestational_timing":extracted.get("gestational_timing", "Not reported"),
                "population":        extracted.get("population", "Not reported"),
                "limitations":       extracted.get("limitations", "Not reported"),
            }

            log(f"  ✓ Extracted | AI tools: {str(record['ai_tools'])[:60]}")

        except Exception as e:
            log(f"  ERROR extracting {pdf_key}: {e}", "ERROR")
            record = {
                "filename": pdf_key, "extracted_title": title,
                "title": title, "context": f"ERROR: {e}",
                "problem": "", "ai_tools": "", "contribution": "",
                "results": "", "dataset": "", "data_modality": "",
                "gestational_timing": "", "population": "", "limitations": ""
            }

        results.append(record)
        checkpoint[pdf_key] = record
        save_checkpoint(checkpoint)
        time.sleep(SLEEP_BETWEEN)

    return results


# SAVE CSV
def save_csv(results: list[dict], output_path: str):
    if not results:
        return
    fieldnames = [
        "filename", "extracted_title", "context", "problem", "ai_tools",
        "contribution", "results", "dataset", "data_modality",
        "gestational_timing", "population", "limitations"
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    log(f"CSV saved: {output_path} ({len(results)} papers)")


# SYNTHESIS 
def synthesize(results: list[dict], output_path: str):
    log("Running synthesis (clustering, limitations, future directions)...")
    log("This may take 2-3 minutes for 88 papers...")

    # Build compact summaries for each paper
    summaries = []
    for i, r in enumerate(results):
        s = (
            f"Paper {i+1}: {r.get('extracted_title', r.get('filename',''))}\n"
            f"  Data modality: {r.get('data_modality','')}\n"
            f"  AI tools: {r.get('ai_tools','')}\n"
            f"  Problem: {r.get('problem','')}\n"
            f"  Contribution: {r.get('contribution','')}\n"
            f"  Results: {r.get('results','')}\n"
            f"  Limitations: {r.get('limitations','')}\n"
        )
        summaries.append(s)

    # Split into batches if too many papers (model context limit)
    # For 88 papers, send in 2 batches then synthesize
    BATCH_SIZE = 44
    batch_syntheses = []

    for batch_start in range(0, len(summaries), BATCH_SIZE):
        batch = summaries[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        log(f"  Synthesizing batch {batch_num} ({len(batch)} papers)...")

        batch_text = "\n---\n".join(batch)
        prompt = SYNTHESIS_TEMPLATE.format(n=len(batch), summaries=batch_text)

        try:
            synthesis = call_ollama(SYNTHESIS_SYSTEM, prompt, max_tokens=2500)
            batch_syntheses.append(synthesis)
        except Exception as e:
            log(f"  Synthesis batch {batch_num} failed: {e}", "ERROR")
            batch_syntheses.append(f"*Synthesis failed for batch {batch_num}: {e}*")

        time.sleep(1)

    # Final meta-synthesis if multiple batches
    if len(batch_syntheses) > 1:
        log("  Running final meta-synthesis across batches...")
        meta_prompt = (
            f"Below are two partial synthesis reports from a scoping review of {len(results)} papers "
            f"on AI for preterm birth prediction. Merge them into one coherent final report "
            f"with the same section structure. Eliminate redundancy. Keep all unique points.\n\n"
            f"=== PART 1 ===\n{batch_syntheses[0]}\n\n"
            f"=== PART 2 ===\n{batch_syntheses[1]}"
        )
        try:
            final_synthesis = call_ollama(SYNTHESIS_SYSTEM, meta_prompt, max_tokens=3000)
        except Exception as e:
            log(f"  Meta-synthesis failed: {e}", "ERROR")
            final_synthesis = "\n\n---\n\n".join(batch_syntheses)
    else:
        final_synthesis = batch_syntheses[0]

    # Write Markdown output
    md_content = (
        f"# Scoping Review Synthesis\n"
        f"## AI/ML for Preterm Birth Prediction\n\n"
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*  \n"
        f"*Papers analysed: {len(results)}*  \n"
        f"*Model: {MODEL} via Ollama*\n\n"
        f"---\n\n"
        f"{final_synthesis}\n\n"
        f"---\n\n"
        f"## Appendix: Per-Paper Limitations\n\n"
    )

    for i, r in enumerate(results):
        title = r.get("extracted_title", r.get("filename", f"Paper {i+1}"))
        lim = r.get("limitations", "Not reported")
        md_content += f"**{i+1}. {title}**  \n{lim}\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    log(f"Synthesis report saved: {output_path}")


# ENTRY POINT
def main():
    print("=" * 60)
    print("  Paper Extraction & Synthesis Pipeline")
    print("  AI for Preterm Birth Prediction - Scoping Review")
    print("=" * 60)
    print()

    # Get PDF folder
    if len(sys.argv) > 1:
        pdf_folder = sys.argv[1]
    else:
        pdf_folder = input("Enter path to PDF folder (e.g. ./pdfs): ").strip()
        if not pdf_folder:
            pdf_folder = "./All_final_scoping_articles"

    if not os.path.isdir(pdf_folder):
        print(f"ERROR: Folder not found: {pdf_folder}")
        sys.exit(1)

    # Get output directory
    out_dir = input("Enter output folder (press Enter for current directory): ").strip()
    if not out_dir:
        out_dir = "."
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, OUTPUT_CSV)
    md_path  = os.path.join(out_dir, OUTPUT_MD)

    log(f"\nPDF folder:    {pdf_folder}")
    log(f"CSV output:    {csv_path}")
    log(f"MD output:     {md_path}")
    log(f"Checkpoint:    {CHECKPOINT_FILE}")
    log(f"Model:         {MODEL}")
    log(f"\nMax text/paper:{MAX_TEXT_CHARS} chars (~{MAX_TEXT_CHARS//4} tokens)")

    # Step 1: Extract all papers
    results = extract_all_papers(pdf_folder)

    # Step 2: Save CSV
    save_csv(results, csv_path)

    # Step 3: Synthesize
    synthesize(results, md_path)

    print()
    print("=" * 60)
    print("  DONE")
    print(f"  CSV:      {csv_path}")
    print(f"  Report:   {md_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()