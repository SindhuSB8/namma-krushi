# Namma Krushi - government schemes: live website fetching removed (latest)

- Removed the "Refresh all from official websites" button, the "Official pages saved: n/31" progress line and the
  "Pages that could not be read" list, the automatic background sync, and the per-scheme "Latest from the official
  website" panel with its "Refresh from official website" button.
- Scheme pages now show only the curated knowledge-base summary (benefits, eligibility, how to apply), read aloud
  support, and the plain "Official source" link, which the farmer can open to check current rates and dates.
- Deleted `services/scheme_fetcher.py`, `scripts/refresh_schemes.py` and `artifacts/scheme_cache/`; removed the
  ten fetch-only strings from `ui_strings_en.json` / `ui_strings_kn.json`, the `truststore` requirement and the
  fetcher tests. The app no longer makes any network request to government websites.

- Cleanup: removed presentation-only files (`presentation_render/`, `template_preview/`, `presentation_assets/`,
  `scripts/build_master_presentation.py`, `scripts/make_presentation_contact_sheets.py`), Python caches, the unused
  `scheme_official_site` string and the now-unused `key_prefix` argument in `views/schemes.py`.

---

# Namma Krushi - disease-prediction history and admin counts fix (latest)

## Root cause of "Total Disease Predictions = 0"
- Prediction itself worked, but saving it failed **silently**: `services/farm_assistant.py` wrapped the
  image write *and* the INSERT in one `try/except` that only logged. Any failure (e.g. a `user_id` that
  is not in this database's `users` table -> `FOREIGN KEY constraint failed`, or a locked database)
  left the farmer looking at a normal result while no row was stored and an orphan image stayed on disk.
- This database file has no `sqlite_sequence` entry for `disease_predictions`: no INSERT has ever
  succeeded in it. Disease images on disk exist for farmers 2-5, who are not in this DB's `users` table.
- Chat history was written to a *second* file (`database/namma_krushi_chat.db`), so `chat_messages` in
  `namma_krushi.db` stayed empty while the admin page counted the other file.

## Changes
- `database/db.py`: new `save_disease_prediction()` (atomic, validates the farmer, ignores a repeat of the
  same result within 15 s), `get_admin_counts()`, `count_chat_interactions()`. Chat now uses the main
  database; the old `*_chat.db` is imported once (never modified or deleted; chats of farmers that no
  longer exist are not imported).
- `services/farm_assistant.py`: reports `saved` / `prediction_id`; removes the image file if saving fails
  or the result is a duplicate; stores forward-slash image paths. Unreliable predictions are still not saved.
- `views/advisory.py` + translations: farmer sees "Saved to your History." or a clear warning.
- `views/admin_dashboard.py`: live counts for farmers, disease predictions, greenhouse analyses and AI
  advisory interactions, a Refresh button, the database path, and a recent-predictions table.
- Tests: `tests/test_disease_history_and_admin_counts.py` (incl. real-model end-to-end), updated
  `tests/test_database.py`; stale voice-input UI tests skipped.

## Update: History "What should I do?" and Schemes latest-website sync
- `services/disease_actions.py` (new) + `views/history_reports.py`: every saved disease scan has a
  "What should I do?" expander (English from the disease knowledge base, Kannada from the reviewed advice).
- `services/scheme_fetcher.py`: browser-like headers, 20 s read timeout with one retry, Windows certificate
  store via `truststore` (certificate checking stays ON), PDF/JS-only/error pages reported with a clear
  reason, and a background worker that refreshes every scheme page.
- `views/schemes.py`: automatic background sync on first visit, "Refresh all" button, live progress and
  a list of pages that could not be read. `requirements.txt`: added `truststore`.

---

# Namma Krushi - integration fixes (latest)

## What changed in this round
- **Old results no longer leak into new answers.** Each submission is answered from *its own* leaf image and
  readings only. Earlier saved results are used only if the farmer ticks "Also use my previous saved results"
  (off by default, never for an input supplied now, and labelled "earlier saved result"). Old result cards are
  cleared on every new submission. Voice questions follow the same rule.
- **Leaf-image validation** (`services/disease_service.py`): unreadable / tiny / blank / non-plant-colour images are
  rejected before the CNN runs; low-confidence, tied or high-entropy predictions are reported as "cannot be reliably
  analysed". Unreliable images are not saved to History and are never used as the current disease. Thresholds are
  constants at the top of the file - re-calibrate them with real field photos and real non-leaf images.
- **Kannada -> English query conversion** (`services/translation_service.py`): keeps high/low direction
  ("ಆರ್ದ್ರತೆ ಹೆಚ್ಚು" -> "high humidity"), negation ("do not"), symptoms and the requested action; whole-word/suffix
  matching so short roots no longer fire inside unrelated words. If nothing is understood and the online translator
  is unreachable the farmer is told, instead of the app guessing a topic.
- **Scheme routing** (`services/rag_service.py`): whole-word, three-tier matching. "apply fungicide", "benefit of
  ventilation" and "my polyhouse humidity is high" are agriculture questions; PM-KUSUM, NHM, KCC, "polyhouse
  subsidy" etc. still route to schemes.
- **Greenhouse**: specific, knowledge-base-grounded advice per abnormal reading in English and Kannada
  (`services/greenhouse_advice.py`); no scikit-learn "feature names" warning; stricter validation (NaN/None/missing).
  A version-mismatch of scikit-learn is logged once with the fix (install the pinned 1.6.1).
- **Results UI**: separate disease and greenhouse cards with green / yellow / red indicators per parameter.
- **History**: each saved advisory answer now carries a snapshot of the exact analysis it used (no schema change).
- **Profile / registration validation** (`services/validation.py`): empty, 1-character, digits-only, control-character
  or over-long names are rejected and nothing is saved; password rules (min 6, max 72, differs from current).
  Profile page header text is now translated.
- New tests: `tests/test_integration_fixes.py`; UI tests updated for the opt-in behaviour.

## Not verifiable offline (please run once in your environment)
Streamlit AppTest suites, CNN inference on real leaf images, microphone / Whisper transcription, and the online
Kannada translation service.

---

# Namma Krushi - integrated frontend + audit fixes

## Frontend (from Namma_Krushi_Integrated_Frontend.zip)
Adopted as the UI: `app.py`, Home (`views/dashboard.py`), AI Farming Assistant (`views/advisory.py`),
History & Reports (`views/history_reports.py`). Schemes and Profile pages are unchanged.
Wired to the fixed backend, plus:
- Every string goes through the English/Kannada translation files (the upload hard-coded English).
- Sensor inputs start blank (all five = analysed, partly filled = warning).
- Voice question (browser dictation or recording) added under the form.
- Results stay on screen after the page reruns, are kept per farmer and cleared on logout.
- An analysis with no typed question still produces combined advice.
- History shows readable explanations and CSV downloads.
Not carried over from the upload (unused / stale): disease_detection.py, greenhouse_analysis.py,
disease_history.py, chat_history.py and their outdated tests.

## Schemes
- Cards show scheme information only - "chatbot response pattern", "Source note" etc. are removed
  (`services/text_cleaning.py`).
- Search could only reach 2 of 14 scheme chunks (PM-KISAN, KCC, PMFBY, AIF were unreachable); fixed.
- Generic words ("scheme", "government") no longer outrank "polyhouse", "subsidy".
- Quick-filter buttons work; all sections of a scheme are shown; PM-KUSUM and NHM added.

## Earlier audit fixes
See the previous CHANGES list: scheme-question routing, light thresholds from policy, model caching,
scikit-learn pin, rag/config.py root path, pydantic requirement, admin FAISS message.

## More schemes and official-website fetching
- 8 new schemes (16 in total): Per Drop More Crop (drip subsidy), Interest Subvention on KCC loans, PM Kisan Maandhan
  (pension), Soil Health Card, e-NAM, Farm Mechanization (SMAM), PMFME (food processing), FPO scheme - plus PM-KUSUM and
  National Horticulture Mission. English + Kannada text, official links, and routing so chat questions find them.
- They work immediately: `services/kb_supplement.py` reads scheme articles that are not yet in the search index.
- Schemes page: "Browse by topic" filter (5 topics) with one-tap buttons.
- Official website text: each card has "Latest from the official website" with a Refresh button
  (`services/scheme_fetcher.py`). Allow-listed official hosts only, cached with a date, falls back to the saved copy.
  Weekly refresh from a scheduler:  python scripts/refresh_schemes.py
- Search ranking: rare words ("polyhouse") now outrank shared words ("subsidy"); "pm-kisan" matches PM-KISAN only.

## Nursery, greenhouse, tomato and all-India state schemes (31 schemes in total)
New: MIDH nursery & planting material, NHB greenhouse/protected cultivation projects, cold storage & post-harvest,
Operation Greens, Market Intervention Scheme (tomato price support), PM Kisan SAMPADA cold chain, RKVY-RAFTAAR,
organic/natural farming, and state articles for Karnataka, Tamil Nadu, Maharashtra, Gujarat, Rajasthan,
Haryana/Punjab/Himachal and Telangana/Andhra Pradesh. Eight topic filters on the Schemes page.
Central figures were checked against official guidance; state rates marked "reported" come from secondary sources and
must be confirmed with the state horticulture department. A question with no state named ranks national schemes first.

Run:  pip install -r requirements.txt  &&  python -m streamlit run app.py
Tests: python -m pytest tests     (90 tests)
Run `python scripts/build_faiss.py` once to add PM-KUSUM and NHM to the schemes index.
