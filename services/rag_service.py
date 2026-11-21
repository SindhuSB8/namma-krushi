"""Read-only RAG retrieval with a practical offline fallback."""
import json
import math
import re
from functools import lru_cache

import numpy as np
from config import FAISS_ROOT, RAG_RETRIEVAL_MODE
from services.text_cleaning import clean_farmer_text
from services.kb_supplement import unindexed_scheme_chunks

# Scheme routing uses whole-word matching in three tiers, so everyday farming
# words ("apply fungicide", "benefit of ventilation") are not mistaken for
# government-scheme questions.
_STRONG_SCHEME = (
    r"schemes?", r"yojana", r"subsid(?:y|ies)", r"government", r"govt", r"loans?", r"credit", r"insurance",
    r"pm[\s-]?kisan", r"pmkisan", r"pmfby", r"kcc", r"midh", r"nhb", r"nhm", r"kusum", r"solar pumps?",
    r"horticulture mission", r"pension", r"maandhan", r"soil health cards?", r"e-?nam", r"interest subvention",
    r"fpos?", r"farmer producer", r"pmfme", r"per drop", r"pdmc", r"custom hiring", r"operation greens",
    r"market intervention", r"sampada", r"rkvy", r"pkvy", r"price support", r"mahadbt", r"ikhedut", r"raj kisan",
)
# Topic words that mean "scheme" only when money/support wording is present.
_TOPIC_WORDS = (r"polyhouse", r"greenhouse", r"micro[\s-]?irrigation", r"drip", r"mechani[sz]ation",
                r"cold chain", r"natural farming", r"shade ?net", r"protected cultivation")
_MONEY_WORDS = (r"subsid(?:y|ies)", r"grants?", r"schemes?", r"loans?", r"credit", r"financial assistance",
                r"funding", r"funds?", r"assistance", r"incentives?", r"cost sharing")
# Weak words never route alone: they need a scheme or topic word beside them.
_WEAK_WORDS = (r"apply", r"application", r"eligib\w*", r"benefits?", r"documents?")
_alt = lambda parts: re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")
_STRONG_RE, _TOPIC_RE, _MONEY_RE, _WEAK_RE = map(_alt, (_STRONG_SCHEME, _TOPIC_WORDS, _MONEY_WORDS, _WEAK_WORDS))
TOPIC_HINTS = {
    "yield": ("fruit", "fruit set", "flower", "pollination", "irrigation", "nutrition", "fertigation", "harvest", "ventilation"),
    "grow": ("tomato", "nursery", "transplant", "irrigation", "nutrition", "harvest"),
    "home": ("tomato", "nursery", "transplant", "irrigation", "root zone"),
    "yellow": ("yellow", "disease", "irrigation", "root zone", "nutrition"),
    "wilt": ("wilt", "irrigation", "root", "disease"),
    "humidity": ("humidity", "ventilation", "leaf wetness"),
    "temperature": ("temperature", "ventilation", "fruit set"),
    "water": ("irrigation", "soil moisture", "root zone", "drainage"),
    "irrigation": ("water", "soil moisture", "root zone", "drainage"),
    "pest": ("pest", "whiteflies", "thrips", "leaf miner", "fruit borer"),
    "disease": ("disease", "leaf", "blight", "wilt", "spot"),
    "polyhouse": ("protected cultivation", "greenhouse", "shade net", "midh"),
    "greenhouse": ("protected cultivation", "polyhouse", "midh"),
}
INTENT_DOCUMENTS = {
    "yield": {"05_temperature_humidity_and_ventilation", "07_irrigation_and_soil_moisture", "08_fertigation_and_nutrition", "09_training_pruning_and_trellising", "10_pollination_flowering_and_fruit_set"},
    "grow": {"01_tomato_crop_basics", "02_nursery_and_transplanting", "07_irrigation_and_soil_moisture", "08_fertigation_and_nutrition"},
    "home": {"01_tomato_crop_basics", "02_nursery_and_transplanting", "07_irrigation_and_soil_moisture"},
    "polyhouse": {"01_midh_protected_cultivation", "08_national_horticulture_mission"},
    "greenhouse": {"01_midh_protected_cultivation", "08_national_horticulture_mission"},
    "sauce": {"15_pmfme_food_processing"}, "puree": {"15_pmfme_food_processing"}, "ketchup": {"15_pmfme_food_processing"},
    "processing": {"15_pmfme_food_processing"},
}
STOP_WORDS = {"a", "an", "and", "are", "can", "do", "fast", "for", "get", "how", "i", "in", "is", "my", "of", "the", "to", "what", "with", "should", "not", "much", "does", "will"}

