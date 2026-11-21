"""Demo nhanh: chạy 4 văn bản mẫu với kho tài liệu trong data/corpus."""
import csv
import pathlib
import warnings

warnings.filterwarnings("ignore")
from vn_plagiarism import PlagiarismDetector, load_corpus_dir, print_report

ROOT = pathlib.Path(__file__).parent
det = PlagiarismDetector(sentence_threshold=0.5).fit(load_corpus_dir(ROOT / "data/corpus"))

rows = list(csv.DictReader((ROOT / "data/benchmark/benchmark.csv").open(encoding="utf-8")))
picked = {}
for r in rows:
    picked.setdefault(r["type"], r)
for kind, title in [("copy", "Chép nguyên văn"), ("light", "Sửa nhẹ"), ("mosaic", "Ghép từ 2 nguồn"),
                    ("independent", "Tự viết cùng chủ đề (không đạo văn)")]:
    print("=" * 78, f"\n{title}\n", "=" * 78, sep="")
    print_report(det.check(picked[kind]["text"]))
    print()
