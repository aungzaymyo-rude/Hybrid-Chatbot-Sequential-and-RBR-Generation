from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SOURCE_MD = DOCS / "dissertation_supervisor_ready.md"
OUT_DIR = DOCS / "overleaf_dissertation_project"
SECTIONS_DIR = OUT_DIR / "sections"
FIGURES_DIR = OUT_DIR / "figures"

FIGURE_SOURCES = {
    "hybrid_architecture.png": DOCS / "figures" / "figure_3_1_hybrid_architecture.png",
    "mlops_lifecycle.png": DOCS / "figures" / "figure_3_2_mlops_lifecycle.png",
    "chat_ui.png": DOCS / "figures" / "figure_3_3_chat_ui.png",
    "metric_comparison.png": DOCS / "figures" / "figure_4_1_metric_comparison.png",
    "training_curves.png": DOCS / "figures" / "figure_4_2_training_curves.png",
    "dataset_splits.png": DOCS / "figures" / "figure_4_3_dataset_and_splits.png",
    "testing_summary.png": DOCS / "figures" / "figure_4_4_testing_summary.png",
    "admin_overview.png": DOCS / "figures" / "figure_4_5_admin_overview.png",
    "admin_trace.png": DOCS / "figures" / "figure_4_7_admin_trace.png",
}

SECTION_FILES = {
    "Chapter 1: Introduction": "01_introduction.tex",
    "Chapter 2: Literature Review": "02_literature_review.tex",
    "Chapter 3: Design and Development": "03_design_and_development.tex",
    "Chapter 4: Result Analysis and Evaluation": "04_result_analysis_and_evaluation.tex",
    "Chapter 5: Conclusions and Further Work": "05_conclusions_and_future_work.tex",
}

SECTION_LABELS = {
    "Chapter 1: Introduction": "sec:introduction",
    "Chapter 2: Literature Review": "sec:literature-review",
    "Chapter 3: Design and Development": "sec:design-development",
    "Chapter 4: Result Analysis and Evaluation": "sec:results-evaluation",
    "Chapter 5: Conclusions and Further Work": "sec:conclusion",
}

APPEND_FIGURES = {
    "### 3.3 System Architecture": r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\linewidth]{figures/hybrid_architecture.png}
    \caption{Hybrid haematology chatbot architecture.}
    \label{fig:hybrid-architecture}
\end{figure}
""",
    "### 3.9 Deployment, Monitoring, and Retraining": r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/mlops_lifecycle.png}
    \caption{MLOps lifecycle used in the implemented chatbot project.}
    \label{fig:mlops-lifecycle}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.74\linewidth]{figures/chat_ui.png}
    \caption{Implemented browser-based chat interface.}
    \label{fig:chat-ui}
\end{figure}
""",
    "### 4.2 Model Performance": r"""
\begin{table}[H]
    \centering
    \caption{Final held-out test metrics for the two model profiles.}
    \label{tab:final-metrics}
    \begin{tabular}{lccccc}
        \hline
        Model & Accuracy & Macro F1 & Weighted F1 & Macro Precision & Macro Recall \\
        \hline
        General & 0.8928 & 0.8649 & 0.8914 & 0.8822 & 0.8617 \\
        Report & 0.9358 & 0.8965 & 0.9360 & 0.8968 & 0.9040 \\
        \hline
    \end{tabular}
\end{table}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/metric_comparison.png}
    \caption{Metric comparison across the general and report model profiles.}
    \label{fig:metric-comparison}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/training_curves.png}
    \caption{Training loss and validation F1 behaviour over the eight-epoch schedule.}
    \label{fig:training-curves}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/dataset_splits.png}
    \caption{Dataset footprint and fixed 70/15/15 split allocation.}
    \label{fig:dataset-splits}
\end{figure}
""",
    "### 4.4 Testing Strategy": r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.72\linewidth]{figures/testing_summary.png}
    \caption{Automated test execution summary showing 52 passing tests.}
    \label{fig:testing-summary}
\end{figure}
""",
    "### 4.5 Operational Evaluation and Admin Monitoring": r"""
\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/admin_overview.png}
    \caption{Admin overview dashboard used for operational monitoring and review.}
    \label{fig:admin-overview}
\end{figure}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.88\linewidth]{figures/admin_trace.png}
    \caption{Inference trace view showing how a phrase was processed across the NLP pipeline.}
    \label{fig:admin-trace}
\end{figure}
""",
}

README_TEXT = """# Overleaf Dissertation Package

This folder is a self-contained Overleaf-ready LaTeX project for the dissertation.

## What to upload
- `main.tex`
- `references.bib`
- the entire `sections/` folder
- the entire `figures/` folder

The easiest approach is to zip the whole `overleaf_dissertation_project` folder and upload it to Overleaf.

## Compile settings
- Document class: `article`
- Paper size: `a4paper`
- Reference style: `biblatex` with `authoryear`
- Recommended compiler in Overleaf: `pdfLaTeX`
- Bibliography tool: `biber`

