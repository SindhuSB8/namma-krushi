# RAG Build Guide for Antigravity / Claude

## Goal
Create production-like retrieval artifacts from this KB without exposing build internals in the farmer UI.

## Collections

### agriculture
Include:
- `agriculture/*.md`
- `diseases/*.md`
- `pests/*.md`
- `farmer_advisory/*.md`
- `00_rag_answering_policy.md`

### schemes
Include:
- `schemes/*.md`

## Embedding model
Preferred: `BAAI/bge-m3`.

Use the same embedding model for indexing and query-time embeddings. Store the exact model name and revision in the manifest. If you change the embedding model, rebuild the entire FAISS index.

## Chunking

Recommended starting point:
- target: 450–700 tokens
- overlap: 80–120 tokens
- split first by Markdown headings, then by paragraphs
- do not split very short disease documents unnecessarily

## Metadata per chunk

```json
{
  "chunk_id": "diseases/03_early_blight.md::symptoms::001",
  "title": "Early Blight",
  "category": "disease",
  "tags": ["early blight", "Alternaria", "cnn label"],
  "source_ids": ["S12", "S05", "S34"],
  "freshness": "stable",
  "file_path": "diseases/03_early_blight.md"
}
```

## FAISS artifacts

Recommended output:

```text
artifacts/faiss/
  agriculture/
    index.faiss
    metadata.jsonl
    manifest.json
  schemes/
    index.faiss
    metadata.jsonl
    manifest.json
```

`manifest.json` should include embedding model, dimension, distance metric, creation timestamp, document count, chunk count, and a checksum of input files.

## Retrieval routing

- disease/pest/cultivation/greenhouse question -> agriculture index
- subsidy/scheme/eligibility/loan/insurance question -> schemes index
- ambiguous question -> search both, then rerank

## Query normalization

If Kannada is selected:
Kannada input -> IndicTrans2 Kannada→English -> retrieval query -> answer generation -> IndicTrans2 English→Kannada.

Preserve the original Kannada message for chat history, but retrieval can run on the translated English query.

## Retrieval settings

Start with top-k 6–8, then rerank to 3–5 passages for final prompting. Use metadata filters when a disease class or scheme intent is already known. For example, when the CNN returns `Early Blight`, prefer chunks tagged `early blight` before broad semantic search.

## Prompt guardrails

The answer prompt should say:
- use only retrieved context for factual agricultural claims;
- state uncertainty when evidence is insufficient;
- do not invent pesticide doses or scheme eligibility;
- for time-sensitive schemes, include official source and freshness warning;
- if the app provides ML/XAI context, use it exactly and do not fabricate feature contributions.
