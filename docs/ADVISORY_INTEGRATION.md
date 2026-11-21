The advisory now combines the logged-in farmer's latest disease prediction,
latest greenhouse analysis, and evidence from the existing agricultural RAG
store. Dashboard, disease detection, greenhouse analysis, and government scheme
pages remain independent. Their information is connected only in chatbot
advisory answers. With Use Context ON, the chatbot uses the current farmer's
latest saved analyses and relevant agricultural or scheme knowledge. With it
OFF, the chatbot gives general RAG answers without reading those analyses.

The generic responses had three causes: retrieval searched only the question;
the default offline answer discarded the analysis string; and the Kannada
renderer replaced the English answer with a generic topic response. The former
UI context helper also passed free-text XAI and could pass legacy numeric
greenhouse labels.

`services/analysis_context.py` reads selected fields from the existing
`disease_predictions` and `greenhouse_analyses` tables. Both queries filter by
the authenticated session's user ID and order by timestamp, then descending
primary key. Reads are uncached so new results appear on the next rerun.
Disease confidence is converted from the stored fraction to percent. Crop is
read from the deployed CNN's existing module metadata because this application's
crop-specific disease table has no crop column. Greenhouse labels use the
existing label map. Structured XAI checks are reconstructed from saved readings
using the existing greenhouse explanation and labeling policy, rather than
inserting the stored free-text explanation into a prompt. Only out-of-range
parameters are flagged, with their actual high/low direction.

The retrieval query includes crop, diagnosis, greenhouse status, flagged
parameters, and the question. It excludes sensor numbers. Focused disease and
parameter searches use the existing KB taxonomy and retrieval service so one
topic does not crowd the other out. Management headings improve lexical
ranking. Internal authoring notes and contradictory condition-specific sections
are filtered. No index is rebuilt and no embedding model is changed.
Scheme questions also preserve a search using the original question in the
existing schemes index. Both contextual offline answers and optional LLM
prompts include scheme guidance when requested. Analysis history is never
treated as proof of scheme eligibility.

Focused greenhouse searches can retrieve multiple sections from their routed
article. This prevents a descriptive introduction from hiding its management
section. Every flagged parameter gets its own adjustment or evidence limitation;
missing cold-weather heating guidance does not suppress supported irrigation
actions. Low root-zone moisture advice is conditional on confirming dryness
and uses the retrieved emitter-flow, drainage, crop-stage and substrate checks.
It does not invent an irrigation volume or schedule.

Low-humidity answers also use explanatory evidence, rather than requiring every
retrieved sentence to be an imperative. Each flagged reading is shown against
the deployed greenhouse model's policy range. Those ranges are model references;
the substrate-water range is not a universal field-soil target. For dry air,
retrieval also uses the existing irrigation article when a root-zone reading is
available. The response prioritizes air humidity, rechecking sensors and
monitoring temperature/humidity together, then uses the actual root-zone status
and retrieved emitter/drainage checks before discussing irrigation changes.
No humidification method or equipment setting is invented where the KB has none.

The optional Ollama prompt contains separate application facts, retrieved
evidence, and question sections. It requires integrated advice, preserves model
predictions, prohibits unsupported causation and chemical dosages, and respects
the selected language. The contextual offline path also reports both analyses
and supplies evidence-backed actions, or states that evidence is insufficient.
Kannada contextual answers use the existing localized labels and knowledge
summaries; English chunks are not displayed in Kannada answers.

The existing context toggle remains enabled by default. A compact “Using Latest
Analysis” panel appears above the input when results exist. Source links use the
existing display conventions and are saved with the response in chat history.
Disease-only, greenhouse-only, neither-analysis, and toggle-off cases remain
supported. A chat session that belongs to another farmer is cleared from the UI.

Files changed for this integration:

| File | Change |
| --- | --- |
| `services/analysis_context.py` | Shared latest-result normalization, formatting, query building, evidence routing |
| `services/advisory_service.py` | Context-aware retrieval and Kannada orchestration |
| `services/llm_service.py` | Combined prompt and contextual offline answers |
| `services/disease_service.py` | Read supported crop from existing deployment metadata |
| `services/greenhouse_service.py` | Shared label decoder and structured policy interpretation |
| `services/rag_service.py` | Management-heading ranking and internal-note filtering |
| `services/localization.py` | Kannada actions for the retrieved humidity-management section |
| `views/advisory.py` | Shared context, compact panel, sources, session ownership check |
| `components/source_cards.py` | Reusable source Markdown for persisted chat |
| `translation/ui_strings_en.json`, `translation/ui_strings_kn.json` | Panel, unavailable-context, and read-failure labels |
| `.streamlit/config.toml` | Remove an existing UTF-8 BOM that caused startup parsing warnings; retain all theme values |
| `tests/test_analysis_context.py` | Context, retrieval, language, user isolation, prompt, failure, and XAI regressions |
| `tests/test_advisory_ui.py` | Full application demo and voice-event integration |
| `tests/test_advisory_cold_dry_ui.py` | Persisted English/Kannada chat for cold/dry and low-humidity cases, including real greenhouse inference |

Validation command: `python -B -X utf8 -m pytest tests -q --disable-warnings`.
The suite contains 43 passing tests. The complete application test uses an
isolated temporary SQLite database, actual registration/login forms, a saved
tomato image with the existing CNN, the existing greenhouse model at 93%
humidity, the advisory panel and exact tomato question, persisted source links,
Kannada, scheme questions with context enabled and disabled, existing history
pages, the standalone government scheme page, and a second farmer. Context-OFF
UI tests also fail if any analysis-context database read is attempted. The
saved image produced Early Blight at about 92.85%; the greenhouse result was
Needs Adjustment with humidity flagged high. Other regressions cover all four
availability cases, timestamp ties, fresh records, generic questions, numeric
labels, nighttime light, missing readings, low humidity, failed translation,
insufficient evidence, and an unavailable LLM. The farmer-reported Septoria
case (97.7%, Unsuitable, temperature 14°C, root-zone moisture 5%) is covered in
English and Kannada service tests and a full chatbot UI/persistence test. A
mixed cold-temperature/high-humidity test checks that ventilation advice is
not presented as the remedy for low temperature.
The reported low-humidity case (Septoria 97.7%, temperature 24°C, humidity 15%,
root-zone moisture 75%, PAR 500, CO₂ 600) is covered in both languages and in a
full UI test that runs the existing greenhouse model, saves Unsuitable, and
checks the persisted combined chat response. Additional regressions cover low
humidity alongside dry roots, missing readings/evidence, and a changed model
policy to verify that reference ranges are loaded rather than hardcoded.

Both persisted FAISS indexes load with matching metadata counts: agriculture
158 vectors and schemes 14 vectors. Model and index artifacts and the database
schema are unchanged.

Local limitations: the configured runtime uses lexical retrieval over the
persisted FAISS metadata and has Ollama disabled. The real offline path is
tested; live LLM generation is covered with a mocked endpoint, not a running
Ollama model. Browser microphone capture and speech playback require a browser;
the voice event and shared generation/save path are tested headlessly. The
installed scikit-learn version emits compatibility warnings for the existing
greenhouse artifact, although inference passed. No dependencies were upgraded
or models retrained.

Run with the existing global installation on this PC (no venv install needed):

```powershell
cd "F:\Namma Krushi"
& "C:\Python314\python.exe" -m streamlit run app.py
```

Restart an already running server after service edits, then send a new question.
Previously saved chat answers remain historical messages; refreshing does not
regenerate them.
