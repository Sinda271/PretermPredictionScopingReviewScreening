#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader


SECTION_NAMES = {
    "abstract": ["abstract", "summary"],
    "introduction": ["introduction", "background"],
    "methods": ["methods", "materials and methods", "methodology", "patients and methods", "data and methods"],
    "results": ["results"],
    "discussion": ["discussion"],
    "conclusion": ["conclusion", "conclusions"],
    "limitations": ["limitations", "strengths and limitations", "study limitations"],
}

NEXT_HEADINGS = [
    "abstract",
    "keywords",
    "introduction",
    "background",
    "methods",
    "materials and methods",
    "methodology",
    "patients and methods",
    "data and methods",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "references",
    "acknowledg",
    "funding",
]


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def compact(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " ..."


def text_path_for(pdf: Path, out_dir: Path) -> Path:
    digest = hashlib.sha1(str(pdf.resolve()).encode("utf-8")).hexdigest()[:10]
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", pdf.stem)[:90]
    return out_dir / f"{safe}_{digest}.txt"


def run_pdftotext(pdf: Path, txt: Path) -> None:
    txt.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(txt)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def metadata_for(pdf: Path) -> dict:
    try:
        reader = PdfReader(str(pdf))
        info = reader.metadata or {}
        return {
            "pages": len(reader.pages),
            "metadata_title": str(info.get("/Title", "") or "").strip(),
            "metadata_author": str(info.get("/Author", "") or "").strip(),
        }
    except Exception as exc:
        return {"pages": None, "metadata_error": str(exc)}


def extract_doi(text: str) -> str:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, flags=re.I)
    if not match:
        return ""
    doi = match.group(0).rstrip(".,;:)])}").replace(" ", "")
    return doi


def extract_section(text: str, labels: list[str], limit: int = 3000) -> str:
    lines = text.splitlines()
    lower_lines = [re.sub(r"[^a-z0-9 ]+", "", line.lower()).strip() for line in lines]
    start_idx = None
    for idx, line in enumerate(lower_lines):
        for label in labels:
            norm = re.sub(r"[^a-z0-9 ]+", "", label.lower()).strip()
            if line == norm or line.startswith(norm + " "):
                start_idx = idx + 1
                break
        if start_idx is not None:
            break
    if start_idx is None:
        return ""

    end_idx = len(lines)
    headings = {re.sub(r"[^a-z0-9 ]+", "", h.lower()).strip() for h in NEXT_HEADINGS}
    for idx in range(start_idx + 1, min(len(lines), start_idx + 400)):
        line = lower_lines[idx]
        if line in headings or any(line.startswith(h + " ") for h in headings if len(h) > 5):
            end_idx = idx
            break
    return compact("\n".join(lines[start_idx:end_idx]), limit)


def infer_title_from_first_page(text: str, metadata_title: str, filename: str) -> str:
    first = text[:5000]
    lines = []
    for raw in first.splitlines()[:80]:
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        low = line.lower()
        if len(line) < 8:
            continue
        if any(token in low for token in ["doi:", "http", "www.", "copyright", "received", "accepted", "available online"]):
            continue
        if low in {"abstract", "summary", "introduction", "research article", "original article", "article"}:
            continue
        if re.match(r"^(vol\.|volume|issue|journal|contents|keywords|page)\b", low):
            continue
        lines.append(line)

    if metadata_title and len(metadata_title) > 12 and not metadata_title.lower().endswith(".pdf"):
        bad_meta = ["elsevier", "sciencedirect", "springer", "mdpi", "frontiers"]
        if not any(bad in metadata_title.lower() for bad in bad_meta):
            return compact(metadata_title, 250)

    if lines:
        title = lines[0]
        if len(title) < 45 and len(lines) > 1:
            title = f"{title} {lines[1]}"
        return compact(title, 250)

    stem = Path(filename).stem
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return compact(stem, 250)


def matching_sentences(text: str, patterns: list[str], max_sentences: int = 8) -> list[str]:
    normalized = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    hits = []
    for sentence in sentences:
        low = sentence.lower()
        if any(pattern in low for pattern in patterns):
            cleaned = sentence.strip()
            if 40 <= len(cleaned) <= 700 and cleaned not in hits:
                hits.append(cleaned)
        if len(hits) >= max_sentences:
            break
    return hits


def make_digest(pdf: Path, text: str, txt_path: Path) -> dict:
    meta = metadata_for(pdf)
    sections = {
        name: extract_section(text, labels)
        for name, labels in SECTION_NAMES.items()
    }
    first_page = "\n".join(text.splitlines()[:120])
    relevant_patterns = [
        "dataset",
        "cohort",
        "population",
        "participants",
        "pregnant",
        "electronic health",
        "ultrasound",
        "microbiome",
        "metabol",
        "electrohyster",
        "machine learning",
        "deep learning",
        "random forest",
        "support vector",
        "neural network",
        "xgboost",
        "auc",
        "accuracy",
        "sensitivity",
        "specificity",
        "limitation",
    ]
    return {
        "file_name": pdf.name,
        "text_path": str(txt_path),
        "pages": meta.get("pages"),
        "metadata_title": meta.get("metadata_title", ""),
        "metadata_author": meta.get("metadata_author", ""),
        "doi": extract_doi(text),
        "title_candidate": infer_title_from_first_page(text, meta.get("metadata_title", ""), pdf.name),
        "first_page": compact(first_page, 3000),
        "abstract": sections["abstract"],
        "introduction": sections["introduction"],
        "methods": sections["methods"],
        "results": sections["results"],
        "discussion": sections["discussion"],
        "conclusion": sections["conclusion"],
        "limitations": sections["limitations"],
        "evidence_sentences": matching_sentences(text, relevant_patterns, 14),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".", help="Folder containing PDF files")
    parser.add_argument("--output", default="outputs/scoping_review_extraction")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists():
        raise SystemExit(f"Input folder does not exist: {input_dir}")

    output_dir = Path(args.output)
    text_dir = output_dir / "texts"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(input_dir.glob("*.pdf"))
    digests = []
    failures = []

    for pdf in pdfs:
        txt_path = text_path_for(pdf, text_dir)
        try:
            run_pdftotext(pdf, txt_path)
            text = clean_text(txt_path.read_text(encoding="utf-8", errors="replace"))
            digests.append(make_digest(pdf, text, txt_path))
        except Exception as exc:
            failures.append({"file_name": pdf.name, "error": str(exc)})

    (output_dir / "digests.json").write_text(
        json.dumps({"count": len(digests), "failures": failures, "articles": digests}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    for idx, article in enumerate(digests, 1):
        lines.append(f"## {idx}. {article['file_name']}")
        lines.append(f"Title candidate: {article['title_candidate']}")
        lines.append(f"DOI: {article['doi'] or 'not found'}")
        lines.append(f"Pages: {article['pages']}")
        if article["abstract"]:
            lines.append("Abstract: " + article["abstract"])
        if article["methods"]:
            lines.append("Methods: " + article["methods"])
        if article["results"]:
            lines.append("Results: " + article["results"])
        if article["limitations"]:
            lines.append("Limitations: " + article["limitations"])
        if article["conclusion"]:
            lines.append("Conclusion: " + article["conclusion"])
        if article["evidence_sentences"]:
            lines.append("Evidence sentences: " + " ".join(article["evidence_sentences"][:8]))
        lines.append("")
    (output_dir / "digest_readable.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"pdfs": len(pdfs), "extracted": len(digests), "failures": failures}, ensure_ascii=False))


if __name__ == "__main__":
    main()
