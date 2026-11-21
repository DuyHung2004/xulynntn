"""
Sinh tập kiểm thử có nhãn (data/benchmark/benchmark.csv) từ kho tài liệu gốc.

Nhãn 1 (đạo văn), được sinh nhân tạo từ chính kho tài liệu:
  copy     : chép nguyên văn 3-4 câu liên tiếp
  copy_mix : chép 2 câu rồi thêm câu mở đầu và kết luận tự viết
  light    : chép rồi đổi một số từ (từ điển đồng nghĩa nhỏ), bỏ vài từ nối
  heavy    : chép rồi đổi gần hết các từ có trong từ điển và đảo vài cụm
  shuffle  : chép nguyên văn nhưng đảo thứ tự câu
  paraphrase : diễn đạt lại bằng tay (data/paraphrase/*.txt): đổi gần hết từ ngữ, giữ ý
  mosaic   : ghép 2 câu từ tài liệu A, 2 câu từ tài liệu B, xen câu tự viết

Nhãn 0 (không đạo văn):
  independent : văn bản tự viết cùng chủ đề (data/independent/i*.txt)
  unrelated   : văn bản khác chủ đề (data/independent/u*.txt)
  mixed       : ghép 2 văn bản độc lập

Lưu ý: các mẫu "heavy" chỉ đổi từ vựng theo từ điển nên vẫn là diễn đạt lại
ở mức từ ngữ, KHÔNG phải paraphrase ngữ nghĩa thật sự.

Chạy:  python build_benchmark.py
"""
import csv
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).parent / "data"
random.seed(42)

# Từ điển thay thế (cụm gốc -> cụm thay)
SYN_LIGHT = {
    "quan trọng": "thiết yếu", "giúp": "hỗ trợ", "cho phép": "giúp", "thường": "hay",
    "nhiều": "rất nhiều", "rất": "vô cùng", "lớn": "to", "nhanh": "mau",
    "hiện nay": "ngày nay", "tuy nhiên": "nhưng", "bao gồm": "gồm có",
    "phổ biến": "thông dụng", "tăng nhanh": "tăng mạnh", "khoảng": "chừng",
    "ngày nay": "hiện nay", "vấn đề": "bài toán", "mục tiêu": "đích đến",
}
SYN_HEAVY = {
    **SYN_LIGHT,
    "lĩnh vực": "mảng", "hệ thống": "cơ chế", "dữ liệu": "số liệu",
    "tập trung vào": "chú trọng", "xây dựng": "phát triển", "khả năng": "năng lực",
    "thực hiện": "tiến hành", "những": "các", "sử dụng": "dùng",
    "kết quả": "thành tích", "phát triển": "mở rộng", "giảm": "hạ",
    "tăng": "gia tăng", "nguy cơ": "rủi ro", "người dùng": "người sử dụng",
    "doanh nghiệp": "công ty", "thế giới": "toàn cầu", "gia đình": "mái ấm",
    "nổi tiếng": "được biết đến", "cần": "phải", "giải pháp": "phương án",
    "chuyên gia": "nhà nghiên cứu", "người học": "học viên", "đặt ra": "nêu ra",
}
DROP = ["và", "cũng", "rất", "thường", "đã"]

OWN_OPEN = [
    "Trong bài viết này, tôi muốn trình bày một số ý kiến của mình về chủ đề trên.",
    "Đây là một đề tài mà nhiều bạn sinh viên quan tâm trong thời gian gần đây.",
    "Để bắt đầu, chúng ta hãy cùng điểm qua những kiến thức nền tảng cần thiết.",
]
OWN_MID = [
    "Theo quan sát của riêng tôi, vấn đề này còn nhiều điều đáng bàn.",
    "Tôi cho rằng mỗi người nên tự tìm hiểu thêm để có cái nhìn đầy đủ.",
    "Điều này làm tôi nhớ lại một buổi thảo luận nhóm ở lớp học kỳ trước.",
]
OWN_END = [
    "Tóm lại, đây là chủ đề thú vị và còn rất nhiều hướng để nghiên cứu tiếp.",
    "Hy vọng bài viết này mang lại cho bạn đọc vài gợi ý hữu ích.",
    "Em xin chân thành cảm ơn thầy cô và các bạn đã theo dõi.",
]


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]


def replace_words(text, table, p=1.0):
    for src in sorted(table, key=len, reverse=True):
        def sub(m, dst=table[src]):
            if random.random() > p:
                return m.group(0)
            return dst.capitalize() if m.group(0)[0].isupper() else dst
        text = re.sub(r"\b" + re.escape(src) + r"\b", sub, text, flags=re.IGNORECASE)
    return text


def drop_words(text, words, p=0.5):
    for w in words:
        text = re.sub(r"\s\b" + w + r"\b", lambda m: "" if random.random() < p else m.group(0), text)
    return text


def main():
    corpus = {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted((ROOT / "corpus").glob("*.txt"))}
    ids = list(corpus)
    rows = []

    def add(kind, label, text, source):
        rows.append({"id": f"{kind}_{len(rows):03d}", "label": label, "type": kind,
                     "source": source, "text": " ".join(text.split())})

    for did in ids:
        sents = sentences(corpus[did])
        n = len(sents)
        # copy
        k = random.choice([3, 4])
        start = random.randint(0, max(0, n - k))
        add("copy", 1, " ".join(sents[start:start + k]), did)
        # copy_mix
        start = random.randint(0, max(0, n - 2))
        add("copy_mix", 1, " ".join([random.choice(OWN_OPEN)] + sents[start:start + 2] + [random.choice(OWN_END)]), did)
        # light
        base = " ".join(sents[: min(4, n)])
        add("light", 1, drop_words(replace_words(base, SYN_LIGHT, 0.7), DROP, 0.4), did)
        # heavy
        base = " ".join(sents[: min(4, n)])
        add("heavy", 1, drop_words(replace_words(base, SYN_HEAVY, 1.0), DROP, 0.7), did)
        # shuffle
        sub = sents[: min(4, n)]
        add("shuffle", 1, " ".join(reversed(sub)), did)
        # mosaic
        other = random.choice([x for x in ids if x != did])
        so = sentences(corpus[other])
        a = random.sample(sents, 2)
        b = random.sample(so, 2)
        parts = [random.choice(OWN_OPEN), a[0], b[0], random.choice(OWN_MID), a[1], b[1], random.choice(OWN_END)]
        add("mosaic", 1, " ".join(parts), f"{did}+{other}")

    for f in sorted((ROOT / "paraphrase").glob("*.txt")):
        add("paraphrase", 1, f.read_text(encoding="utf-8"), f.stem)

    indep = {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted((ROOT / "independent").glob("*.txt"))}
    for name, text in indep.items():
        add("independent" if name.startswith("i") else "unrelated", 0, text, name)
    names = list(indep)
    for _ in range(15):
        a, b = random.sample(names, 2)
        add("mixed", 0, indep[a] + " " + indep[b], f"{a}+{b}")

    random.shuffle(rows)
    out = ROOT / "benchmark" / "benchmark.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "label", "type", "source", "text"])
        w.writeheader()
        w.writerows(rows)
    pos = sum(r["label"] for r in rows)
    print(f"Đã ghi {len(rows)} mẫu ({pos} đạo văn, {len(rows) - pos} không) -> {out}")


if __name__ == "__main__":
    main()
