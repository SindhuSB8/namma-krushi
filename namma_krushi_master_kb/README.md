# Namma Krushi — Master Knowledge Base

This package is a curated English knowledge base for the academic prototype **Namma Krushi: an AI-driven Kannada–English advisory system for greenhouse tomato cultivation**.

## What this KB is intended to answer

The RAG layer should be able to answer farmer questions about tomato crop basics, nursery and transplanting, protected cultivation, greenhouse environment, irrigation, soil moisture, nutrition, fertigation, training and pruning, pollination, flowering and fruit set, physiological disorders, major tomato diseases, important pests, integrated pest management, and selected Central/Karnataka government scheme discovery.

The disease documents deliberately include the labels used by common tomato image datasets so that a CNN prediction such as `Early Blight`, `Late Blight`, `Tomato Yellow Leaf Curl Virus`, `Tomato Mosaic Virus`, `Bacterial Spot`, `Septoria Leaf Spot`, `Leaf Mold`, `Target Spot`, `Powdery Mildew`, `Spider Mites`, or `Healthy` can be passed directly to the RAG layer for a grounded explanation.

## Important architecture rule

Use this KB as the **retrieval and explanation layer**, not as a replacement for the greenhouse ML model or image classifier.

- Disease CNN -> class + confidence -> retrieve the matching disease article -> farmer-friendly explanation.
- Greenhouse ML -> Suitable / Needs Adjustment / Unsuitable + XAI factors -> retrieve environment and management articles -> recommendation.
- Scheme question -> route to the scheme index -> return official source and a freshness warning.
- Kannada question -> translate to English -> retrieve from this English KB -> generate grounded English answer -> translate back to Kannada.

## Recommended FAISS layout

Build two indexes:

1. `agriculture.faiss` for agriculture, disease, pest, and farmer-advisory documents.
2. `schemes.faiss` for government scheme documents.

Do not mix scheme chunks with agronomy chunks in one index unless you add a reliable metadata filter/router.

## Recommended embeddings

Use `BAAI/bge-m3` when the machine can handle it. It is a strong choice for this project because it supports multilingual retrieval and leaves room for later direct Kannada retrieval. If the local machine is constrained, a smaller E5/BGE embedding model can be substituted, but the FAISS index must then be rebuilt with that model.

## Recommended chunking

Start with 450–700 tokens per chunk with 80–120 tokens overlap. Prefer semantic headings as boundaries. Preserve metadata: `title`, `category`, `tags`, `source_ids`, `freshness`, and `file_path`.

Do **not** split short disease articles into tiny fragments that separate symptoms from management. The RAG answer is much better when the retrieved chunk contains disease name + recognition clues + management context.

## Freshness policy

Agronomy articles are relatively stable, but pesticide registrations, fertilizer recommendations, scheme benefits, eligibility rules, application windows, and subsidy rates can change. The chatbot should state the official source and ask the farmer to verify current local guidance when a decision depends on a changing rule.

## Scope boundary

This KB is intentionally broad **within greenhouse tomato cultivation**. It should not pretend to answer unrelated medicine, law, finance, or crops outside scope. If the KB does not contain enough evidence, the chatbot should say that and direct the farmer to an agricultural officer, KVK, horticulture department, or the relevant official portal.
