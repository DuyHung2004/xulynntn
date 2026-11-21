# Hướng dẫn sử dụng

Tài liệu này hướng dẫn cài đặt, dùng giao diện web, thêm dữ liệu, đánh giá hệ thống và dùng thư viện trong code.
Phần giải thích lý thuyết (TF-IDF, n-gram, winnowing, công thức) và mã nguồn từng hàm nằm trong file PDF
`Huong_dan_phat_hien_dao_van_tieng_Viet.pdf` cùng thư mục. Lưu ý PDF dùng kho demo 3 tài liệu để minh hoạ, còn dự án này
có kho 15 tài liệu, nên con số trong PDF khác với kết quả bạn chạy ở đây.

## 1. Cài đặt

Yêu cầu Python 3.9 trở lên.

```bash
cd vn_plagiarism_project
python -m venv .venv                 # tuỳ chọn, nên dùng
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Bộ tách từ: mặc định cài `pyvi`. Nếu muốn dùng `underthesea`, chạy `pip install underthesea`; hệ thống tự ưu tiên underthesea
nếu có. Nếu không có cả hai, hệ thống vẫn chạy nhưng tách theo âm tiết nên kém chính xác hơn.

Độ giống ngữ nghĩa (tuỳ chọn): `pip install sentence-transformers`. Lần đầu bật sẽ tải mô hình `keepitreal/vietnamese-sbert`
(cần internet, vài trăm MB).

Kiểm tra cài đặt đúng chưa:

```bash
python -m unittest discover -s tests     # kỳ vọng: Ran 8 tests ... OK
python demo.py
```

## 2. Giao diện web

```bash
streamlit run app.py
```

Mở địa chỉ hiện ra (thường là http://localhost:8501).

### Tab "Kiểm tra"

1. Dán văn bản vào ô lớn, hoặc tải file `.txt`, hoặc chọn một mẫu ở ô "Nạp văn bản mẫu" (lấy từ tập kiểm thử).
2. Bấm **Kiểm tra**.
3. Đọc kết quả:
   - **Điểm toàn bài** và **câu bị đánh dấu** (tỉ lệ phần trăm), cùng khung kết luận bốn mức màu.
   - Văn bản được hiển thị lại, câu nghi chép tô đỏ; rê chuột vào để xem tên tài liệu nguồn và điểm.
   - Bảng "Tài liệu giống nhất" cho điểm từng độ đo để biết độ đo nào đang cao.
   - Danh sách "Các câu bị đánh dấu": mở từng mục để so câu nghi vấn với câu nguồn.

Thanh bên trái:

- **Ngưỡng đánh dấu câu** (mặc định 0.55). Kéo thấp để bắt cả câu sửa nhẹ nhưng dễ báo nhầm các câu chỉ chung thuật ngữ;
  kéo cao để chỉ bắt câu gần như y hệt.
- **Dùng độ giống ngữ nghĩa**: bật khi đã cài sentence-transformers.

### Tab "Kho tài liệu"

Quản lý các tài liệu gốc, lưu thẳng vào thư mục `data/corpus/`:

- **Thêm bằng cách dán**: nhập tên và nội dung, bấm *Thêm vào kho*.
- **Thêm bằng cách tải file**: chọn một hoặc nhiều file `.txt` (UTF-8), bấm *Lưu các file đã chọn*.
- Bảng liệt kê số từ, số câu từng tài liệu; có ô xem nội dung và ô chọn tài liệu để xoá.

Mỗi lần kho thay đổi, hệ thống tự học lại ở lần kiểm tra kế tiếp.

### Tab "Đánh giá"

Hiển thị `docs/evaluation_results.md`. Cập nhật bằng cách chạy lại `python evaluate.py` (mục 4).

## 3. Thêm dữ liệu

### Thêm tài liệu vào kho gốc

Cách 1: dùng tab "Kho tài liệu". Cách 2: chép file vào `data/corpus/`.

Yêu cầu của file: định dạng `.txt`, mã hoá UTF-8, một tài liệu một file, tên file không dấu cách (dùng gạch dưới).
Tài liệu nên có ít nhất vài câu hoàn chỉnh vì so khớp mức câu bỏ qua câu dưới 3 từ.
Nếu có file Word hoặc PDF, hãy chuyển sang văn bản thuần trước.

### Thêm mẫu cho tập kiểm thử

| Thư mục | Chứa gì | Nhãn |
| --- | --- | --- |
| `data/independent/` | Văn bản tự viết. Tên file bắt đầu bằng `i` là cùng chủ đề với kho, bằng `u` là khác chủ đề | Không đạo văn |
| `data/paraphrase/` | Đoạn diễn đạt lại một tài liệu của kho. **Tên file phải trùng tên file trong `data/corpus/`** | Đạo văn |

Sau khi thêm, tạo lại tập kiểm thử:

```bash
python build_benchmark.py        # ghi data/benchmark/benchmark.csv
```

Script tự sinh thêm các mẫu đạo văn từ kho: chép nguyên văn (`copy`), chép kèm câu tự viết (`copy_mix`), sửa nhẹ (`light`),
đổi nhiều từ (`heavy`), đảo câu (`shuffle`), ghép hai nguồn (`mosaic`), và mẫu sạch ghép từ hai văn bản độc lập (`mixed`).
Từ điển đồng nghĩa dùng cho `light` và `heavy` nằm đầu file `build_benchmark.py`, bạn có thể mở rộng.

Muốn dùng dữ liệu thật thay cho dữ liệu mẫu: thay nội dung `data/corpus/` và `data/independent/`, tự viết hoặc thu thập
các đoạn diễn đạt lại bỏ vào `data/paraphrase/`, rồi chạy lại hai script `build_benchmark.py` và `evaluate.py`.

## 4. Đánh giá hệ thống

```bash
python evaluate.py
```

Script chia mẫu thành dev và test theo từng loại, chọn ngưỡng tốt nhất trên dev, rồi báo cáo Precision, Recall, F1 trên test
cho 5 cấu hình (chỉ TF-IDF; chỉ containment; chỉ winnowing; tổ hợp 3 độ đo; tổ hợp thêm mức câu). Kết quả in ra màn hình
và ghi vào `docs/evaluation_results.md`.

Bảng thứ hai cho biết mỗi cấu hình bắt được bao nhiêu mẫu của từng loại đạo văn, và báo nhầm bao nhiêu mẫu sạch.
Đây là bảng nên dùng trong báo cáo, vì nó chỉ ra độ đo nào mạnh ở dạng đạo văn nào.

Cách đọc: containment và winnowing mạnh ở chép nguyên văn nhưng gần như không bắt được diễn đạt lại; TF-IDF bắt được
diễn đạt lại nhờ từ khoá chung nhưng có thể báo nhầm khi kho có nhiều tài liệu cùng chủ đề (điều này chưa được đo trong tập kiểm thử nhỏ này).

## 5. Dùng bằng dòng lệnh

```bash
python check.py bai_nop.txt
python check.py bai_nop.txt --corpus data/corpus --threshold 0.5
python check.py bai_nop.txt --semantic          # cần sentence-transformers
```

## 6. Dùng thư viện trong code

```python
from vn_plagiarism import PlagiarismDetector, load_corpus_dir, print_report

