# Overleaf Dissertation Package

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
