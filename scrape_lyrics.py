import json
import lyricsgenius
import time
import os
import requests
import re
from bs4 import BeautifulSoup
import undetected_chromedriver as uc 

GENIUS_TOKEN = "LFP9Sx7dySmRjOZ9PKKbVK-znlIDKnP2PQT_x8dQyGggV32trYkS82xHQEC09Cxg"
MAX_SONGS_PER_ARTIST = 50

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, 'vietnamese_artists.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'lyrics_dataset.json') 
HISTORY_FILE = os.path.join(BASE_DIR, 'history_log.json')    

options = uc.ChromeOptions()
options.add_argument("--disable-popup-blocking") 

print("\n" + "="*50)
print("ĐANG KHỞI ĐỘNG CHROME...")
driver = uc.Chrome(options=options)

print("HƯỚNG DẪN:")
print("1. Trình duyệt mở Genius.com -> Bấm CAPTCHA nếu có.")
print("2. Đợi web tải xong.")
print("="*50 + "\n")

driver.get("https://genius.com")
input("Thấy trang chủ Genius hiện ra bấm ENTER")
print("\nĐã vượt. Bắt đầu cào...")

genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.verbose = False
genius.skip_non_songs = True

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def manual_search_artist_id(artist_name):
    url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    params = {"q": artist_name}
    try:
        r = requests.get(url, params=params, headers=headers)
        if r.status_code == 200:
            hits = r.json()['response']['hits']
            if hits:
                return hits[0]['result']['primary_artist']['id'], hits[0]['result']['primary_artist']['name']
    except Exception as e:
        print(f"Lỗi API search: {e}")
    return None, None

def get_lyrics_and_tags_stealth(song_url):
    try:
        driver.get(song_url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        lyrics_divs = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
        if not lyrics_divs:
            lyrics_divs = soup.find_all('div', class_=lambda x: x and x.startswith('Lyrics__Container'))
            
        final_lyrics = None
        if lyrics_divs:
            text_parts = []
            for div in lyrics_divs:
                for br in div.find_all("br"):
                    br.replace_with("\n")
                text_parts.append(div.get_text())
            
            raw_text = "\n".join(text_parts).strip()
            
            raw_text = re.sub(r"^.*?Lyrics\s*", "", raw_text, flags=re.IGNORECASE | re.DOTALL)
            raw_text = re.sub(r"\d+\s*Contributors?\s*", "", raw_text, flags=re.IGNORECASE)
            raw_text = re.sub(r"\[.*?(?:Lời bài hát|Lyrics).*?\]\s*", "", raw_text, flags=re.IGNORECASE | re.DOTALL)
            
            final_lyrics = raw_text.strip()

        found_tags = []
        try:
            tag_links = soup.find_all('a', href=re.compile(r'/tags/'))
            for link in tag_links:
                tag_text = link.get_text().strip()
                if tag_text and len(tag_text) < 50 and tag_text not in found_tags:
                    if "all tags" not in tag_text.lower():
                        found_tags.append(tag_text)
        except:
            pass

        return final_lyrics, found_tags
            
    except Exception as e:
        print(f"Lỗi Driver: {e}")
        return None, []

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Lỗi: Không tìm thấy file {INPUT_FILE}")
        return

    artists_list = load_json(INPUT_FILE)
    
    all_songs_dataset = load_json(OUTPUT_FILE)
    history_log = load_json(HISTORY_FILE)
    
    processed_urls = set(item['url'] for item in history_log if 'url' in item)
    
    print(f"Đã load {len(all_songs_dataset)} mẫu dataset.")
    print(f"Đã load {len(processed_urls)} URL trong lịch sử.")

    try:
        for name in artists_list:
            print(f"\n--- Đang xử lý: {name} ---")
            
            artist_id, official_name = manual_search_artist_id(name)
            if not artist_id:
                print("Không tìm thấy ID.")
                continue
                
            print(f"ID: {artist_id}. Lấy list nhạc...")
            
            try:
                artist_obj = genius.artist_songs(artist_id, sort='popularity', per_page=MAX_SONGS_PER_ARTIST, page=1)
                
                songs_list = []
                if isinstance(artist_obj, dict) and 'songs' in artist_obj:
                    songs_list = artist_obj['songs']
                elif hasattr(artist_obj, 'songs'):
                    songs_list = artist_obj.songs

                print(f"Tìm thấy {len(songs_list)} bài. Bắt đầu lọc & tải...")
                
                new_count = 0
                for song in songs_list:
                    if isinstance(song, dict):
                        url = song.get('url')
                        title = song.get('title')
                    else:
                        url = song.url
                        title = song.title
                    
                    if url in processed_urls:
                        print(f"Đã có: {title}")
                        continue
                    # -------------------------------

                    lyrics, scraped_tags = get_lyrics_and_tags_stealth(url)
                    
                    if lyrics and len(lyrics) > 20: 
                        tags_str = ", ".join(scraped_tags) if scraped_tags else ""
                        prompt_text = f"Viết lời bài hát {tags_str} của {official_name}:\n"
                        
                        all_songs_dataset.append({
                            "prompt": prompt_text,
                            "completion": lyrics
                        })
                        
                        history_log.append({
                            "url": url,
                            "title": title,
                            "artist": official_name
                        })
                        processed_urls.add(url)
                        
                        print(f"      + OK: {title}")
                        new_count += 1
                    else:
                        print(f"      - RỖNG/LỖI: {title}")
                    
                    time.sleep(2)

                if new_count > 0:
                    save_json(all_songs_dataset, OUTPUT_FILE)
                    save_json(history_log, HISTORY_FILE)
                    print(f"Đã lưu {new_count} mẫu mới.")

            except Exception as e:
                print(f"Lỗi xử lý vòng lặp: {e}")

    except KeyboardInterrupt:
        print("\nDừng chương trình.")
    finally:
        if all_songs_dataset:
            save_json(all_songs_dataset, OUTPUT_FILE)
            save_json(history_log, HISTORY_FILE)
            print(f"\n💾 TỔNG KẾT: {len(all_songs_dataset)} MẪU.")
        
        print("Đang đóng trình duyệt...")
        driver.quit()

if __name__ == "__main__":
    main()