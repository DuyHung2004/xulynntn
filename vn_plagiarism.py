"""
Hệ thống phát hiện đạo văn tiếng Việt (môn Xử lý ngôn ngữ tự nhiên).

Pipeline:
    1. Tiền xử lý: chuẩn hoá Unicode (NFC), chữ thường, bỏ dấu câu,
       tách từ (underthesea / pyvi nếu có, nếu không thì tách theo âm tiết),
       loại bỏ stopword.
    2. Đặc trưng / độ tương đồng:
         - TF-IDF + cosine            (tương đồng theo từ vựng)
         - Jaccard trên word n-gram   (sao chép nguyên văn từng cụm)
         - Winnowing fingerprint      (Schleimer et al., 2003 - như MOSS)
         - (tuỳ chọn) embedding ngữ nghĩa bằng sentence-transformers,
           để bắt được diễn đạt lại (paraphrase)
    3. Phát hiện mức câu: với mỗi câu trong văn bản nghi vấn, tìm câu giống
       nhất trong kho tài liệu gốc -> đoạn nghi đạo văn + nguồn.
    4. Điểm tổng hợp và kết luận theo ngưỡng.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------
# 1. Tiền xử lý
# --------------------------------------------------------------------------

# Danh sách stopword tiếng Việt rút gọn (có thể mở rộng từ file ngoài)
VI_STOPWORDS = set("""
và của là có trong cho các những một được này đó với để khi từ đã sẽ đang
cũng như nhưng thì mà bị bởi theo về ra vào lên xuống rất hơn nhiều ít
tại do nên vì nếu hay hoặc còn cả đều chỉ vẫn lại đây kia ấy nào gì
""".split())

_TOKENIZER = None


def _load_tokenizer():
    """Thử underthesea -> pyvi -> None (tách theo âm tiết)."""
    global _TOKENIZER
    if _TOKENIZER is not None:
        return _TOKENIZER
    try:
        from underthesea import word_tokenize  # type: ignore
        _TOKENIZER = lambda s: word_tokenize(s, format="text").split()
    except Exception:
        try:
            from pyvi import ViTokenizer  # type: ignore
            _TOKENIZER = lambda s: ViTokenizer.tokenize(s).split()
        except Exception:
            _TOKENIZER = lambda s: s.split()
    return _TOKENIZER


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)  # bỏ dấu câu, giữ chữ có dấu
    text = re.sub(r"\d+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    tok = _load_tokenizer()
    tokens = tok(normalize(text))
    if remove_stopwords:
        tokens = [t for t in tokens if t not in VI_STOPWORDS]
    return tokens


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.split()) >= 3]


# --------------------------------------------------------------------------
# 2. Các độ đo tương đồng
# --------------------------------------------------------------------------

def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def jaccard_ngram(a: list[str], b: list[str], n: int = 3) -> float:
    """Jaccard trên tập n-gram từ."""
    sa, sb = set(ngrams(a, n)), set(ngrams(b, n))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def containment_ngram(a: list[str], b: list[str], n: int = 3) -> float:
    """Tỉ lệ n-gram của a xuất hiện trong b (phù hợp khi a ngắn hơn b)."""
    sa, sb = set(ngrams(a, n)), set(ngrams(b, n))
    return len(sa & sb) / len(sa) if sa else 0.0


def winnowing(tokens: list[str], k: int = 4, w: int = 4) -> set[int]:
    """Winnowing: lấy hash nhỏ nhất trong mỗi cửa sổ w hash của k-gram."""
    grams = [" ".join(g) for g in ngrams(tokens, k)]
    if not grams:
        return set()
    hashes = [int(hashlib.md5(g.encode()).hexdigest()[:8], 16) for g in grams]
    if len(hashes) <= w:
        return {min(hashes)}
    return {min(hashes[i:i + w]) for i in range(len(hashes) - w + 1)}


def winnowing_similarity(a: list[str], b: list[str], k: int = 4, w: int = 4) -> float:
    fa, fb = winnowing(a, k, w), winnowing(b, k, w)
    if not fa or not fb:
        return 0.0
    return len(fa & fb) / min(len(fa), len(fb))


# --------------------------------------------------------------------------
# 3. Bộ phát hiện
# --------------------------------------------------------------------------

@dataclass
class SentenceMatch:
    suspect_sentence: str
    source_id: str
    source_sentence: str
    score: float


@dataclass
class DocResult:
    source_id: str
    tfidf_cosine: float
    jaccard_3gram: float
    containment_3gram: float
    winnowing: float
    semantic: float | None
    score: float


@dataclass
class Report:
    overall_score: float
    verdict: str
    per_document: list[DocResult] = field(default_factory=list)
    matches: list[SentenceMatch] = field(default_factory=list)
    plagiarized_ratio: float = 0.0  # % câu nghi vấn bị đánh dấu


class PlagiarismDetector:
    """
    Cách dùng:
        det = PlagiarismDetector()
        det.fit({"doc1": "...", "doc2": "..."})
        report = det.check("văn bản cần kiểm tra")
    """

    def __init__(self, sentence_threshold: float = 0.55,
                 use_semantic: bool = False,
                 semantic_model: str = "keepitreal/vietnamese-sbert",
                 weights: dict | None = None,
                 use_sentence_level: bool = True):
        self.sentence_threshold = sentence_threshold
        self.use_sentence_level = use_sentence_level
        self.use_semantic = use_semantic
        self.weights = weights or {"tfidf": 0.25, "containment": 0.35,
                                   "winnowing": 0.25, "semantic": 0.15}
        self._sbert = None
        if use_semantic:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._sbert = SentenceTransformer(semantic_model)
        self.docs: dict[str, str] = {}

    # ---- huấn luyện trên kho tài liệu gốc ----
    def fit(self, docs: dict[str, str]) -> "PlagiarismDetector":
        self.docs = docs
        self.doc_tokens = {k: tokenize(v) for k, v in docs.items()}
        self.vec_doc = TfidfVectorizer(analyzer=lambda x: x, sublinear_tf=True)
        self.doc_matrix = self.vec_doc.fit_transform(self.doc_tokens.values())

        # kho câu để so khớp mức câu
        self.src_sents: list[tuple[str, str]] = []  # (doc_id, câu gốc)
        for did, text in docs.items():
            for s in split_sentences(text):
                self.src_sents.append((did, s))
        self.src_sent_tokens = [tokenize(s) for _, s in self.src_sents]
        self.vec_sent = TfidfVectorizer(
            analyzer=lambda x: x + [" ".join(g) for g in ngrams(x, 2)],
            sublinear_tf=True)
        self.sent_matrix = self.vec_sent.fit_transform(self.src_sent_tokens)
        if self._sbert is not None:
            self.src_emb = self._sbert.encode([s for _, s in self.src_sents],
                                              normalize_embeddings=True)
        return self

    # ---- kiểm tra một văn bản ----
    def check(self, text: str, top_k: int = 5) -> Report:
        susp_tokens = tokenize(text)
        susp_vec = self.vec_doc.transform([susp_tokens])
        cos = cosine_similarity(susp_vec, self.doc_matrix)[0]

        results: list[DocResult] = []
        for i, (did, toks) in enumerate(self.doc_tokens.items()):
            sem = None
            if self._sbert is not None:
                e = self._sbert.encode([text, self.docs[did]], normalize_embeddings=True)
                sem = float(e[0] @ e[1])
            jac = jaccard_ngram(susp_tokens, toks)
            con = containment_ngram(susp_tokens, toks)
            win = winnowing_similarity(susp_tokens, toks)
            w = self.weights
            if sem is None:
                tot = w["tfidf"] + w["containment"] + w["winnowing"]
                score = (w["tfidf"] * cos[i] + w["containment"] * con
                         + w["winnowing"] * win) / tot
            else:
                score = (w["tfidf"] * cos[i] + w["containment"] * con
                         + w["winnowing"] * win + w["semantic"] * sem)
            results.append(DocResult(did, float(cos[i]), jac, con, win, sem, float(score)))
        results.sort(key=lambda r: r.score, reverse=True)

        if self.use_sentence_level:
            matches, ratio = self._sentence_level(text)
        else:
            matches, ratio = [], 0.0
        best = results[0].score if results else 0.0
        overall = max(best, ratio)
        return Report(overall_score=overall, verdict=self._verdict(overall),
                      per_document=results[:top_k], matches=matches,
                      plagiarized_ratio=ratio)

    # ---- mức câu ----
    def _sentence_level(self, text: str) -> tuple[list[SentenceMatch], float]:
        sents = split_sentences(text)
        if not sents or not self.src_sents:
            return [], 0.0
        toks = [tokenize(s) for s in sents]
        sims = cosine_similarity(self.vec_sent.transform(toks), self.sent_matrix)
        if self._sbert is not None:
            sem = self._sbert.encode(sents, normalize_embeddings=True) @ self.src_emb.T
            sims = 0.6 * sims + 0.4 * sem
        matches = []
        for i, s in enumerate(sents):
            j = int(np.argmax(sims[i]))
            if sims[i, j] >= self.sentence_threshold:
                matches.append(SentenceMatch(s, self.src_sents[j][0],
                                             self.src_sents[j][1], float(sims[i, j])))
        return matches, len(matches) / len(sents)

    @staticmethod
    def _verdict(score: float) -> str:
        if score >= 0.7:
            return "ĐẠO VĂN CAO (sao chép gần như nguyên văn)"
        if score >= 0.4:
            return "NGHI VẤN ĐẠO VĂN (có nhiều đoạn trùng/diễn đạt lại)"
        if score >= 0.2:
            return "TRÙNG LẶP THẤP (cần xem lại các đoạn được đánh dấu)"
        return "KHÔNG PHÁT HIỆN ĐẠO VĂN"


def print_report(rep: Report) -> None:
    print(f"Điểm tổng hợp: {rep.overall_score:.1%} -> {rep.verdict}")
    print(f"Tỉ lệ câu bị đánh dấu: {rep.plagiarized_ratio:.1%}")
    print("\nTài liệu giống nhất:")
    for r in rep.per_document:
        sem = f" sem={r.semantic:.2f}" if r.semantic is not None else ""
        print(f"  - {r.source_id}: score={r.score:.2f} tfidf={r.tfidf_cosine:.2f} "
              f"contain3={r.containment_3gram:.2f} winnow={r.winnowing:.2f}{sem}")
    if rep.matches:
        print("\nCác câu nghi vấn:")
        for m in rep.matches:
            print(f"  [{m.score:.2f}] \"{m.suspect_sentence}\"\n"
                  f"        <- {m.source_id}: \"{m.source_sentence}\"")


# --------------------------------------------------------------------------
# 5. Tiện ích: nạp kho tài liệu từ thư mục
# --------------------------------------------------------------------------

def load_corpus_dir(path) -> dict[str, str]:
    """Đọc mọi file .txt trong thư mục thành dict {tên file không đuôi: nội dung}."""
    from pathlib import Path
    docs = {}
    for f in sorted(Path(path).glob("*.txt")):
        txt = f.read_text(encoding="utf-8").strip()
        if txt:
            docs[f.stem] = txt
    return docs
