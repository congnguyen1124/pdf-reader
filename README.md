# LinguaPDF

Ứng dụng desktop Python 3 dành cho việc học tiếng Anh bằng tài liệu PDF trên macOS và Linux. LinguaPDF cho phép tô sáng, đặt ghi chú trực tiếp trên trang, bật/tắt lớp chỉnh sửa, lưu riêng thay đổi để bảo vệ PDF gốc và ôn từ vựng bằng flashcard có lịch nhắc lại.

## Tính năng

- Thư viện bên trái là cây Explorer gọn theo phong cách VS Code: folder lồng nhau, hàng file một dòng, thao tác bằng icon, tìm kiếm nhanh và kéo-thả workspace giữa các folder.
- Workspace mới được đặt tên `snake_case`, tự tránh trùng tên và có kho từ vựng riêng.
- Workspace có thể bắt đầu không cần PDF, sau đó gắn PDF có sẵn hoặc nhập văn bản để sinh PDF A4 nhiều trang.
- PDF tạo từ văn bản giữ Unicode tiếng Việt, text có thể chọn và có số trang tự động.
- Hiển thị tất cả trang PDF liên tục theo chiều dọc, phóng to/thu nhỏ đồng bộ.
- Tìm chữ trên toàn bộ PDF bằng `Cmd+F` (macOS) hoặc `Ctrl+F` (Linux), tô rõ mọi kết quả và dùng Enter/Shift+Enter để nhảy tới kết quả kế/ trước như trong IDE.
- Pinch bằng hai ngón trên trackpad để zoom; vẫn hỗ trợ `Ctrl/Cmd +/-` và `Ctrl/Cmd + 0`.
- Hai icon đầu topbar thu gọn/mở lại thư viện trái và bảng từ vựng phải để tối đa không gian đọc.
- Con trỏ chỉ đổi sang dạng chọn chữ khi nằm đúng trên text trong PDF.
- Double-click chọn một từ; kéo chuột chọn nhiều dòng theo đúng thứ tự đọc với lớp chọn màu xanh tạm thời.
- Popup vùng chọn là một hàng icon: 4 ô màu, underline, gạch ngang và thêm nhanh từ vựng.
- Click ra ngoài popup sẽ đóng thanh công cụ và xóa ngay lớp bôi xanh tạm thời.
- Thêm nhanh tự lấy phần tiếng Anh đã chọn và chỉ yêu cầu nhập nghĩa tiếng Việt.
- Giữ `Space` để tạm chuyển sang chế độ kéo trang; thả phím để quay lại chọn chữ.
- Tạo textbox ghi chú trong suốt trực tiếp trên trang; khung mặc định gọn một dòng và tự co/nở sát nội dung, có tay nắm kéo/resize cùng thanh nổi để đổi màu chữ, tăng/giảm cỡ chữ hoặc xóa.
- Nút **Hiện chỉnh sửa** để ẩn/hiện toàn bộ lớp ghi chú.
- Nút **Tự động lưu** để chủ động bật/tắt việc ghi thay đổi xuống đĩa.
- PDF được sao chép vào thư viện nội bộ; chỉnh sửa lưu không phá hủy bằng sidecar JSON.
- Xuất một file `.annotated.pdf` mới có annotation thật, mở được bằng các trình PDF phổ biến.
- Kho từ vựng tách riêng cho từng mục; nhập bằng bảng hai cột hoặc dán từ Excel/Sheets.
- Màn nhập hàng loạt có bảng English/Tiếng Việt rộng, trạng thái kiểm tra dữ liệu trực tiếp, dán clipboard, thêm hàng và đổi cột.
- Ôn theo `English → Tiếng Việt`, `Tiếng Việt → English`, hoặc trộn hai chiều.
- Có thể ôn thẻ đến hạn hoặc toàn bộ thẻ; thẻ đánh dấu **Again/Học lại** tự quay lại cuối hàng đợi cho đến khi nhớ đúng, và mỗi phiên có thể khởi động lại từ đầu.
- Theo dõi số lần ôn, độ chính xác và ngày đến hạn bằng thuật toán spaced repetition.
- Mọi nút trên topbar đều có phím tắt và hiện phím đó trong tooltip khi hover.
- Chuyển trực tiếp toàn bộ ứng dụng giữa English/Tiếng Việt; mặc định là English.
- Theme sáng/tối được áp dụng ngay và ghi nhớ cho lần mở sau.
- Phím tắt chính: `Ctrl/Cmd+O` nhập PDF, `Ctrl/Cmd+N` tạo bộ từ, `Ctrl/Cmd+S` lưu, `Ctrl/Cmd+F` tìm trong PDF, `Ctrl/Cmd +/-` zoom, `Ctrl/Cmd+0` vừa chiều rộng, `Ctrl/Cmd+1/2` chọn chữ/ghi chú, `Ctrl/Cmd+Shift+L/F` ẩn hiện hai panel.

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

