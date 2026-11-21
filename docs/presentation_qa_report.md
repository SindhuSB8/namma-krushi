# Presentation QA Report

## Deliverable summary

- File: `AI_Based_Crop_Disease_Detection_Advisory_System_Master_Presentation.pptx`
- Slide count: **45**
- Template use: the supplied college deck was used only for PES visual identity, layout cues and the student/guide details available in it. Its old project-topic content was not reused.

## Content checks

| Check | Result |
|---|---|
| Complete academic flow from abstract through conclusion and references | PASS |
| Literature review contains at least 10 verified papers | PASS — 10 main studies plus contextual/technical references |
| Dataset source matches the project notebook | PASS — Kaggle Tomato Disease Multiple Sources |
| Disease image totals and splits match artifacts | PASS — 32,535 original; 1 corrupt; 32,534 valid; 23,265 train; 2,586 validation; 6,683 test |
| Disease model metrics match stored evaluation files | PASS — 94.28% test accuracy; 94.49% macro-F1 |
| Greenhouse metrics match stored model artifacts | PASS — 97.20% test accuracy; 95.00% macro-F1 |
| RAG/KB counts match metadata | PASS — 50 KB files; 34 verified sources; 158 agriculture chunks; 14 scheme chunks |
| Database entities match implementation | PASS |
| Limitations avoid unsupported agronomic guarantees | PASS |
| Unknown academic year clearly marked | PASS — `[To be confirmed]` on slide 1 |

## Visual and PowerPoint checks

| Check | Result |
|---|---|
| Opened by installed Microsoft PowerPoint | PASS |
| Exported every slide through PowerPoint | PASS — 45 PNG renders at 1600 × 900 |
| Manual visual inspection of all slide renders | PASS — three contact sheets reviewed; dense slides additionally inspected at full resolution |
| Automated text-boundary scan in PowerPoint | PASS — **0 overflow candidates** |
| Native PPTX package integrity | PASS — ZIP test returned no bad member |
| Reloaded with `python-pptx` | PASS — 45 slides |
| Consistent PES-inspired header/footer, logo and page numbering | PASS |
| Body text kept readable and diagrams editable | PASS |
| PowerPoint-incompatible embedded chart workbooks avoided | PASS — charts rebuilt as native editable shapes |

## Visual inventory

- **13 major editable diagrams:** overview, scenario, proposed solution, system architecture, process flow, preprocessing, augmentation, disease model, disease module, RAG architecture, integration, database and implementation map.
- **4 editable data charts:** class distribution, training history, greenhouse model comparison and greenhouse feature importance.
- **1 stored evaluation artifact image:** disease confusion matrix.
- **6 placements of actual application-uploaded leaf artifacts:** three on the dataset slide and three on the implementation slide.
- **0 AI-generated images.**
- **0 fabricated application screenshots.** Browser automation did not produce a trustworthy authenticated dashboard capture, so the presentation uses repository-derived module diagrams and real retained upload artifacts instead.

## Software verification


- Covered areas represented on slide 38 include authentication, chat ownership, history migration, concurrent database writes, latest greenhouse-card values, Kannada RAG, localization, RAG safety and speech-text escaping.

## Source traceability


- Every slide's purpose and primary evidence are listed in `presentation_content_map.md`.


