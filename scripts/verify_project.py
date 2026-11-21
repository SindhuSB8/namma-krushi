"""Non-destructive health check for supplied artifacts and app foundations."""
import json, sqlite3, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def report(ok, label, warning=False):
    print(f"[{'PASS' if ok else 'WARN' if warning else 'FAIL'}] {label}")
    return ok or warning
def main():
    passed=True
    from database.db import initialize_database, DATABASE_PATH
    initialize_database(); tables={r[0] for r in sqlite3.connect(DATABASE_PATH).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    passed &= report({'users','admins','disease_predictions','greenhouse_analyses','chat_sessions','chat_messages'} <= tables,"SQLite initialization and tables")
    g=ROOT/'artifacts/greenhouse/model_artifacts/greenhouse_model.pkl'
    passed &= report(g.exists(),"Greenhouse model")
    features=json.loads((ROOT/'artifacts/greenhouse/model_artifacts/feature_columns.json').read_text())
    passed &= report(features == ['temperature','humidity','soil_moisture','light_intensity','co2'],"Greenhouse features")
    classes=json.loads((ROOT/'artifacts/disease/class_names.json').read_text())
    passed &= report((ROOT/'artifacts/disease/model_artifacts/tomato_disease_model.keras').exists(),"Disease CNN")
    passed &= report(len(classes)==11,"11 disease classes")
    for name in ('agriculture','schemes'):
        folder=ROOT/'artifacts/faiss'/name; metadata=[x for x in (folder/'metadata.jsonl').read_text(encoding='utf8').splitlines() if x]
        try:
            import faiss
            index=faiss.read_index(str(folder/'index.faiss'))
            passed &= report(index.ntotal==len(metadata),f"{name.title()} FAISS integrity ({index.ntotal} vectors)")
        except Exception: passed &= report(False,f"{name.title()} FAISS dependency",warning=True)
        manifest=json.loads((folder/'manifest.json').read_text())
        passed &= report(manifest['embedding_dimension']==1024,f"{name.title()} BGE-M3 dimension")
    for package,label in [('transformers','IndicTrans2 runtime'),('faster_whisper','Whisper'),('requests','Ollama client'),('edge_tts','TTS')]:
        try: __import__(package); report(True,label)
        except Exception: report(False,label,warning=True)
    return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
