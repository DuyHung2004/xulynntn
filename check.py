"""
Kiểm tra một file văn bản bằng dòng lệnh.

    python check.py bai_nop.txt
    python check.py bai_nop.txt --corpus data/corpus --threshold 0.5 --semantic
"""
import argparse
import pathlib
import warnings

warnings.filterwarnings("ignore")
from vn_plagiarism import PlagiarismDetector, load_corpus_dir, print_report

ap = argparse.ArgumentParser(description="Phát hiện đạo văn tiếng Việt")
ap.add_argument("file", help="file .txt (UTF-8) cần kiểm tra")
ap.add_argument("--corpus", default=str(pathlib.Path(__file__).parent / "data" / "corpus"),
                help="thư mục chứa các file .txt gốc")
ap.add_argument("--threshold", type=float, default=0.55, help="ngưỡng đánh dấu câu (mặc định 0.55)")
ap.add_argument("--semantic", action="store_true", help="bật độ giống ngữ nghĩa (cần sentence-transformers)")
a = ap.parse_args()

corpus = load_corpus_dir(a.corpus)
if not corpus:
    raise SystemExit(f"Kho tài liệu trống: {a.corpus}")
det = PlagiarismDetector(sentence_threshold=a.threshold, use_semantic=a.semantic).fit(corpus)
print_report(det.check(pathlib.Path(a.file).read_text(encoding="utf-8")))
