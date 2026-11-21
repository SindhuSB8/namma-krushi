"""Language-aware orchestration for the farmer advisory chat."""
import re

from services.llm_service import answer
from services.rag_service import retrieve, route
from services.localization import localize_rag_item
from services.translation_service import translate_rag_query_to_english
from services.analysis_context import analysis_evidence_routes, build_retrieval_query, greenhouse_evidence_matches, has_analysis_context


def _retrieve_with_analysis(question, context):
    """Keep the existing RAG service; add focused searches for each analysis.

    A combined query alone can let one topic crowd the other out of top-k.
    The existing taxonomy selects disease and XAI evidence without changing
    the stored indexes or embedding model.
    """
    broad = retrieve(build_retrieval_query(question, context))
    routes = analysis_evidence_routes(context)
    # Preserve the question's scheme intent before agricultural context terms
    # are added. Scheme knowledge is combined here, never in the ML modules.
    focused = retrieve(question, "schemes") if route(question) == "schemes" else []
    analysis_groups = []
    disease = context.get("disease", {})
    if disease.get("available"):
        query = f"{disease['crop']} {disease['disease']} management principles prevention"
        analysis_groups.append([r for r in retrieve(query, "agriculture") if r.get("document_id") in routes["disease"]])
    greenhouse = context.get("greenhouse", {})
    searched = set()
    hints = {
        ("temperature", "High"): "heat ventilation",
        ("temperature", "Low"): "cold temperature night growth stage local climate",
        ("humidity", "High"): "high humidity ventilation",
        ("humidity", "Low"): "dry air humidity temperature root zone irrigation decisions emitter flow drainage",
        ("soil_moisture", "High"): "excess water drainage irrigation decisions emitter flow",
        ("soil_moisture", "Low"): "water stress irrigation decisions emitter flow drainage",
        ("light_intensity", "High"): "strong radiation shading",
        ("light_intensity", "Low"): "low light",
        ("co2", "High"): "carbon dioxide monitoring safety",
        ("co2", "Low"): "carbon dioxide ventilation",
    }
    for p in greenhouse.get("problem_parameters", []):
        hint = hints.get((p["feature"], p["direction"]), "")
        query = f"greenhouse {p['direction'].lower()} {p['label']} management {hint}"
        if query in searched:
            continue
        searched.add(query)
        for document in sorted(routes["greenhouse_parameters"][p["feature"]]):
            candidates = retrieve(query, "agriculture", top_k=3, document_ids={document})
            analysis_groups.append([r for r in candidates if greenhouse_evidence_matches(r, context, p)][:2])
    # Reserve a first evidence section for every concern before adding more
    # sections, so supplementary text does not crowd later parameters out.
    focused.extend(group[0] for group in analysis_groups if group)
    focused.extend(item for group in analysis_groups for item in group[1:])
    output, seen = [], set()
    for item in focused + broad:
        if item.get("document_id") in routes["greenhouse"] and not greenhouse_evidence_matches(item, context):
            continue
        # Other disease articles can match shared management words. Keep the
        # known diagnosis authoritative unless the question names that topic.
        if disease.get("available") and item.get("category") == "disease" and item.get("document_id") not in routes["disease"]:
            if item.get("topic", "").casefold() not in question.casefold():
                continue
        key = item.get("chunk_id") or (item.get("document_id"), item.get("text"))
        if key not in seen:
            output.append(item)
            seen.add(key)
    return output[:10]


