from services.rag_service import _lexical_retrieve


def test_internal_scheme_authoring_notes_are_never_returned():
    metadata = [
        {
            "document_id": "internal",
            "topic": "Scheme discovery",
            "text": "## Namma Krushi chatbot response pattern\nInternal retrieval instruction.",
        },
        {
            "document_id": "midh",
            "topic": "MIDH protected cultivation scheme",
            "text": "Protected cultivation assistance is listed on the official portal.",
        },
    ]

    results = _lexical_retrieve("protected cultivation scheme", metadata, top_k=2)

    assert [item["document_id"] for item in results] == ["midh"]


def test_unmatched_query_does_not_return_arbitrary_zero_score_documents():
    metadata = [
        {
            "document_id": "midh",
            "topic": "MIDH protected cultivation",
            "text": "Official protected cultivation assistance.",
        }
    ]

    assert _lexical_retrieve("completely-unrelated-token", metadata, top_k=1) == []


def test_scoped_search_keeps_management_sections_from_the_same_article():
    from services.rag_service import retrieve

    results = retrieve(
        "low root-zone moisture irrigation decisions emitter flow drainage",
        "agriculture",
        top_k=3,
        document_ids={"07_irrigation_and_soil_moisture"},
    )
    assert len(results) >= 2
    assert {r["document_id"] for r in results} == {"07_irrigation_and_soil_moisture"}
    assert any("Better irrigation decisions" in r["text"] for r in results)
    assert any("root zone should not remain saturated" in r["text"] for r in results)