# Words every scheme article contains; they say nothing about WHICH scheme is meant.
GENERIC_SCHEME_WORDS = {"scheme", "schemes", "government", "govt", "offer", "offers", "offered", "available", "which", "any", "there", "yojana"}

# State articles answer "polyhouse subsidy in <state>"; for a question that names no
# state, the national schemes (MIDH, NHB) must come first.
STATE_SCHEME_KEYWORDS = {
    "25_karnataka_protected_cultivation": ("karnataka", "fruits id"),
    "26_tamil_nadu_horticulture_subsidies": ("tamil", "tamilnadu"),
    "27_maharashtra_polyhouse_pocra": ("maharashtra", "mahadbt", "pocra"),
    "28_gujarat_ikhedut_horticulture": ("gujarat", "ikhedut"),
    "29_rajasthan_polyhouse_subsidy": ("rajasthan", "raj kisan"),
    "30_north_india_haryana_punjab_himachal": ("haryana", "punjab", "himachal"),
    "31_telangana_andhra_horticulture": ("telangana", "andhra"),
}

def _present(item):
    """Scheme articles carry builder notes ("the chatbot should ...", "Source note").
    Strip them from the text instead of discarding the whole chunk, otherwise
    PM-KISAN, KCC, PMFBY and AIF could never be found."""
    if item.get("category") == "scheme":
        return {**item, "text": clean_farmer_text(item.get("text", ""))}
    return item

def _farmer_facing(item):
    """Keep RAG authoring notes out of farmer-facing search results."""
    if item.get("category") == "scheme":
        return bool(clean_farmer_text(item.get("text", "")).strip())
    text = item.get("text", "").lower()
    heading = text.lstrip().splitlines()[0] if text.strip() else ""
    if item.get("document_id") in {
        "04_greenhouse_analysis_to_advice",
        "05_disease_prediction_to_advice",
    }:
        return False
    internal_headings = (
        "chatbot",
        "source note",
        "ml integration",
        "advisory behavior",
        "history data in namma krushi",
        "chat-history integration",
    )
    return not any(marker in heading for marker in internal_headings) and not any(
        marker in text for marker in ("the chatbot should", "the rag answer should", "for the namma krushi prototype")
    )

def route(query):
    text = (query or "").lower()
    if _STRONG_RE.search(text):
        return "schemes"
    if _TOPIC_RE.search(text) and (_MONEY_RE.search(text) or _WEAK_RE.search(text)):
        return "schemes"
    return "agriculture"