def _kannada_grounded_answer(english_question, english_answer, results):
    """Render the English RAG result as deterministic farmer-safe Kannada."""
    if not results:
        return "ಆ ಪ್ರಶ್ನೆಗೆ ಸ್ಥಳೀಯ ಕೃಷಿ ಸಲಹಾ ಮಾಹಿತಿ ಕಂಡುಬಂದಿಲ್ಲ. ಟೊಮ್ಯಾಟೊ ಬೆಳೆ, ನೀರಾವರಿ, ರೋಗ, ಕೀಟ, ಹಸಿರುಮನೆ ಅಥವಾ ಸರ್ಕಾರಿ ಯೋಜನೆಯ ಬಗ್ಗೆ ಸ್ವಲ್ಪ ಹೆಚ್ಚಿನ ವಿವರದೊಂದಿಗೆ ಕೇಳಿ."

    question = english_question.lower()
    if route(question) == "schemes":
        item = localize_rag_item(results[0], "Kannada")
        return f"**{item['topic']}**\n\n{item['text']}"
    if "water" in question or "irrigation" in question:
        return "ಟೊಮ್ಯಾಟೊಗೆ ಒಂದೇ ನಿಗದಿತ ಪ್ರಮಾಣದ ನೀರು ಎಲ್ಲ ಸಂದರ್ಭಕ್ಕೂ ಸರಿಯಾಗುವುದಿಲ್ಲ. ಮಣ್ಣು ಅಥವಾ ಬೆಳವಣಿಗೆ ಮಾಧ್ಯಮದ ತೇವಾಂಶ, ಗಿಡದ ಹಂತ, ಹವಾಮಾನ ಮತ್ತು ಒಳಚರಂಡಿಯನ್ನು ನೋಡಿ ನೀರಾವರಿ ಹೊಂದಿಸಿ. ಬೇರು ವಲಯ ತೇವವಾಗಿರಲಿ; ಆದರೆ ನೀರು ನಿಲ್ಲಬಾರದು. ಡ್ರಿಪ್ಪರ್ ಹರಿವು ಸಮವಾಗಿದೆಯೇ ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಮಣ್ಣು ಇನ್ನೂ ಒದ್ದೆಯಾಗಿದ್ದರೆ ಮತ್ತೊಮ್ಮೆ ನೀರು ಹಾಕಬೇಡಿ. ಗಿಡದ ವಯಸ್ಸು, ಕುಂಡ ಅಥವಾ ಜಮೀನು, ಮತ್ತು ಈಗಿನ ತೇವಾಂಶ ತಿಳಿಸಿದರೆ ಪ್ರಮಾಣವನ್ನು ಇನ್ನಷ್ಟು ನಿಖರವಾಗಿ ಹೇಳಬಹುದು."
    if "yield" in question or "grow" in question:
        return "ಟೊಮ್ಯಾಟೊ ಇಳುವರಿಗಾಗಿ ನೀರಾವರಿಯನ್ನು ಸ್ಥಿರವಾಗಿಡಿ, ಹೂಬಿಡುವ ಸಮಯದಲ್ಲಿ ತಾಪಮಾನ ಮತ್ತು ಆರ್ದ್ರತೆಯನ್ನು ಗಮನಿಸಿ, ಉತ್ತಮ ಗಾಳಿಚಲನೆಯಿಂದ ಪರಾಗಸ್ಪರ್ಶಕ್ಕೆ ನೆರವಾಗಿರಿ ಮತ್ತು ಹೆಚ್ಚು ಗೊಬ್ಬರ ಹಾಕುವ ಮೊದಲು ಡ್ರಿಪ್ಪರ್ ಹರಿವು ಹಾಗೂ ಒಳಚರಂಡಿಯನ್ನು ಪರಿಶೀಲಿಸಿ. ರೋಗಗ್ರಸ್ತ ಕೆಳ ಎಲೆಗಳನ್ನು ತೆಗೆದು ಬೆಳೆಗೊಂಚಲಿನಲ್ಲಿ ಗಾಳಿಯಾಡುವಂತೆ ಮಾಡಿ."
    if "pest" in question or "whitefly" in question or "borer" in question:
        return "ಮೊದಲು ಎಲೆಯ ಮೇಲ್ಭಾಗ ಮತ್ತು ಕೆಳಭಾಗವನ್ನು ಪರಿಶೀಲಿಸಿ ಕೀಟವನ್ನು ಖಚಿತಪಡಿಸಿ. ಹೆಚ್ಚು ಬಾಧಿತ ಭಾಗಗಳನ್ನು ಬೇರ್ಪಡಿಸಿ, ಕಳೆ ಮತ್ತು ಬೆಳೆ ಅವಶೇಷಗಳನ್ನು ತೆರವುಗೊಳಿಸಿ, ಕೀಟ ಪ್ರವೇಶ ಜಾಲ ಮತ್ತು ಅಂಟು ಬಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ. ಕೀಟ ಗುರುತು ಮತ್ತು ಹಾನಿಯ ಮಟ್ಟ ಖಚಿತವಾಗುವವರೆಗೆ ಅಂಧವಾಗಿ ಔಷಧಿ ಸಿಂಪಡಿಸಬೇಡಿ; ಅಗತ್ಯವಿದ್ದರೆ ಸ್ಥಳೀಯ ಶಿಫಾರಸು ಮತ್ತು ಲೇಬಲ್ ಪ್ರಕಾರ ಮಾತ್ರ ಬಳಸಿ."

    item = localize_rag_item(results[0], "Kannada")
    return f"**{item['topic']}**\n\n{item['text']}"


