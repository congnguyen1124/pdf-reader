# LinguaPDF

Ứng dụng desktop Python 3 dành cho việc học tiếng Anh bằng tài liệu PDF trên macOS và Linux. LinguaPDF cho phép tô sáng, đặt ghi chú trực tiếp trên trang, bật/tắt lớp chỉnh sửa, lưu riêng thay đổi để bảo vệ PDF gốc và ôn từ vựng bằng flashcard có lịch nhắc lại.

## Tính năng

- Thư viện bên trái quản lý toàn bộ PDF đã nhập và các bộ từ vựng độc lập.
- Tạo bài học chỉ để theo dõi từ vựng mà không cần PDF.
- Hiển thị tất cả trang PDF liên tục theo chiều dọc, phóng to/thu nhỏ đồng bộ.
- Nhấp hoặc kéo để chọn đúng chữ trong PDF, sau đó tô 4 màu, underline hoặc gạch ngang.
- Giữ `Space` để tạm chuyển sang chế độ kéo trang; thả phím để quay lại chọn chữ.
- Tạo ghi chú trực tiếp trên trang, nhập ngay trong vùng note và kéo phần tiêu đề để di chuyển.
- Nút **Hiện chỉnh sửa** để ẩn/hiện toàn bộ lớp ghi chú.
- Nút **Tự động lưu** để chủ động bật/tắt việc ghi thay đổi xuống đĩa.
- PDF được sao chép vào thư viện nội bộ; chỉnh sửa lưu không phá hủy bằng sidecar JSON.
- Xuất một file `.annotated.pdf` mới có annotation thật, mở được bằng các trình PDF phổ biến.
- Kho từ vựng tách riêng cho từng mục; nhập bằng bảng hai cột hoặc dán từ Excel/Sheets.
- Ôn theo `English → Tiếng Việt`, `Tiếng Việt → English`, hoặc trộn hai chiều.
- Theo dõi số lần ôn, độ chính xác và ngày đến hạn bằng thuật toán spaced repetition.
- Phím tắt: `Ctrl/Cmd+O` nhập PDF, `Ctrl/Cmd+N` tạo bộ từ, `Ctrl/Cmd+S` lưu, `Ctrl/Cmd +/-` zoom; trong flashcard dùng `Space` để lật và `1–4` để đánh giá.

## Cài đặt nhanh

Yêu cầu Python 3.10 trở lên.

### macOS / Linux

```bash
cd /duong/dan/toi/pdf-reader
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m linguapdf
```

Repository đã có sẵn thư mục `.venv`; nếu chuyển dự án sang máy khác, nên xóa và tạo lại môi trường ảo bằng lệnh ở trên vì virtual environment không có tính di động giữa các máy.

## Cách sử dụng

1. Chọn **Nhập PDF** để đưa một bản sao vào thư viện, hoặc **Bộ từ vựng mới** nếu không cần tài liệu PDF.
2. Chọn một mục ở cột trái. Từ vựng và toàn bộ lịch sử ôn luôn thuộc riêng mục đó.
3. Ở chế độ **Chọn chữ**, nhấp một từ hoặc kéo qua nhiều từ. Bảng định dạng xuất hiện để chọn màu tô, underline hay gạch ngang.
4. Giữ `Space` và kéo chuột để di chuyển tài liệu. Khi thả `Space`, con trỏ tự trở lại chế độ chọn chữ.
5. Chọn **Ghi chú**, nhấp lên trang rồi nhập trực tiếp. Kéo thanh “Ghi chú — kéo tại đây” để đặt note vào vị trí khác. Note tự thay đổi kích thước hiển thị khi zoom.
6. Bật **Tự động lưu** để thay đổi được ghi ngay vào sidecar. Khi tắt, thay đổi chỉ ở phiên hiện tại cho đến khi chọn **Lưu thay đổi**.
7. Dùng **Hiện chỉnh sửa** để xem PDF sạch mà không xóa annotation; dùng **Tệp → Xuất PDF đã chỉnh sửa…** để tạo PDF mới.
8. Trong tab **Từ vựng**, chọn **Thêm hàng loạt**. Nhập trực tiếp trong bảng English/Tiếng Việt hoặc dán hai cột từ bảng tính:

   ```text
   remarkable    đáng chú ý
   sustainable   bền vững
   take into account    cân nhắc
   ```

   Khi dán văn bản thuần, hai cột cũng có thể ngăn bằng Tab, `;`, `,` hoặc `|`; nút **Đổi hai cột** xử lý danh sách Việt–Anh.
9. Mở tab **Ôn tập**, chọn chiều hỏi và đánh giá mức nhớ bằng 4 nút.

## Dữ liệu được lưu ở đâu?

- PDF đã nhập, annotation, từ vựng và lịch sử ôn nằm trong thư mục dữ liệu ứng dụng:
  - macOS: `~/Library/Application Support/LinguaPDF/`
  - Linux: `~/.local/share/LinguaPDF/`
- Cài đặt giao diện: kho cấu hình chuẩn của Qt theo từng hệ điều hành.

PDF nguồn không bao giờ bị ghi đè: ứng dụng làm việc trên bản sao trong thư mục `pdfs/`. Chức năng xuất cũng bắt buộc chọn một đường dẫn khác.

## Kiến trúc

```text
src/linguapdf/
├── domain/                 # Mô hình dữ liệu, parser, thuật toán ôn tập
├── services/
│   ├── pdf_service.py      # Mở PDF, sidecar và xuất annotation
│   └── library_service.py  # SQLite cho tài liệu, từ vựng, lịch sử
├── ui/
│   ├── main_window.py      # Điều phối ứng dụng
│   ├── library_panel.py    # Quản lý PDF và bộ từ vựng ở cột trái
│   ├── pdf_viewer.py       # Render liên tục, chọn chữ, note và annotation
│   ├── vocabulary_panel.py # Kho từ vựng và màn hình flashcard
│   ├── bulk_import_dialog.py
│   └── styles.py
└── main.py                 # Điểm khởi chạy
```

Phần domain không phụ thuộc giao diện, services chịu trách nhiệm persistence, còn UI chỉ điều phối hành vi. Cách tách này giúp việc kiểm thử và bổ sung tính năng dễ hơn.

## Kiểm thử

```bash
source .venv/bin/activate
pytest
ruff check src tests
```

Test hiện có bao phủ parser nhập hàng loạt, lịch spaced repetition, dự án PDF/bộ từ độc lập, cách ly từ vựng, sidecar annotation và xuất PDF.

## Ghi chú nền tảng

PySide6 và PyMuPDF đều hỗ trợ macOS/Linux. Nếu Linux báo thiếu plugin đồ họa Qt, cài các package hệ thống tương ứng với distro (thường là `libxcb-cursor0`, `libegl1` và font Noto), rồi chạy lại trong `.venv`.
