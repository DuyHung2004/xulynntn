"""
Đánh giá hệ thống trên tập kiểm thử có nhãn (data/benchmark/benchmark.csv).

Quy trình:
  1. Chia mỗi loại mẫu thành 2 nửa: dev (chọn ngưỡng) và test (báo cáo kết quả).
  2. Với mỗi cấu hình (ablation), quét ngưỡng trên dev, chọn ngưỡng cho F1 cao nhất.
  3. Báo cáo Precision / Recall / F1 trên test tại ngưỡng đã chọn,
     cùng recall theo từng loại đạo văn và tỉ lệ báo nhầm trên mẫu sạch.

Chạy:  python evaluate.py            (ghi thêm docs/evaluation_results.md)
"""
import csv
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

from vn_plagiarism import PlagiarismDetector, load_corpus_dir  # noqa: E402

CONFIGS = {
    "A. Chỉ TF-IDF cosine": dict(weights={"tfidf": 1, "containment": 0, "winnowing": 0, "semantic": 0}, use_sentence_level=False),
    "B. Chỉ containment 3-gram": dict(weights={"tfidf": 0, "containment": 1, "winnowing": 0, "semantic": 0}, use_sentence_level=False),
    "C. Chỉ winnowing": dict(weights={"tfidf": 0, "containment": 0, "winnowing": 1, "semantic": 0}, use_sentence_level=False),
    "D. Tổ hợp 3 độ đo (không mức câu)": dict(use_sentence_level=False),
    "E. Tổ hợp 3 độ đo + mức câu (mặc định)": dict(use_sentence_level=True),
}
THRESHOLDS = [round(0.05 * i, 2) for i in range(2, 19)]  # 0.10 .. 0.90


def prf(y, p):
    tp = sum(1 for a, b in zip(y, p) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y, p) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, p) if a == 1 and b == 0)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    return pr, rc, f1


def load_benchmark():
    rows = list(csv.DictReader((ROOT / "data/benchmark/benchmark.csv").open(encoding="utf-8")))
    seen, dev, test = {}, [], []
    for r in rows:  # chia luân phiên trong từng loại -> cân bằng dev/test
        i = seen.get(r["type"], 0)
        seen[r["type"]] = i + 1
        (dev if i % 2 == 0 else test).append(r)
    return dev, test


def main():
    corpus = load_corpus_dir(ROOT / "data/corpus")
    dev, test = load_benchmark()
    types = sorted({r["type"] for r in dev + test if r["label"] == "1"})
    neg_types = sorted({r["type"] for r in dev + test if r["label"] == "0"})
    out = [f"# Kết quả đánh giá\n\nKho: {len(corpus)} tài liệu. Dev: {len(dev)} mẫu, test: {len(test)} mẫu.\n"]
    out.append("| Cấu hình | Ngưỡng (chọn trên dev) | Precision | Recall | F1 |")
    out.append("| --- | --- | --- | --- | --- |")
    per_type_lines = []

    for name, kw in CONFIGS.items():
        det = PlagiarismDetector(sentence_threshold=0.5, **kw).fit(corpus)
        score = {r["id"]: det.check(r["text"]).overall_score for r in dev + test}
        best_t, best_f = None, -1
        for t in THRESHOLDS:
            f = prf([int(r["label"]) for r in dev], [int(score[r["id"]] >= t) for r in dev])[2]
            if f > best_f:
                best_t, best_f = t, f
        y = [int(r["label"]) for r in test]
        p = [int(score[r["id"]] >= best_t) for r in test]
        pr, rc, f1 = prf(y, p)
        out.append(f"| {name} | {best_t:.2f} | {pr:.2f} | {rc:.2f} | {f1:.2f} |")
        cells = []
        for t in types:
            sub = [r for r in test if r["type"] == t]
            cells.append(f"{sum(score[r['id']] >= best_t for r in sub)}/{len(sub)}")
        for t in neg_types:
            sub = [r for r in test if r["type"] == t]
            cells.append(f"{sum(score[r['id']] >= best_t for r in sub)}/{len(sub)}")
        per_type_lines.append(f"| {name} | " + " | ".join(cells) + " |")

    out.append("\n## Số mẫu bị đánh dấu là đạo văn, theo từng loại (trên test)\n")
    out.append("Với loại đạo văn, số càng cao càng tốt (bắt được). Với loại sạch (in nghiêng ở tiêu đề), số càng thấp càng tốt (báo nhầm).\n")
    head = "| Cấu hình | " + " | ".join(types) + " | " + " | ".join(f"{t} (sạch)" for t in neg_types) + " |"
    out.append(head)
    out.append("|" + " --- |" * (len(types) + len(neg_types) + 1))
    out.extend(per_type_lines)
    out.append("\nLưu ý: tập kiểm thử do chương trình tự sinh từ kho nhỏ nên kết quả mang tính minh hoạ; "
               "mẫu 'heavy' chỉ là đổi từ theo từ điển, chưa phải paraphrase ngữ nghĩa.")
    text = "\n".join(out)
    print(text)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/evaluation_results.md").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
