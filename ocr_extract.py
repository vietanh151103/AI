#!/usr/bin/env python3
"""
Trích xuất thông tin tem sản phẩm từ ảnh bằng OCR.

Thông tin cần lấy:
- Mã model (nếu không có thì dùng tên sản phẩm trên tem)
- Số seri (xuất ra dạng viết liền, ngăn cách bởi ", ")
- Năm sản xuất
- Xuất xứ

Ví dụ:
    python ocr_extract.py label1.jpg label2.png --lang vie+eng
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

import pytesseract
from PIL import Image


MODEL_KEYS = [
    "mã model",
    "model",
    "model code",
    "mã sp",
    "mã sản phẩm",
]
SERIAL_KEYS = [
    "serial",
    "s/n",
    "sn",
    "seri",
    "số seri",
    "số series",
]
YEAR_KEYS = [
    "năm sản xuất",
    "năm sx",
    "manufacture year",
    "mfg year",
    "year",
]
ORIGIN_KEYS = [
    "xuất xứ",
    "made in",
    "origin",
    "country of origin",
]
PRODUCT_NAME_KEYS = [
    "tên sản phẩm",
    "product name",
    "product",
    "tên hàng",
]


@dataclass
class ProductInfo:
    product_type: str
    model_or_product_name: str
    serial_numbers: str
    manufacture_year: str
    origin: str
    raw_text: str


def normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line


def pick_value_after_key(line: str, keys: Iterable[str]) -> str | None:
    lower = line.lower()
    for key in keys:
        idx = lower.find(key)
        if idx == -1:
            continue
        value = line[idx + len(key):]
        value = re.sub(r"^[\s:：\-–]+", "", value).strip()
        if value:
            return value
    return None


def extract_serials(text: str) -> list[str]:
    serials = []

    line_pattern = re.compile(
        r"(?:serial|s/n|\bsn\b|seri|số\s*seri|số\s*series)\s*[:：\-–]?\s*([A-Z0-9\-_/]{4,})",
        flags=re.IGNORECASE,
    )
    serials.extend(m.group(1).upper() for m in line_pattern.finditer(text))

    fallback_pattern = re.compile(r"\b[A-Z0-9]{8,}\b")
    for candidate in fallback_pattern.findall(text.upper()):
        if any(ch.isdigit() for ch in candidate):
            serials.append(candidate)

    cleaned = []
    seen = set()
    for s in serials:
        s = re.sub(r"[^A-Z0-9]", "", s)
        if len(s) < 6:
            continue
        if s not in seen:
            seen.add(s)
            cleaned.append(s)
    return cleaned


def extract_year(text: str) -> str:
    year_match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", text)
    if year_match:
        return year_match.group(1)
    return ""


def extract_origin(lines: list[str]) -> str:
    for line in lines:
        value = pick_value_after_key(line, ORIGIN_KEYS)
        if value:
            return value
    for line in lines:
        m = re.search(r"made\s+in\s+([A-Za-z\s]+)", line, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def extract_model_or_name(lines: list[str]) -> str:
    for line in lines:
        value = pick_value_after_key(line, MODEL_KEYS)
        if value:
            return value

    for line in lines:
        value = pick_value_after_key(line, PRODUCT_NAME_KEYS)
        if value:
            return value

    for line in lines:
        low = line.lower()
        if not line:
            continue
        if any(k in low for k in SERIAL_KEYS + YEAR_KEYS + ORIGIN_KEYS):
            continue
        if re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", line):
            continue
        return line

    return ""


def parse_product_block(text: str, index: int) -> ProductInfo:
    lines = [normalize_line(x) for x in text.splitlines()]
    lines = [x for x in lines if x]
    normalized_text = "\n".join(lines)

    model_or_product_name = extract_model_or_name(lines)
    serial_numbers = ", ".join(extract_serials(normalized_text))
    manufacture_year = extract_year(normalized_text)
    origin = extract_origin(lines)

    product_type = model_or_product_name or f"Sản phẩm {index}"

    return ProductInfo(
        product_type=product_type,
        model_or_product_name=model_or_product_name,
        serial_numbers=serial_numbers,
        manufacture_year=manufacture_year,
        origin=origin,
        raw_text=normalized_text,
    )


def split_blocks(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n+", text) if b.strip()]
    if not blocks:
        return [text.strip()] if text.strip() else []
    return blocks


def ocr_text(image_path: Path, lang: str) -> str:
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang=lang)


def process_image(image_path: Path, lang: str) -> list[ProductInfo]:
    raw_text = ocr_text(image_path, lang=lang)
    blocks = split_blocks(raw_text)
    products = [parse_product_block(block, i + 1) for i, block in enumerate(blocks)]
    return products


def print_table(results: list[ProductInfo]) -> None:
    headers = ["Loại sản phẩm", "Model/Tên SP", "Số seri", "Năm SX", "Xuất xứ"]
    rows = [
        [
            r.product_type,
            r.model_or_product_name,
            r.serial_numbers,
            r.manufacture_year,
            r.origin,
        ]
        for r in results
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell or ""))

    def fmt(row: list[str]) -> str:
        return " | ".join((row[i] or "").ljust(widths[i]) for i in range(len(headers)))

    print(fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OCR ảnh tem để lấy mã model/tên SP, số seri, năm sản xuất, xuất xứ."
    )
    parser.add_argument("images", nargs="+", type=Path, help="Đường dẫn ảnh tem sản phẩm")
    parser.add_argument(
        "--lang",
        default="vie+eng",
        help="Ngôn ngữ OCR cho Tesseract (mặc định: vie+eng)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="In kết quả dạng JSON thay vì bảng",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    all_results: list[ProductInfo] = []
    for image in args.images:
        if not image.exists():
            raise FileNotFoundError(f"Không tìm thấy ảnh: {image}")
        all_results.extend(process_image(image, args.lang))

    if args.json:
        print(json.dumps([asdict(x) for x in all_results], ensure_ascii=False, indent=2))
    else:
        print_table(all_results)


if __name__ == "__main__":
    main()
