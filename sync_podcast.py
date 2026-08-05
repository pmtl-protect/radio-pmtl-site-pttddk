import feedparser
import requests
import json
import os
from huggingface_hub import HfApi

# Cấu hình
RSS_URL = "https://www.spreaker.com/show/6422707/episodes/feed"
HF_REPO = "pmtlprotect123/radio-pmtl-site-pttddk"
HF_TOKEN = os.getenv("HF_TOKEN")
JSON_FILE = "playlist.json"

api = HfApi()

def sync():
    playlist_modified = False # Biến theo dõi xem có link cũ nào được sửa không

    # 1. Đọc playlist hiện tại
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                playlist = json.load(f)
                
                # --- TỰ ĐỘNG QUÉT VÀ SỬA LINK CŨ ---
                for item in playlist:
                    if item.get("url") and item["url"].startswith("https://huggingface.co"):
                        item["url"] = item["url"].replace("https://huggingface.co", "/huggingface-audio")
                        playlist_modified = True # Đánh dấu là file có sự thay đổi cần lưu lại
                # -----------------------------------
            except:
                playlist = []
    else:
        playlist = []
    
    existing_urls = [item.get('original_url') for item in playlist]

    # 2. Lấy dữ liệu từ RSS Spreaker
    feed = feedparser.parse(RSS_URL)
    new_items = []

    # Duyệt từ cũ đến mới để bài mới nhất nằm trên cùng sau khi append
    for entry in feed.entries:
        original_url = entry.enclosures[0].href
        
        if original_url not in existing_urls:
            title = entry.title
            
            # Chỉ lấy phần ID số ở cuối URL để làm tên file
            raw_id = entry.id.split('/')[-1] 
            file_name = f"{raw_id}.mp3"
            
            print(f"Đang xử lý tập mới: {title}")

            # 3. Tải file từ Spreaker
            try:
                response = requests.get(original_url, timeout=30)
                with open(file_name, "wb") as f:
                    f.write(response.content)

                # 4. Đẩy lên Hugging Face
                api.upload_file(
                    path_or_fileobj=file_name,
                    path_in_repo=f"audio/{file_name}",
                    repo_id=HF_REPO,
                    repo_type="dataset",
                    token=HF_TOKEN
                )

                # 5. Tạo link Raw qua Netlify Proxy
                hf_raw_url = f"/huggingface-audio/datasets/{HF_REPO}/resolve/main/audio/{file_name}"
                
                # Lấy duration nếu có
                duration = ""
                if hasattr(entry, 'itunes_duration'):
                    duration = entry.itunes_duration

                new_items.append({
                    "title": title,
                    "url": hf_raw_url,
                    "original_url": original_url,
                    "duration": duration
                })
                
                # Xóa file tạm
                if os.path.exists(file_name):
                    os.remove(file_name)
            except Exception as e:
                print(f"Lỗi khi xử lý bài {title}: {e}")

    # 6. LƯU FILE: Lưu lại nếu có bài mới HOẶC nếu vừa sửa link cũ thành công
    if new_items or playlist_modified:
        updated_playlist = new_items + playlist
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_playlist, f, ensure_ascii=False, indent=2)
        return True
    
    return False

if __name__ == "__main__":
    if sync():
        print("Đồng bộ hoàn tất (Đã cập nhật bài mới hoặc sửa xong link cũ)!")
    else:
        print("Không có bài mới để cập nhật, và các link cũ đều đã chuẩn xác.")
