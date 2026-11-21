"""
Giao diện web (Streamlit) cho hệ thống phát hiện đạo văn tiếng Việt.

Chạy:  streamlit run app.py
"""
import csv
import html
import pathlib
import re
import warnings

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")
from vn_plagiarism import PlagiarismDetector, load_corpus_dir, split_sentences  # noqa: E402

ROOT = pathlib.Path(__file__).parent
CORPUS_DIR = ROOT / "data" / "corpus"
BENCH = ROOT / "data" / "benchmark" / "benchmark.csv"

st.set_page_config(page_title="Phát hiện đạo văn tiếng Việt", page_icon="🔎", layout="wide")

# ------------------------------------------------------------------ helpers

def slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return name[:60] or "tai_lieu"


@st.cache_resource(show_spinner="Đang học kho tài liệu...")
def build_detector(corpus_items: tuple, sentence_threshold: float, use_semantic: bool):
    det = PlagiarismDetector(sentence_threshold=sentence_threshold, use_semantic=use_semantic)
    return det.fit(dict(corpus_items))


@st.cache_data
def load_samples():
    if not BENCH.exists():
        return {}
    rows = list(csv.DictReader(BENCH.open(encoding="utf-8")))
    labels = {"copy": "Chép nguyên văn", "copy_mix": "Chép 2 câu + câu tự viết", "light": "Sửa nhẹ (đổi vài từ)",
              "heavy": "Đổi nhiều từ", "shuffle": "Đảo thứ tự câu", "mosaic": "Ghép từ 2 nguồn",
              "paraphrase": "Diễn đạt lại (viết tay)", "independent": "Tự viết cùng chủ đề (sạch)",
              "mixed": "Hai văn bản độc lập (sạch)", "unrelated": "Khác chủ đề (sạch)"}
    out, seen = {}, {}
    for r in rows:
        seen[r["type"]] = seen.get(r["type"], 0) + 1
        out[f"{labels.get(r['type'], r['type'])} #{seen[r['type']]}"] = r["text"]
    return dict(sorted(out.items()))


def highlight(text: str, matches) -> str:
    by_sent = {m.suspect_sentence: m for m in matches}
    parts = []
    for s in split_sentences(text):
        m = by_sent.get(s)
        if m:
            tip = html.escape(f"{m.source_id} · {m.score:.0%}")
            parts.append(f'<mark title="{tip}" style="background:#ffd9d9;padding:2px 4px;border-radius:4px">'
                         f'{html.escape(s)}</mark>')
        else:
            parts.append(html.escape(s))
    return " ".join(parts)


VERDICT_COLOR = {"ĐẠO VĂN CAO": "#c62828", "NGHI VẤN": "#ef6c00", "TRÙNG LẶP THẤP": "#f9a825", "KHÔNG PHÁT HIỆN": "#2e7d32"}

def verdict_color(v: str) -> str:
    return next((c for k, c in VERDICT_COLOR.items() if v.startswith(k)), "#555")


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.header("⚙️ Cấu hình")
    sent_th = st.slider("Ngưỡng đánh dấu câu", 0.30, 0.90, 0.55, 0.05,
                        help="Câu có điểm giống nguồn ≥ ngưỡng sẽ bị đánh dấu. Thấp: bắt nhiều hơn nhưng dễ báo nhầm.")
    use_sem = st.checkbox("Dùng độ giống ngữ nghĩa (Sentence-BERT)", value=False,
                          help="Cần cài sentence-transformers và tải mô hình lần đầu. Bắt được diễn đạt lại tốt hơn nhưng chậm.")
    st.caption("Điểm toàn bài ≥ 0.70: đạo văn cao · 0.40–0.70: nghi vấn · 0.20–0.40: trùng lặp thấp.")

corpus = load_corpus_dir(CORPUS_DIR) if CORPUS_DIR.exists() else {}
tab_check, tab_corpus, tab_eval = st.tabs(["🔎 Kiểm tra", "📚 Kho tài liệu", "📊 Đánh giá"])

# ------------------------------------------------------------------ tab: kiểm tra

