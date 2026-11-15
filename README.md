# Canvas 2D Script-Driven Cloud Renderer (GitHub Actions)

Bộ công cụ giúp bạn biến một **kịch bản đầu vào (`script.json`)** thành video hoạt hình 2D 1080p @ 60FPS hoàn chỉnh (tự động đọc giọng `vi-VN-NamMinhNeural` qua `edge-tts`, tự động đo độ dài câu thoại để căn khớp chuyển động từng cảnh và chia 4 máy chủ render song song trên GitHub Actions).

## 1. Cấu trúc gói
- `index.html`: Engine vẽ Canvas 2D theo kịch bản (hỗ trợ mở trực tiếp trên trình duyệt để sửa và xem trước kịch bản thông qua nút **Input Script (JSON)**, đồng thời cung cấp hook `window.loadScript()` & `window.renderFrameAt()` cho Cloud).
- `script.json`: File kịch bản đầu vào. Bạn không cần tự tính giây (`s`, `e`) — chỉ cần ghi lời thoại `text`, bối cảnh `env` và danh sách `actors`, script Python sẽ tự đo độ dài giọng đọc `edge-tts` để khớp thời gian chính xác.
- `scripts/build_timeline_and_tts.py`: Tự động sinh giọng đọc cho từng cảnh và xuất `out/compiled_timeline.json` + `out/voiceover.mp3`.
- `scripts/render_chunk.mjs`: Chạy Headless Chromium (Playwright) truyền thẳng luồng frame PNG sang `ffmpeg` (`image2pipe`).
- `.github/workflows/render-from-script.yml`: Workflow tự động chạy khi bạn sửa `script.json` hoặc khi bấm **Run workflow** và dán JSON kịch bản trực tiếp trên web GitHub.

## 2. Cách sử dụng trên GitHub Cloud
1. Tạo một repo **Public** mới trên GitHub và đẩy toàn bộ code này lên:
   ```bash
   git init
   git add .
   git commit -m "Init 2D Script Cloud Renderer"
   git branch -M main
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```
2. Mỗi khi muốn làm video mới, bạn chỉ cần:
   - **Cách 1**: Mở `index.html` trên máy, bấm **Input Script (JSON)** để soạn/xem trước kịch bản, bấm **Copy JSON** rồi dán đè vào `script.json` và `git push`.
   - **Cách 2**: Vào tab **Actions** trên GitHub -> chọn **Render 2D Video From Input Script (Cloud Matrix)** -> bấm **Run workflow** và dán thẳng JSON vào ô `custom_script_json`.
3. Sau khoảng 1,5 – 2 phút, tải file `final_2d_animation_60fps.mp4` trong mục **Artifacts**.
