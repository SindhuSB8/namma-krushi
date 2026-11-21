# Presentation Content Map

| Slide | Title | Purpose | Primary evidence / source |
|---:|---|---|---|
| 1 | Namma Krushi: AI-Based Tomato Disease Detection & Advisory System | College-formatted title, student and guide details | Supplied college template; project README |
| 2 | Abstract | Summarize the complete implemented system and measured results | README; model artifacts; database and KB metadata |
| 3 | Introduction | Establish crop-health, greenhouse and advisory context | Project scope; R1–R10 |
| 4 | Problem Scenario | Show the farmer decision chain and points of delay/risk | Project problem framing; R2, R3, R8 |
| 5 | Problem Statement | State the capstone research/engineering problem | Repository scope and implemented modules |
| 6 | Motivation | Quantify the available data, knowledge base and localization scope | Disease/greenhouse artifacts; KB manifest |
| 7 | Objectives | Define eight testable system objectives | README, services and tests |
| 8 | Purpose & Scope | Separate implemented scope from exclusions | README and application modules |
| 9 | Existing Approaches & Their Limitations | Compare manual, portal, classifier and chatbot approaches | R1–R10 |
| 10 | Proposed System | Present the integrated end-to-end response | Application architecture and services |
| 11 | Literature Survey I | Review five studies on vision and agricultural advisory | R1–R5 |
| 12 | Literature Survey II | Review five recent studies on transfer learning, QA and RAG | R6–R10 |
| 13 | Literature Analysis & Research Gap | Convert literature limitations into project design responses | R1–R10 |
| 14 | Comparative Study | Compare the proposed system with common alternatives | Literature analysis; project features |
| 15 | Functional Requirements | Enumerate authentication, disease, greenhouse, advisory, scheme and history functions | Source code and tests |
| 16 | Non-Functional Requirements | State usability, reliability, security, traceability and safety requirements | Source code, tests and deployment constraints |
| 17 | Tools & Technologies | Show the verified software stack | Requirements/config/source files; D2–D5 |
| 18 | Overall System Architecture | Show user, application, AI, retrieval and persistence components | Application and service modules |
| 19 | Complete Process Flow | Trace start-to-history execution | `app.py`, page modules and services |
| 20 | Disease Dataset Overview | Give exact image totals, split and source | D1; disease notebook/artifacts; actual upload images |
| 21 | Dataset Class Distribution | Visualize all 11 class counts and imbalance | Disease manifest/evaluation artifacts |
| 22 | Data Preprocessing Pipeline | Explain validation, split, decode, resize and batching | Disease training notebook |
| 23 | Data Augmentation | Document the exact training augmentations and class weighting | Disease training notebook/history |
| 24 | Disease Model Architecture | Show EfficientNetB0 transfer-learning architecture | D2; model training code/artifacts |
| 25 | Model Training Methodology | Document phases, loss, callbacks and selection | Training code and history CSV files |
| 26 | Training Performance | Plot training and validation accuracy from both phases | `phase1_history.csv`, `phase2_history.csv` |
| 27 | Disease Model Evaluation | Report held-out test metrics and per-class performance | Classification report and test metrics |
| 28 | Confusion Matrix & Class Performance | Show class-confusion evidence and difficult classes | Stored confusion matrix and class report |
| 29 | Greenhouse Dataset & Model | Present verified data partitions, features, labels and selection method | Greenhouse model metrics and training artifacts |
| 30 | Greenhouse Evaluation & Explainability | Compare candidate models and show feature importance | Model comparison and feature-importance CSV files |
| 31 | Disease Detection Module | Trace image upload through inference, storage and output | Disease service, page logic and database methods |
| 32 | RAG / Chatbot Architecture | Explain offline indexing and online query/answer path | FAISS metadata, configuration, R12 |
| 33 | Knowledge Base Design | Quantify source documents, chunks and domain separation | KB manifest, FAISS metadata, S01–S34 |
| 34 | Prediction-to-Advisory Integration | Show how classification and retrieval combine safely | Disease/advisory services and curated content |
| 35 | Kannada–English & Voice Interaction | Explain static UI localization, query translation and voice fallbacks | Translation/voice services and locale files |
| 36 | Database Design | Present users, prediction, greenhouse and chat entities | `database/db.py` |
| 37 | Implementation & User Interface | Map the implemented Streamlit modules and retained inputs | Page modules, README and actual upload artifacts |
| 38 | System Testing | Report representative automated tests and actual pass status | Test suite; 12/12 passed on 30 September 2026 |
| 39 | Results & Discussion | Integrate disease, greenhouse and application results | All model artifacts and tests |
| 40 | Limitations | State nine specific technical and agronomic limits | Artifact scope, literature and deployment review |
| 41 | Future Enhancements | Define feasible next research/engineering steps | Limitations and literature gaps |
| 42 | Conclusion | Summarize predict–explain–advise value | Whole project evidence |
| 43 | References | Give research references R1–R7 | R1–R7 |
| 44 | References (continued) | Give R8–R12, dataset and technical references | R8–R12, D1–D2, S01–S34 register |
| 45 | Thank You | Close the presentation in the college template style | Supplied college template |

## Visual inventory

- Native editable diagrams: slides 2, 4, 10, 18, 19, 22–24, 31–32, 34, 36–37.
- Native editable charts: slides 21, 26 and 30 (two charts).
- Artifact images: slide 28 confusion matrix; slides 20 and 37 actual application-uploaded leaves.
- Tables: slides 9, 11–16, 25, 27, 33 and 38.
