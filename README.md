# Hệ thống phát hiện đạo văn tiếng Việt

Đồ án môn Xử lý ngôn ngữ tự nhiên. So một văn bản nghi vấn với kho tài liệu gốc, cho điểm tương đồng,
chỉ ra từng câu nghi chép và nguồn của nó. Có giao diện web, dòng lệnh, bộ dữ liệu và script đánh giá.

## Chạy nhanh (3 bước)

```bash
pip install -r requirements.txt       # Python 3.9 trở lên
streamlit run app.py                  # giao diện web, mở http://localhost:8501
python check.py bai_nop.txt           # hoặc kiểm tra bằng dòng lệnh
```

Windows: bấm đúp `run_app.bat`. Linux, macOS: `./run_app.sh`.

## Cấu trúc thư mục

```
vn_plagiarism_project/
├── vn_plagiarism.py        Thư viện chính: tiền xử lý, các độ đo, lớp PlagiarismDetector
├── app.py                  Giao diện web Streamlit (3 tab: Kiểm tra, Kho tài liệu, Đánh giá)
├── check.py                Kiểm tra một file .txt bằng dòng lệnh
├── demo.py                 Chạy thử 4 văn bản mẫu
├── build_benchmark.py      Sinh tập kiểm thử có nhãn từ kho tài liệu
├── evaluate.py             Đánh giá Precision/Recall/F1 và so sánh các cấu hình (ablation)
├── requirements.txt
├── tests/test_basic.py     8 kiểm thử đơn vị
├── data/
│   ├── corpus/             15 tài liệu gốc (kho để so sánh)
│   ├── independent/        21 văn bản tự viết, không đạo văn (15 cùng chủ đề, 6 khác chủ đề)
│   ├── paraphrase/         15 đoạn diễn đạt lại viết tay từ kho (đạo văn qua diễn đạt lại)
│   └── benchmark/benchmark.csv   141 mẫu có nhãn (105 đạo văn, 36 không)
└── docs/
    ├── HUONG_DAN_SU_DUNG.md                        Hướng dẫn dùng giao diện, dữ liệu, đánh giá
    ├── Huong_dan_phat_hien_dao_van_tieng_Viet.pdf  Giải thích chi tiết lý thuyết và mã nguồn (16 trang)
    └── evaluation_results.md                       Kết quả đánh giá mới nhất
```

## Hệ thống hoạt động thế nào

1. **Tiền xử lý**: chuẩn hoá Unicode NFC, chữ thường, bỏ dấu câu, tách từ (pyvi hoặc underthesea), bỏ stopword, tách câu.
2. **Bốn độ đo**: TF-IDF cosine, containment 3-gram (kèm Jaccard), winnowing (fingerprint như MOSS),
   và (tuỳ chọn) độ giống ngữ nghĩa bằng Sentence-BERT.
3. **So khớp mức câu**: mỗi câu nghi vấn được so với mọi câu trong kho bằng TF-IDF từ đơn và bigram.
4. **Điểm toàn bài** = giá trị lớn hơn giữa điểm tài liệu giống nhất và tỉ lệ câu bị đánh dấu.
   Mức kết luận: từ 0.7 đạo văn cao, 0.4 nghi vấn, 0.2 trùng lặp thấp, dưới đó là không phát hiện.

## Kết quả đánh giá (trên 66 mẫu test, ngưỡng chọn trên dev)

| Cấu hình | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Chỉ TF-IDF cosine | 1.00 | 0.98 | 0.99 |
| Chỉ containment 3-gram | 1.00 | 0.86 | 0.92 |
| Chỉ winnowing | 1.00 | 0.86 | 0.92 |
| Tổ hợp 3 độ đo | 0.98 | 0.98 | 0.98 |
| Tổ hợp 3 độ đo + mức câu (mặc định) | 0.98 | 0.96 | 0.97 |

Cách đọc kết quả cho đúng:

- Containment và winnowing bắt **0/7** mẫu diễn đạt lại, vì chúng dựa trên cụm từ liền nhau. TF-IDF bắt được
  phần lớn vì các bài diễn đạt lại vẫn giữ từ khoá chủ đề.
- Tập kiểm thử do chương trình tự sinh từ kho **chỉ 15 tài liệu**, nên TF-IDF dễ đạt điểm cao. Với kho lớn và
  nhiều tài liệu cùng chủ đề, TF-IDF có thể báo nhầm nhiều hơn (chưa được kiểm chứng ở đây). Đây là kết quả minh hoạ, không phải đo độ chính xác ngoài đời thực.
- Mẫu `heavy` chỉ đổi từ theo từ điển, không phải paraphrase ngữ nghĩa thật. Mẫu `paraphrase` (viết tay) mới là thử thách thật.
- Chưa chạy chế độ Sentence-BERT trong môi trường này (cần tải mô hình), nên khả năng bắt diễn đạt lại của nó chưa được kiểm chứng.

Chi tiết từng loại mẫu: xem `docs/evaluation_results.md`. Chạy lại: `python build_benchmark.py && python evaluate.py`.

## Hạn chế đã biết

- Ngưỡng và trọng số đặt theo thực nghiệm trên dữ liệu nhỏ, cần chọn lại khi dùng kho thật.
- Tách câu bằng regex đơn giản, sai với viết tắt có dấu chấm (TP.HCM, PGS.TS.).
- Chưa phân biệt trích dẫn đúng quy cách với sao chép.
- Chỉ so với kho được nạp, không tìm trên internet. Chưa xử lý đạo văn qua dịch.
- Kết quả chỉ mang tính hỗ trợ; người đọc đưa ra kết luận cuối cùng.

## Dữ liệu

Toàn bộ văn bản trong `data/` do tác giả đồ án soạn lại bằng lời riêng cho mục đích học tập (không sao chép từ báo hay sách).
Bạn có thể thay `data/corpus/` bằng tài liệu thật (mỗi tài liệu một file `.txt` UTF-8) ngay trên giao diện web hoặc bằng cách chép file vào thư mục.