def is_greeting(question):
    """Return True only for a social greeting, never a crop question."""
    cleaned = re.sub(r"[^\w\s]", " ", question.casefold())
    normalized = " ".join(cleaned.split())
    exact_greetings = {
        "hi", "hii", "hiii", "hello", "hey", "hai", "gm",
        "good morning", "good morming", "good mormg", "good afternoon", "good evening",
        "how are you", "whats up", "what is up", "namaskara", "ನಮಸ್ಕಾರ",
    }
    return normalized in exact_greetings


def greeting_response(language):
    if language == "Kannada":
        return "ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಟೊಮ್ಯಾಟೊ ಬೆಳೆ, ರೋಗ, ಕೀಟ, ನೀರಾವರಿ ಅಥವಾ ಹಸಿರುಮನೆ ಬಗ್ಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
    return "Hello! How can I help with your tomato crop, disease, pests, irrigation, or greenhouse today?"


def answer_farmer_question(question, language, analysis_context=""):
    """Answer a farmer in their selected language using English RAG material.

    General Kannada chat preserves its existing English retrieval and answer
    pipeline. Structured analysis chat uses English retrieval plus a complete
    Kannada generated or offline answer that retains the same analysis facts.
    """
    # Greetings are social messages, not agricultural questions.  Sending
    # them to semantic retrieval can return an unrelated crop document.
    if is_greeting(question):
        return greeting_response(language), [], False, True

    retrieval_question = question
    question_translated = True
    if language == "Kannada":
        retrieval_question, question_translated = translate_rag_query_to_english(question)
        retrieval_question = retrieval_question or "management advice"
        if not question_translated and not has_analysis_context(analysis_context):
            return (
                "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಹುಡುಕಾಟಕ್ಕೆ ಸಿದ್ಧಪಡಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೊಮ್ಯಾಟೊ, ನೀರಾವರಿ, ರೋಗ, ಕೀಟ, ಹಸಿರುಮನೆ ಅಥವಾ ಸರ್ಕಾರಿ ಯೋಜನೆ ಎಂಬ ಮುಖ್ಯ ಪದದೊಂದಿಗೆ ಮತ್ತೆ ಕೇಳಿ.",
                [],
                False,
                False,
            )

    if has_analysis_context(analysis_context):
        # Both generated and offline replies retain the same analysis facts,
        # including in Kannada. Generic Kannada queries can still use the
        # analyses when the optional question translator is unavailable.
        results = _retrieve_with_analysis(retrieval_question, analysis_context)
        response, generated = answer(retrieval_question, results, language, analysis_context)
        return response, results, generated, question_translated

    results = retrieve(retrieval_question)
    english_answer, generated = answer(
        retrieval_question, results, "English", analysis_context
    )

    if language != "Kannada":
        return english_answer, results, generated, True

    kannada_answer = _kannada_grounded_answer(
        retrieval_question, english_answer, results
    )
    return kannada_answer, results, generated, question_translated
