import feedparser
import requests
import json
import os
from huggingface_hub import HfApi

# Cấu hình
RSS_URL = "https://www.spreaker.com/show/6422189/episodes/feed"
HF_REPO = "patonline85/radio-pmtl-site" # Mình đã cập nhật dựa trên log của bạn
HF_TOKEN = os.getenv("HF_TOKEN")
JSON_FILE = "playlist.json"

api = HfApi()

def sync():
    # 1. Đọc playlist hiện tại
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                playlist = json.load(f)
            except:
                playlist = []
    else:
        playlist = []
    
    existing_urls = [item.get('original_url') for item in playlist]

    # 2. Lấy dữ liệu từ RSS Spreaker
    feed = feedparser.parse(RSS_URL)
    new_items = []

    # Duyệt từ cũ đến mới để bài mới nhất nằm trên cùng sau khi append
    for entry in reversed(feed.entries):
        original_url = entry.enclosures[0].href
        
        if original_url not in existing_urls:
            title = entry.title
            
            # SỬA LỖI TẠI ĐÂY: Chỉ lấy phần ID số ở cuối URL để làm tên file
            # Ví dụ: từ 'https://.../63010910' lấy ra '63010910'
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

                # 5. Tạo link Raw từ Hugging Face
                hf_raw_url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/audio/{file_name}"
                
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

    if new_items:
        # Đưa các bài mới lên đầu danh sách
        updated_playlist = new_items + playlist
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_playlist, f, ensure_ascii=False, indent=2)
        return True
    return False

if __name__ == "__main__":
    if sync():
        print("Đồng bộ hoàn tất!")
    else:
        print("Không có bài mới để cập nhật.")