@lru_cache(maxsize=2)
def load_index(index_name):
    folder = FAISS_ROOT / index_name
    metadata = [json.loads(line) for line in (folder / "metadata.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if index_name == "schemes":
        # Articles added after the last index build are searched directly from
        # the knowledge-base folder (vectors do not cover them, so lexical search is used).
        extra = unindexed_scheme_chunks({item.get("document_id") for item in metadata})
        if extra:
            return None, metadata + extra
    try:
        import faiss
        index = faiss.read_index(str(folder / "index.faiss"))
        if index.ntotal != len(metadata):
            raise ValueError(f"{index_name} index and metadata do not match")
        return index, metadata
    except Exception:
        # Native FAISS libraries are optional. The persisted metadata remains
        # a useful, deterministic offline search source when they cannot load.
        return None, metadata

def _terms(query):
    words = set(re.findall(r"[a-z0-9]+", query.lower())) - STOP_WORDS
    expanded = set(words)
    for word, hints in TOPIC_HINTS.items():
        if word in words:
            expanded.update(hints)
    return words, expanded

def _lexical_retrieve(query, metadata, top_k, document_ids=None):
    """Rank the persisted knowledge chunks without needing a downloaded model."""
    words, expanded = _terms(query)
    if metadata and all(item.get("category") == "scheme" for item in metadata):
        specific = words - GENERIC_SCHEME_WORDS
        if specific:  # "polyhouse subsidy scheme" must rank by polyhouse/subsidy, not by "scheme"
            words, expanded = specific, expanded - GENERIC_SCHEME_WORDS
    if not words:
        return []
    candidates = [
        item for item in metadata
        if (document_ids is None or item.get("document_id") in document_ids) and _farmer_facing(item)
    ]
    weight = {word: 1.0 for word in words | expanded}
    is_scheme_index = bool(candidates) and all(item.get("category") == "scheme" for item in candidates)
    cap = 3 if is_scheme_index else 10**6   # a word repeated many times must not drown a rarer match
    if is_scheme_index:
        # Rare words identify the scheme ("polyhouse"); words most schemes share
        # ("subsidy", "loan") must not outvote them.
        corpus = [f"{item.get('topic', '')} {item.get('text', '')}".lower() for item in candidates]
        for word in weight:
            df = sum(word in text for text in corpus)
            weight[word] = 1.0 + math.log((len(corpus) + 1) / (df + 1))
    # A hyphenated name such as "pm-kisan" must match that scheme, not every "kisan" article.
    names = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", query.lower()))
    ranked = []
    for item in candidates:
        # Persisted chunks often lack a section field. Include their heading
        # so a management query selects practical advice over crop basics.
        heading = item.get("text", "").splitlines()[0] if item.get("text") else ""
        title = f"{item.get('topic', '')} {item.get('section') or ''} {heading}".lower()
        body = item.get("text", "").lower()
        score = sum(weight[word] * (12 * (word in title) + 2 * min(body.count(word), cap)) for word in words)
        score += sum(weight[hint] * (5 * (hint in title) + min(3, body.count(hint))) for hint in expanded - words)
        score += sum(25 * (name in title) + 4 * body.count(name) for name in names)
        state_words = STATE_SCHEME_KEYWORDS.get(item.get("document_id"))
        if state_words and not any(word in query.lower() for word in state_words):
            score *= 0.5
        for intent, documents in INTENT_DOCUMENTS.items():
            if intent in words and item.get("document_id") in documents:
                score += 40
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    selected, selected_document_ids = [], set()
    for score, item in ranked:
        # A zero-score item is not a search result. Returning it previously
        # made unknown queries look as if they matched random documents.
        if score <= 0:
            continue
        # General search shows distinct articles. A scoped analysis search
        # can retrieve several sections from its specific evidence article.
        document_id = item.get("document_id")
        if document_id in selected_document_ids and document_ids is None:
            continue
        selected_document_ids.add(document_id)
        selected.append({**_present(item), "score": float(score), "retrieval_mode": "offline"})
        if len(selected) == top_k:
            break
    return selected

@lru_cache(maxsize=1)
def _embedding_model():
    # Never try to download models during a farmer interaction.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("BAAI/bge-m3", local_files_only=True)

def retrieve(query, index_name=None, top_k=4, *, document_ids=None):
    """Search existing indexes; optionally focus on sections of known articles."""
    if document_ids is not None:
        document_ids = set(document_ids)
        if not document_ids:
            return []
    index_name = index_name or route(query)
    # This is the normal farmer-chat path: fast, deterministic and completely
    # local. It avoids loading BGE-M3/Torch (and optional torchvision) just to
    # answer a short practical question.
    if RAG_RETRIEVAL_MODE != "semantic":
        _, metadata = load_index(index_name)
        return _lexical_retrieve(query, metadata, min(top_k, len(metadata)), document_ids)
    index, metadata = load_index(index_name)
    if index is None:
        return _lexical_retrieve(query, metadata, min(top_k, len(metadata)), document_ids)
    # For common broad farmer intents, the curated topic expansion is more
    # precise than a generic semantic nearest neighbour (for example, "yield"
    # should surface fruit set, irrigation and nutrition material).
    query_words, _ = _terms(query)
    if index_name == "agriculture" and query_words.intersection(TOPIC_HINTS):
        return _lexical_retrieve(query, metadata, min(top_k, len(metadata)), document_ids)
    try:
        model = _embedding_model()
        vector = np.asarray(model.encode([query], normalize_embeddings=True), dtype="float32")
        candidate_count = index.ntotal if document_ids is not None else min(max(top_k * 3, top_k + 6), index.ntotal)
        scores, ids = index.search(vector, candidate_count)
        results = [
            {**_present(metadata[int(i)]), "score": float(score), "retrieval_mode": "semantic"}
            for score, i in zip(scores[0], ids[0])
            if i >= 0 and _farmer_facing(metadata[int(i)])
            and (document_ids is None or metadata[int(i)].get("document_id") in document_ids)
        ]
        return results[:top_k]
    except Exception:
        return _lexical_retrieve(query, metadata, min(top_k, len(metadata)), document_ids)

def sources(results):
    seen, output = set(), []
    for item in results:
        url = item.get("source_url")
        if url and url not in seen:
            seen.add(url)
            output.append({"name": item.get("source_name") or item.get("topic"), "topic": item.get("topic"), "url": url})
    return output
