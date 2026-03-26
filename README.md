## OCR trích xuất thông tin tem sản phẩm

Chương trình `ocr_extract.py` đọc văn bản từ ảnh và lấy các thông tin:

- Mã model (nếu không có thì lấy tên sản phẩm trên tem)
- Số seri (viết liền và ngăn cách bởi `, `)
- Năm sản xuất
- Xuất xứ

## Cài đặt

```bash
pip install pillow pytesseract
```

Cần cài thêm Tesseract OCR trong hệ điều hành (và language pack `vie`, `eng` nếu dùng tiếng Việt + tiếng Anh).

## Chạy

```bash
python ocr_extract.py tem1.jpg tem2.png --lang vie+eng
```

Hoặc xuất JSON:

```bash
python ocr_extract.py tem1.jpg --json
```
