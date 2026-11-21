import json
from config import ARTIFACTS, DATABASE_PATH
from database.db import fetch_all, get_admin_counts
from services.rag_service import load_index


def render(st):
    st.title("Namma Krushi · Admin dashboard")

    # Every number below is read from SQLite on each page run. Nothing is
    # cached or hard-coded, so a new prediction shows up after "Refresh".
    counts = get_admin_counts()
    cols = st.columns(4)
    cols[0].metric("Registered farmers", counts["farmers"])
    cols[1].metric("Disease predictions", counts["disease_predictions"])
    cols[2].metric("Greenhouse analyses", counts["greenhouse_analyses"])
    cols[3].metric("AI advisory interactions", counts["advisory_interactions"])
    st.caption(
        f"Chat sessions: {counts['chat_sessions']} · "
        f"Database: {DATABASE_PATH}"
    )
    st.button("🔄 Refresh counts", key="admin_refresh_counts")

    st.subheader("Model status")
    g = json.loads((ARTIFACTS / "greenhouse" / "model_artifacts" / "model_metrics.json").read_text())
    d = json.loads((ARTIFACTS / "disease" / "model_artifacts" / "cnn_metrics.json").read_text())
    st.write(f"Greenhouse: {g['best_model']} · test accuracy {g['test_accuracy']:.2%}")
    st.write(f"Disease: {d['model']} · test accuracy {d['test_accuracy']:.2%}")

    st.subheader("FAISS status")
    for index in ("agriculture", "schemes"):
        try:
            faiss_index, metadata = load_index(index)
            if faiss_index is None:
                st.warning(f"{index.title()}: vector index unavailable or out of sync with metadata ({len(metadata)} chunks); using offline lexical search. Re-run scripts/build_faiss.py.")
            else:
                st.success(f"{index.title()}: {faiss_index.ntotal} vectors; metadata integrity verified.")
        except Exception:
            st.error(f"{index.title()}: integrity check failed.")

    st.subheader("Recent disease predictions")
    recent = fetch_all(
        "SELECT p.prediction_id, u.username, p.disease, "
        "ROUND(p.confidence * 100, 1) AS confidence_percent, p.created_at "
        "FROM disease_predictions p JOIN users u ON u.user_id = p.user_id "
        "ORDER BY p.prediction_id DESC LIMIT ?",
        (20,),
    )
    if recent:
        st.dataframe(recent, hide_index=True, width="stretch")
    else:
        st.info("No disease predictions have been saved yet.")

    st.subheader("Recent activity")
    st.dataframe(fetch_all("SELECT username,name,language FROM users ORDER BY user_id DESC LIMIT 20"), hide_index=True, width="stretch")
