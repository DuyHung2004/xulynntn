# Kết quả đánh giá

Kho: 15 tài liệu. Dev: 75 mẫu, test: 66 mẫu.

| Cấu hình | Ngưỡng (chọn trên dev) | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| A. Chỉ TF-IDF cosine | 0.35 | 1.00 | 0.98 | 0.99 |
| B. Chỉ containment 3-gram | 0.10 | 1.00 | 0.86 | 0.92 |
| C. Chỉ winnowing | 0.10 | 1.00 | 0.86 | 0.92 |
| D. Tổ hợp 3 độ đo (không mức câu) | 0.10 | 0.98 | 0.98 | 0.98 |
| E. Tổ hợp 3 độ đo + mức câu (mặc định) | 0.15 | 0.98 | 0.96 | 0.97 |

## Số mẫu bị đánh dấu là đạo văn, theo từng loại (trên test)

Với loại đạo văn, số càng cao càng tốt (bắt được). Với loại sạch (in nghiêng ở tiêu đề), số càng thấp càng tốt (báo nhầm).

| Cấu hình | copy | copy_mix | heavy | light | mosaic | paraphrase | shuffle | independent (sạch) | mixed (sạch) | unrelated (sạch) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Chỉ TF-IDF cosine | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 6/7 | 7/7 | 0/7 | 0/7 | 0/3 |
| B. Chỉ containment 3-gram | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0/7 | 7/7 | 0/7 | 0/7 | 0/3 |
| C. Chỉ winnowing | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0/7 | 7/7 | 0/7 | 0/7 | 0/3 |
| D. Tổ hợp 3 độ đo (không mức câu) | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 6/7 | 7/7 | 1/7 | 0/7 | 0/3 |
| E. Tổ hợp 3 độ đo + mức câu (mặc định) | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 5/7 | 7/7 | 1/7 | 0/7 | 0/3 |

Lưu ý: tập kiểm thử do chương trình tự sinh từ kho nhỏ nên kết quả mang tính minh hoạ; mẫu 'heavy' chỉ là đổi từ theo từ điển, chưa phải paraphrase ngữ nghĩa.