corpus = load_corpus_dir("data/corpus")                 # dict {tên: nội dung}
det = PlagiarismDetector(sentence_threshold=0.55).fit(corpus)

report = det.check(open("bai_nop.txt", encoding="utf-8").read())
print_report(report)

print(report.overall_score, report.verdict)
for m in report.matches:
    print(f"{m.score:.2f}", m.suspect_sentence, "<-", m.source_id)
```

Tham số của `PlagiarismDetector`:

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `sentence_threshold` | 0.55 | Ngưỡng đánh dấu một câu |
| `use_semantic` | False | Bật Sentence-BERT |
| `semantic_model` | keepitreal/vietnamese-sbert | Mô hình embedding |
| `weights` | tfidf 0.25, containment 0.35, winnowing 0.25, semantic 0.15 | Trọng số điểm tổng hợp |
| `use_sentence_level` | True | Tắt để chỉ dùng điểm mức tài liệu |

## 7. Xử lý sự cố

| Triệu chứng | Cách xử lý |
| --- | --- |
| `ModuleNotFoundError: streamlit` | Chạy `pip install -r requirements.txt` trong đúng môi trường Python |
| Cảnh báo `SyntaxWarning` của pyvi | Vô hại, do thư viện pyvi; có thể bỏ qua |
| Tiếng Việt hiển thị lỗi khi đọc file | Lưu file ở dạng UTF-8 |
| "Kho tài liệu đang trống" | Thêm ít nhất một file `.txt` vào `data/corpus/` |
| Câu tự viết bị đánh dấu nhầm | Tăng ngưỡng đánh dấu câu (0.6 đến 0.7), hoặc câu đó chỉ chung thuật ngữ chuyên ngành với nguồn |
| Bài sửa nhẹ không bị bắt | Giảm ngưỡng (0.4 đến 0.5); bật so khớp ngữ nghĩa nếu bài diễn đạt lại hoàn toàn |
| Cổng 8501 đã bị dùng | `streamlit run app.py --server.port 8600` |
| Bật ngữ nghĩa báo lỗi tải mô hình | Cần internet lần đầu; kiểm tra đã cài sentence-transformers |

## 8. Gợi ý cho báo cáo đồ án

1. Mô tả bài toán và đặc thù tiếng Việt (tách từ, Unicode): xem PDF, phần 1 và 4.
2. Trình bày từng độ đo kèm công thức: PDF, phần 5.
3. Báo cáo thí nghiệm ablation bằng bảng của `evaluate.py`, phân tích theo từng loại mẫu.
4. Nêu thẳng hạn chế (README, mục Hạn chế), nhất là việc tập kiểm thử tự sinh và kho nhỏ.
5. Hướng phát triển: PhoBERT, học trọng số bằng hồi quy logistic, loại trừ câu trích dẫn, chỉ mục ngược cho kho lớn.
