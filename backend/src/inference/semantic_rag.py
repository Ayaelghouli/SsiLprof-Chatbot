import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi


model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

documents        = []
metadata         = []
index            = None
bm25             = None
tokenized_corpus = []


def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def build_index(kb_data):
    global documents, metadata, index, bm25, tokenized_corpus

    documents        = []
    metadata         = []
    tokenized_corpus = []

    # index schools
    for school in kb_data.get("ecoles", []):
        category = school.get("category", "")
        text = f"""
        orientation ecole
        {school.get("School_Name")} {school.get("full_name")}
        {category} {category}
        {school.get("interests")}
        {school.get("Filiéres")}
        {school.get("Careers")}
        {school.get("Descreptions")}
        {school.get("Conditions")}
        {school.get("Seuils")}
        {school.get("Cities")}
        """.lower()

        documents.append(text)
        metadata.append(school)
        tokenized_corpus.append(tokenize(text))

    # index social support (bourses, logement)
    for bourse in kb_data.get("soutien_social", []):
        text = f"""
        bourse {bourse.get("School_Name")} {bourse.get("full_name")}
        {bourse.get("category", "")}
        {bourse.get("Conditions")}
        {bourse.get("Descreptions")}
        {bourse.get("interests")}
        """.lower()

        documents.append(text)
        metadata.append(bourse)
        tokenized_corpus.append(tokenize(text))

    # build FAISS index (semantic)
    embeddings = model.encode(documents, normalize_embeddings=True)
    dim        = embeddings.shape[1]
    index      = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings).astype("float32"))

    # build BM25 index (keyword)
    bm25 = BM25Okapi(tokenized_corpus)

    print(f"hybrid RAG ready: {len(documents)} documents")

    return index, documents


def semantic_search(query, top_k=5, alpha=0.65):
    """
    hybrid search: FAISS (semantic) + BM25 (keyword)

    alpha=1.0 → semantic only
    alpha=0.0 → keyword only
    alpha=0.65 → default, favors semantic
    """
    global index, bm25, documents, metadata

    if index is None:
        return []

    # semantic scores via FAISS
    q_vec    = model.encode([query], normalize_embeddings=True)
    scores_s, idx_s = index.search(np.array(q_vec).astype("float32"), top_k * 3)

    semantic_scores = {}
    for rank, i in enumerate(idx_s[0]):
        if i != -1:
            semantic_scores[i] = float(scores_s[0][rank])

    # keyword scores via BM25
    bm25_scores = np.array(bm25.get_scores(tokenize(query)))
    if bm25_scores.max() > 0:
        bm25_scores = bm25_scores / bm25_scores.max()

    # fusion
    final_scores = {}
    for i in range(len(documents)):
        s = semantic_scores.get(i, 0)
        k = bm25_scores[i]
        final_scores[i] = alpha * s + (1 - alpha) * k

    # sort and return top_k
    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return [metadata[i] for i, _ in ranked[:top_k]]