# Namma Krushi: An AI-Driven Kannada-English Advisory System for Greenhouse Tomato Cultivation

ನಮ್ಮ ಕೃಷಿ: ಹಸಿರುಮನೆ ಟೊಮ್ಯಾಟೊ ಕೃಷಿಗಾಗಿ ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಆಧಾರಿತ ಕನ್ನಡ-ಇಂಗ್ಲಿಷ್ ಸಲಹಾ ವ್ಯವಸ್ಥೆ

## App pages

The farmer sidebar has five pages (English and Kannada, switchable at any time):

| Page | Purpose |
|---|---|
| Home | Welcome, assistant shortcut, latest analysis, schemes card, how it works |
| AI Farming Assistant | Optional leaf image + optional greenhouse readings + question; one **Get AI Advice** button runs the disease CNN and greenhouse model, then gives one combined, grounded answer |
| Government Schemes | Search, browse and view all schemes (also reachable by asking the assistant) |
| History & Reports | Leaf scans, greenhouse readings and advisory chats, with CSV downloads |
| Profile | Name and preferred language |


Local Streamlit advisory system for Kannada/English greenhouse-tomato farmers. It preserves and loads the supplied EfficientNetB0 disease model, Random Forest greenhouse model, and separate BGE-M3/FAISS agriculture and scheme indexes; it never retrains or rebuilds them.

## Windows setup (first time only)

This project is tested with **64-bit Python 3.12** on Windows. Use Python 3.12
for the project environment; Python 3.14 is not the supported TensorFlow
runtime. The first installation downloads TensorFlow (about 350 MB) and may
download PyTorch packages, so keep the connection stable.

From the project directory, create and activate a Python 3.12 environment:

```powershell
& "C:\Program Files\Python312\python.exe" -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --timeout 300 --retries 10 -r requirements.txt
```

If PowerShell blocks the activation script, enable it only for the current
terminal and activate the environment again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv312\Scripts\Activate.ps1
```

If a TensorFlow download is interrupted or its temporary file is locked, close
other terminals running `pip`, restart PowerShell, activate `.venv312`, then
run:

```powershell
python -m pip install --no-cache-dir --timeout 300 --retries 10 tensorflow==2.21.0
python -m pip install --no-cache-dir --timeout 300 --retries 10 -r requirements.txt
```

## Start the app

After the first-time setup, activate the existing environment and launch the
application:

```powershell
.\.venv312\Scripts\Activate.ps1
python -m streamlit run app.py
```

Stop Streamlit with `Ctrl+C` in the terminal.

`database/namma_krushi.db` is created automatically. The initial visit chooses language, then supports farmer registration/login. The separate Admin tab permits a one-time local administrator setup only while the `admins` table is empty.

## Architecture

- `services/disease_service.py`: exact 224×224 RGB CNN inference and collision-safe upload history.
- `services/greenhouse_service.py`: saved Random Forest prediction plus policy-based local explanation.
- `services/rag_service.py`: normalised BGE-M3 querying of existing, integrity-checked FAISS indexes; agriculture and schemes remain separate.
- `services/llm_service.py`: optional local Ollama generation with a source-grounded extractive fallback.
- `database/`: bcrypt-protected authentication and SQLite farmer history.

Static labels use curated JSON dictionaries. Translation, local Whisper, and
text-to-speech features degrade without stopping farmer workflows when their
optional models or network providers are unavailable. Voice conversation is
intentionally turn-based, not a continuous call.

## Verification

Run `python scripts/verify_project.py`. It checks SQLite, model artifacts, class counts, FAISS/index metadata consistency and optional services without changing any trained artifact.

## Limits

Advice is sourced from the bundled knowledge base and does not substitute for local agronomy support. The system avoids creating pesticide dose, subsidy, eligibility, or deadline claims not supported by retrieved material.
