"""
retrieval.py
TF-IDF + cosine similarity retrieval over stored chunks.
No API key or model download required -> demos reliably offline.
Swap in real embeddings (OpenAI/sentence-transformers) later if you want
better semantic recall.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import store


def search(query, top_k=6):
    chunks = store.all_chunks()
    if not chunks:
        return []

    texts = [c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform(texts + [query])
    except ValueError:
        # e.g. empty vocabulary
        return []

    doc_vectors = matrix[:-1]
    query_vector = matrix[-1]
    sims = cosine_similarity(query_vector, doc_vectors)[0]

    ranked = sorted(zip(chunks, sims), key=lambda x: x[1], reverse=True)
    results = [{**c, "score": float(s)} for c, s in ranked[:top_k] if s > 0]
    return results