1. Dùng nút **+ Folder** để tạo cây thư mục. Chọn một folder trước khi tạo/import để workspace mới nằm trong folder đó; kéo workspace sang folder khác để sắp xếp lại.
2. Chọn **Import PDF** để đưa một bản sao vào thư viện, hoặc **+ File** để tạo workspace trống. Tên mới được tự chuẩn hóa như `airport_vocabulary`.
3. Trong workspace trống, chọn **Choose PDF** hoặc **Create PDF from text** ngay giữa vùng đọc. Cách thứ hai tự dàn nội dung thành PDF A4 nhiều trang.
4. Dùng ô tìm kiếm trên cây thư viện để lọc cả folder lẫn workspace. Từ vựng và lịch sử ôn luôn thuộc riêng từng workspace.
5. Chọn **Settings → Language** để đổi English/Tiếng Việt và **Settings → Theme** để đổi sáng/tối.
6. Có thể bấm hai icon panel ở đầu topbar để dành toàn bộ chiều rộng cho PDF. Pinch hai ngón trên trackpad để zoom tự nhiên.
7. Ở chế độ **Chọn chữ**, đưa chuột lên text để thấy con trỏ đổi dạng. Double-click để chọn một từ hoặc kéo qua nhiều từ/dòng. Dòng đầu được chọn đến hết bên phải, các dòng giữa được chọn toàn bộ và dòng cuối dừng tại từ dưới con trỏ. Vùng xanh biến mất nếu đóng popup mà không chọn thao tác.
8. Trong thanh icon của vùng chọn, chọn màu tô, underline, gạch ngang hoặc **Thêm nhanh vào từ vựng**. Thêm nhanh tự điền tiếng Anh và chỉ mở một ô nhập nghĩa tiếng Việt.
9. Giữ `Space` và kéo chuột để di chuyển tài liệu. Khi thả `Space`, con trỏ tự trở lại chế độ chọn chữ.
10. Nhấn `Cmd/Ctrl+F` để mở thanh tìm kiếm PDF. Enter đi tới kết quả tiếp theo, Shift+Enter quay lại và Esc đóng thanh tìm kiếm.
11. Chọn **Ghi chú**, nhấp lên trang rồi nhập trực tiếp. Khi note được chọn, kéo tay nắm xanh bên trái để di chuyển, tay nắm tròn bên phải để đổi độ rộng, hoặc dùng thanh nổi để đổi màu/cỡ chữ. Note tự thay đổi kích thước hiển thị khi zoom.
12. Bật **Tự động lưu** để thay đổi được ghi ngay vào sidecar. Khi tắt, thay đổi chỉ ở phiên hiện tại cho đến khi chọn **Lưu thay đổi**.
13. Dùng **Hiện chỉnh sửa** để xem PDF sạch mà không xóa annotation; dùng **Tệp → Xuất PDF đã chỉnh sửa…** để tạo PDF mới.
14. Trong tab **Từ vựng**, chọn **Thêm hàng loạt**. Nhập trực tiếp trong bảng English/Tiếng Việt hoặc dán hai cột từ bảng tính:

   ```text
   remarkable    đáng chú ý
   sustainable   bền vững
   take into account    cân nhắc
   ```

   Khi dán văn bản thuần, hai cột cũng có thể ngăn bằng Tab, `;`, `,` hoặc `|`; nút **Đổi hai cột** xử lý danh sách Việt–Anh.
15. Mở tab **Ôn tập**, chọn chiều hỏi, chọn **Thẻ đến hạn** hoặc **Tất cả thẻ**, rồi đánh giá mức nhớ bằng 4 nút. **Học lại/Again** lặp lại thẻ trong cùng phiên; dùng **Ôn lại từ đầu** bất kỳ lúc nào hoặc ôn lại toàn bộ sau khi hoàn tất.

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
│   ├── text_pdf_service.py # Sinh PDF nhiều trang từ văn bản Unicode
│   └── library_service.py  # SQLite cho folder, workspace, từ vựng, lịch sử
├── ui/
│   ├── main_window.py      # Điều phối ứng dụng
│   ├── library_panel.py    # Cây folder/workspace, tìm kiếm và kéo-thả
│   ├── pdf_viewer.py       # Render liên tục, chọn chữ, note và annotation
│   ├── pdf_search_bar.py    # Tìm kiếm, điều hướng và đếm kết quả trong PDF
│   ├── vocabulary_panel.py # Kho từ vựng và màn hình flashcard
│   ├── workspace_page.py   # Màn hình workspace chưa có PDF
│   ├── text_pdf_dialog.py  # Nhập nội dung để tạo PDF
│   ├── i18n.py             # Chuỗi English/Tiếng Việt
│   ├── bulk_import_dialog.py
│   ├── quick_vocabulary_dialog.py
│   ├── selection_toolbar.py # Thanh icon cho vùng chữ được chọn
│   ├── icons.py             # Icon giao diện được vẽ theo vector
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

Test hiện có bao phủ parser nhập hàng loạt, tìm chữ nhiều trang, vòng lặp thẻ sai, UI nhập thẻ, lịch spaced repetition, cây folder/workspace, chuẩn hóa `snake_case`, PDF Unicode từ văn bản, sidecar annotation và xuất PDF.

## Ghi chú nền tảng

PySide6 và PyMuPDF đều hỗ trợ macOS/Linux. Nếu Linux báo thiếu plugin đồ họa Qt, cài các package hệ thống tương ứng với distro (thường là `libxcb-cursor0`, `libegl1` và font Noto), rồi chạy lại trong `.venv`.