## Notes
- The content was converted from the current dissertation markdown source.
- Title-page placeholders should be replaced in `main.tex`.
- If Overleaf asks to re-run bibliography, compile again after `biber` finishes.
"""

BIB_TEXT = r"""@article{denecke2022,
  author = {Denecke, Kerstin and May, Roman},
  title = {Usability Assessment of Conversational Agents in Healthcare: A Literature Review},
  journal = {Studies in Health Technology and Informatics},
  year = {2022},
  doi = {10.3233/SHTI220431}
}

@article{graves2005,
  author = {Graves, Alex and Schmidhuber, J{\"u}rgen},
  title = {Framewise phoneme classification with bidirectional LSTM and other neural network architectures},
  journal = {Neural Networks},
  volume = {18},
  number = {5--6},
  pages = {602--610},
  year = {2005}
}

@article{hochreiter1997,
  author = {Hochreiter, Sepp and Schmidhuber, J{\"u}rgen},
  title = {Long Short-Term Memory},
  journal = {Neural Computation},
  volume = {9},
  number = {8},
  pages = {1735--1780},
  year = {1997},
  doi = {10.1162/neco.1997.9.8.1735}
}

@article{kreuzberger2023,
  author = {Kreuzberger, Dominik and K{\"u}hl, Niklas and Hirschl, Sebastian},
  title = {Machine Learning Operations (MLOps): Overview, Definition, and Architecture},
  journal = {IEEE Access},
  volume = {11},
  pages = {31866--31879},
  year = {2023},
  doi = {10.1109/ACCESS.2023.3262138}
}

@article{milneives2020,
  author = {Milne-Ives, Madison and de Cock, Caroline and Lim, Elizabeth and Shehadeh, Mohamad H. and de Pennington, Natalie and Mole, Gareth and Normando, Ester and Meinert, Edward},
  title = {The Effectiveness of Artificial Intelligence Conversational Agents in Health Care: Systematic Review},
  journal = {Journal of Medical Internet Research},
  volume = {22},
  number = {10},
  pages = {e20346},
  year = {2020},
  doi = {10.2196/20346}
}

@article{salton1988,
  author = {Salton, Gerard and Buckley, Christopher},
  title = {Term-weighting approaches in automatic text retrieval},
  journal = {Information Processing \& Management},
  volume = {24},
  number = {5},
  pages = {513--523},
  year = {1988}
}

@inproceedings{sculley2015,
  author = {Sculley, D. and Holt, Gary and Golovin, Daniel and Davydov, Eugene and Phillips, Todd and Ebner, Dietmar and Chaudhary, Vinay and Young, Michael and Crespo, Jean-Francois and Dennison, Dan},
  title = {Hidden Technical Debt in Machine Learning Systems},
  booktitle = {Advances in Neural Information Processing Systems 28},
  year = {2015}
}

@article{tudorcar2020,
  author = {Tudor Car, Lorainne and Dhinagaran, Dhivya A. and Kyaw, Bhone Myint and Kowatsch, Tobias and Joty, Shafiq and Theng, Yin-Leng and Atun, Rifat},
  title = {Conversational Agents in Health Care: Scoping Review and Conceptual Analysis},
  journal = {Journal of Medical Internet Research},
  volume = {22},
  number = {8},
  pages = {e17158},
  year = {2020},
  doi = {10.2196/17158}
}
"""

MAIN_TEX = r"""\documentclass[a4paper,11pt]{article}

\usepackage[english]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[top=2.5cm,bottom=2.5cm,left=3cm,right=2cm,marginparwidth=1.75cm]{geometry}
\usepackage{setspace}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{float}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[colorlinks=true, allcolors=blue]{hyperref}
\usepackage[backend=biber,style=authoryear]{biblatex}
\addbibresource{references.bib}

\onehalfspacing
\setlength{\parskip}{0.4em}
\setlength{\parindent}{0pt}
\setlist[itemize]{leftmargin=1.5em}
\setlist[enumerate]{leftmargin=1.7em}

\title{Design and Development of a Hybrid Chatbot for Medical Haematology using Sequential Models for Intent Classification and Retrieval-Based Response Generation}
\author{Student Name: [Insert Name] \\ Student ID: [Insert ID] \\ Programme: [Insert Degree Title] \\ Supervisor: [Insert Supervisor Name]}
\date{May 2026}

\begin{document}
\maketitle

\begin{abstract}
\input{sections/abstract.tex}
\end{abstract}

\section{Introduction}
\label{sec:introduction}
\input{sections/01_introduction.tex}

\section{Literature Review}
\label{sec:literature-review}
\input{sections/02_literature_review.tex}

\section{Design and Development}
\label{sec:design-development}
\input{sections/03_design_and_development.tex}

\section{Result Analysis and Evaluation}
\label{sec:results-evaluation}
\input{sections/04_result_analysis_and_evaluation.tex}

\section{Conclusions and Further Work}
\label{sec:conclusion}
\input{sections/05_conclusions_and_future_work.tex}

\nocite{denecke2022,graves2005,hochreiter1997,kreuzberger2023,milneives2020,salton1988,sculley2015,tudorcar2020}
\printbibliography[title={References}]

\end{document}
"""

MOJIBAKE_MAP = {
    "KÃ¼hl": "Kühl",
    "â€˜": "'",
    "â€™": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "--",
    "â€”": "---",
    "â€¦": "...",
}


def normalize_text(text: str) -> str:
    for bad, good in MOJIBAKE_MAP.items():
        text = text.replace(bad, good)
    return text


def split_document(md_text: str) -> tuple[str, dict[str, str]]:
    abstract = md_text.split("## Abstract", 1)[1].split("## Chapter 1", 1)[0].strip()
    body = md_text.split("## Chapter 1", 1)[1].split("## References", 1)[0]
    chunks = re.split(r"^## ", "## Chapter 1" + body, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        sections[title] = content
    return abstract, sections


def strip_numeric_prefix(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\s+", "", title).strip()


def escape_segment(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "^": r"\^{}",
        "~": r"\~{}",
    }
    text = normalize_text(text)
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_inline(text: str) -> str:
    text = normalize_text(text)
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    parts: list[str] = []
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    last = 0
    for match in pattern.finditer(text):
        if match.start() > last:
            parts.append(escape_segment(text[last:match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            parts.append(r"\textbf{" + escape_segment(token[2:-2]) + "}")
        elif token.startswith("*"):
            parts.append(r"\textit{" + escape_segment(token[1:-1]) + "}")
        elif token.startswith("`"):
            parts.append(r"\texttt{" + escape_segment(token[1:-1]) + "}")
        last = match.end()
    if last < len(text):
        parts.append(escape_segment(text[last:]))
    return "".join(parts)


def convert_markdown_block(content: str) -> str:
    out: list[str] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped in APPEND_FIGURES:
            out.append(APPEND_FIGURES[stripped].strip())
            i += 1
            continue

        if stripped.startswith("[Insert "):
            i += 1
            continue

        if stripped.startswith("### "):
            out.append(r"\subsection{" + format_inline(strip_numeric_prefix(stripped[4:])) + "}")
            i += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            out.append(r"\begin{enumerate}")
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                item = re.sub(r"^\d+\.\s*", "", lines[i].strip())
                out.append(r"\item " + format_inline(item))
                i += 1
            out.append(r"\end{enumerate}")
            continue

        if stripped.startswith("- "):
            out.append(r"\begin{itemize}")
            while i < len(lines) and lines[i].strip().startswith("- "):
                item = lines[i].strip()[2:]
                out.append(r"\item " + format_inline(item))
                i += 1
            out.append(r"\end{itemize}")
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if (
                not next_line
                or next_line.startswith("### ")
                or next_line.startswith("- ")
                or re.match(r"^\d+\.\s", next_line)
                or next_line in APPEND_FIGURES
                or next_line.startswith("[Insert ")
            ):
                break
            paragraph_lines.append(next_line)
            i += 1
        out.append(format_inline(" ".join(paragraph_lines)))
    return "\n\n".join(out) + "\n"


def write_sections(abstract: str, sections: dict[str, str]) -> None:
    SECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    (SECTIONS_DIR / "abstract.tex").write_text(convert_markdown_block(abstract), encoding="utf-8")
    for title, filename in SECTION_FILES.items():
        tex = convert_markdown_block(sections[title])
        (SECTIONS_DIR / filename).write_text(tex, encoding="utf-8")


def copy_figures() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for out_name, src in FIGURE_SOURCES.items():
        shutil.copy2(src, FIGURES_DIR / out_name)


def validate_project() -> list[str]:
    errors: list[str] = []
    required = [OUT_DIR / "main.tex", OUT_DIR / "references.bib", OUT_DIR / "README.md"]
    required += [SECTIONS_DIR / "abstract.tex"]
    required += [SECTIONS_DIR / name for name in SECTION_FILES.values()]
    required += [FIGURES_DIR / name for name in FIGURE_SOURCES]
    for path in required:
        if not path.exists():
            errors.append(f"Missing required file: {path}")

    main_text = (OUT_DIR / "main.tex").read_text(encoding="utf-8")
    for figure_name in FIGURE_SOURCES:
        if figure_name in main_text:
            continue
        for section_path in SECTIONS_DIR.glob("*.tex"):
            if figure_name in section_path.read_text(encoding="utf-8"):
                break
        else:
            errors.append(f"Figure not referenced in TeX: {figure_name}")

    if "Right-click and update field" in main_text:
        errors.append("Word field placeholder leaked into LaTeX.")
    if "3,250" in main_text or "0.9040" in main_text and "0.8965" not in main_text:
        errors.append("Outdated dissertation metrics detected in main.tex.")
    return errors


def main() -> None:
    md_text = normalize_text(SOURCE_MD.read_text(encoding="utf-8"))
    abstract, sections = split_document(md_text)

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_sections(abstract, sections)
    copy_figures()
    (OUT_DIR / "main.tex").write_text(MAIN_TEX, encoding="utf-8")
    (OUT_DIR / "references.bib").write_text(BIB_TEXT, encoding="utf-8")
    (OUT_DIR / "README.md").write_text(README_TEXT, encoding="utf-8")

    errors = validate_project()
    if errors:
        raise SystemExit("\n".join(errors))
    print(OUT_DIR)


if __name__ == "__main__":
    main()
