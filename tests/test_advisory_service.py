import services.advisory_service as advisory_service


def test_kannada_chat_uses_english_rag_then_returns_kannada(monkeypatch):
    calls = []

    def fake_translate_query(text):
        calls.append(text)
        return "How much water does a tomato crop need?", True

    def fake_retrieve(query):
        assert query == "How much water does a tomato crop need?"
        return [{"text": "Keep irrigation steady.", "document_id": "irrigation"}]

    def fake_answer(question, results, language, context):
        assert question == "How much water does a tomato crop need?"
        assert language == "English"
        assert context == "Latest greenhouse result: Suitable"
        return "Keep irrigation steady.", False

    monkeypatch.setattr(
        advisory_service, "translate_rag_query_to_english", fake_translate_query
    )
    monkeypatch.setattr(advisory_service, "retrieve", fake_retrieve)
    monkeypatch.setattr(advisory_service, "answer", fake_answer)

    response, results, generated, translated = advisory_service.answer_farmer_question(
        "ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?",
        "Kannada",
        "Latest greenhouse result: Suitable",
    )

    assert "ಟೊಮ್ಯಾಟೊಗೆ" in response
    assert "ನೀರಾವರಿ" in response
    assert results[0]["document_id"] == "irrigation"
    assert not generated
    assert translated
    assert calls == ["ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?"]
