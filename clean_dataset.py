import json
import re
import os

INPUT_FILE = 'lyrics_dataset.json'
OUTPUT_FILE = 'lyrics_dataset_clean.json'

def remove_artist_from_prompt(prompt_text):
    # Regex pattern:
    # \s+của\s+  -> Tìm khoảng trắng + chữ "của" + khoảng trắng
    # [^:]+      -> Tìm bất kỳ ký tự nào KHÔNG PHẢI dấu hai chấm
    # :          -> Kết thúc ở dấu hai chấm
    pattern = r"\s+của\s+[^:]+:"
    
    # Thay thế đoạn tìm được bằng dấu ":"
    new_prompt = re.sub(pattern, ":", prompt_text)
    return new_prompt

def main():
    # 1. Kiểm tra file tồn tại
    if not os.path.exists(INPUT_FILE):
        print(f"Lỗi: Không tìm thấy file '{INPUT_FILE}'")
        return

    print(f"Đang đọc dữ liệu từ {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Đã load {len(data)} mẫu dữ liệu.")
        
        cleaned_data = []
        
        # 2. Duyệt qua từng dòng và xử lý
        for item in data:
            old_prompt = item.get('prompt', '')
            completion = item.get('completion', '')
            
            # Xử lý cắt bỏ tên ca sĩ
            new_prompt = remove_artist_from_prompt(old_prompt)
            
            cleaned_data.append({
                "prompt": new_prompt,
                "completion": completion
            })

        # 3. Lưu ra file mới
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
            
        print(f"Đã lưu file sạch tại: {OUTPUT_FILE}")
        print(f"Tổng số mẫu: {len(cleaned_data)}")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()