with tab_check:
    st.title("Phát hiện đạo văn tiếng Việt")
    st.write(f"So sánh văn bản của bạn với kho **{len(corpus)} tài liệu** gốc. "
             "Câu bị nghi chép sẽ được tô đỏ, rê chuột vào để xem nguồn.")
    if not corpus:
        st.warning("Kho tài liệu đang trống. Hãy thêm tài liệu ở tab 'Kho tài liệu'.")

    samples = load_samples()
    c1, c2 = st.columns([3, 2])
    with c2:
        choice = st.selectbox("Nạp văn bản mẫu", ["(không)"] + list(samples), help="Lấy từ tập kiểm thử trong data/benchmark")
        upload = st.file_uploader("Hoặc tải file .txt", type=["txt"], key="up_check")
    # chỉ nạp khi lựa chọn thay đổi, để không ghi đè nội dung người dùng đang gõ
    if choice != st.session_state.get("last_choice"):
        st.session_state["last_choice"] = choice
        if choice != "(không)":
            st.session_state["suspect"] = samples[choice]
    up_id = (upload.name, upload.size) if upload is not None else None
    if up_id != st.session_state.get("last_upload"):
        st.session_state["last_upload"] = up_id
        if upload is not None:
            st.session_state["suspect"] = upload.read().decode("utf-8", errors="ignore")
    with c1:
        text = st.text_area("Văn bản cần kiểm tra", key="suspect", height=220,
                            placeholder="Dán văn bản tiếng Việt vào đây...")

    if st.button("Kiểm tra", type="primary", disabled=not (text.strip() and corpus)):
        det = build_detector(tuple(sorted(corpus.items())), sent_th, use_sem)
        rep = det.check(text)
        col = verdict_color(rep.verdict)
        m1, m2, m3 = st.columns(3)
        m1.metric("Điểm toàn bài", f"{rep.overall_score:.0%}")
        m2.metric("Câu bị đánh dấu", f"{rep.plagiarized_ratio:.0%}")
        m3.markdown(f'<div style="padding:14px;border-radius:8px;background:{col}22;border:1px solid {col};'
                    f'color:{col};font-weight:600">{html.escape(rep.verdict)}</div>', unsafe_allow_html=True)

        st.subheader("Văn bản với các câu nghi vấn")
        st.markdown(f'<div style="line-height:1.9;font-size:1.02rem">{highlight(text, rep.matches)}</div>',
                    unsafe_allow_html=True)

        left, right = st.columns(2)
        with left:
            st.subheader("Tài liệu giống nhất")
            df = pd.DataFrame([{
                "Tài liệu": r.source_id, "Điểm": round(r.score, 3), "TF-IDF": round(r.tfidf_cosine, 3),
                "Containment 3-gram": round(r.containment_3gram, 3), "Winnowing": round(r.winnowing, 3),
                **({"Ngữ nghĩa": round(r.semantic, 3)} if r.semantic is not None else {}),
            } for r in rep.per_document])
            st.dataframe(df, hide_index=True, use_container_width=True)
        with right:
            st.subheader("Các câu bị đánh dấu")
            if rep.matches:
                for m in rep.matches:
                    with st.expander(f"{m.score:.0%} · {m.source_id}"):
                        st.markdown(f"**Câu nghi vấn:** {m.suspect_sentence}")
                        st.markdown(f"**Câu nguồn:** {m.source_sentence}")
            else:
                st.info("Không có câu nào đạt ngưỡng.")
        st.caption("Kết quả chỉ mang tính hỗ trợ; trích dẫn đúng quy cách cũng làm điểm tăng. Người đọc đưa ra kết luận cuối cùng.")

# ------------------------------------------------------------------ tab: kho tài liệu

with tab_corpus:
    st.header("Quản lý kho tài liệu gốc")
    st.write(f"Thư mục: `{CORPUS_DIR.relative_to(ROOT)}`. Mỗi tài liệu là một file `.txt` (UTF-8).")

    a, b = st.columns(2)
    with a:
        st.subheader("Thêm bằng cách dán văn bản")
        new_name = st.text_input("Tên tài liệu", placeholder="vd: bai_bao_ve_ai")
        new_text = st.text_area("Nội dung", height=160, key="new_doc_text")
        if st.button("Thêm vào kho", disabled=not (new_name.strip() and new_text.strip())):
            CORPUS_DIR.mkdir(parents=True, exist_ok=True)
            (CORPUS_DIR / f"{slugify(new_name)}.txt").write_text(new_text.strip() + "\n", encoding="utf-8")
            st.success(f"Đã thêm '{slugify(new_name)}'.")
            st.rerun()
    with b:
        st.subheader("Thêm bằng cách tải file")
        files = st.file_uploader("Chọn một hoặc nhiều file .txt", type=["txt"], accept_multiple_files=True, key="up_corpus")
        if files and st.button("Lưu các file đã chọn"):
            CORPUS_DIR.mkdir(parents=True, exist_ok=True)
            for f in files:
                (CORPUS_DIR / f"{slugify(pathlib.Path(f.name).stem)}.txt").write_text(
                    f.read().decode("utf-8", errors="ignore").strip() + "\n", encoding="utf-8")
            st.success(f"Đã lưu {len(files)} file.")
            st.rerun()

    st.subheader(f"Tài liệu hiện có ({len(corpus)})")
    if corpus:
        listing = pd.DataFrame([{"Tài liệu": k, "Số từ": len(v.split()), "Số câu": len(split_sentences(v)),
                                 "Trích đoạn": v[:90] + ("..." if len(v) > 90 else "")} for k, v in corpus.items()])
        st.dataframe(listing, hide_index=True, use_container_width=True)
        view = st.selectbox("Xem nội dung", list(corpus))
        st.text_area("Nội dung", corpus[view], height=140, disabled=True)
        to_del = st.multiselect("Chọn tài liệu để xoá", list(corpus))
        if to_del and st.button("Xoá các tài liệu đã chọn"):
            for k in to_del:
                (CORPUS_DIR / f"{k}.txt").unlink(missing_ok=True)
            st.rerun()

# ------------------------------------------------------------------ tab: đánh giá

with tab_eval:
    st.header("Kết quả đánh giá trên tập kiểm thử")
    res = ROOT / "docs" / "evaluation_results.md"
    if res.exists():
        st.markdown(res.read_text(encoding="utf-8"))
    else:
        st.info("Chưa có kết quả. Chạy `python evaluate.py` để tạo file docs/evaluation_results.md.")
    st.caption("Tạo lại tập kiểm thử bằng `python build_benchmark.py`, đánh giá lại bằng `python evaluate.py`.")
