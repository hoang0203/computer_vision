import json
import os


from pathlib import Path

from huggingface_hub import hf_hub_download
from dotenv import load_dotenv

load_dotenv(override=True)

def download_and_update_metadata(repo_id: str, filename: str, local_filename: str = None, local_folder: str = "models"):
    # 1. Tạo thư mục cục bộ nếu chưa có
    models_dir = Path(local_folder)
    models_dir.mkdir(exist_ok=True)
    metadata_file = models_dir / "metadata.json"

    # 2. Tải mô hình từ Hugging Face
    print(f"Đang tải {filename} từ {repo_id}...")
    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id, 
            filename=filename, 
            local_dir=local_folder
        )
        current_path = Path(downloaded_path)
        
        # Thao tác đổi tên file tại local nếu bạn truyền vào local_filename
        if local_filename:
            target_path = models_dir / local_filename
            if current_path != target_path:
                if target_path.exists():
                    target_path.unlink()  # Xóa file trùng tên cũ nếu có để tránh lỗi
                current_path.rename(target_path)
            current_path = target_path
            final_filename = local_filename
        else:
            final_filename = filename

        print(f"Model đã lưu thành công tại: {current_path}")
    except Exception as e:
        print(f"Lỗi khi tải file: {e}")
        return

    # 3. Xử lý metadata an toàn
    metadata = {}
    if metadata_file.exists():
        with metadata_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

    # Cập nhật metadata dựa theo tên file mới (model_1)
    model_key = Path(final_filename).stem
    metadata[model_key] = repo_id

    # Lưu lại file metadata.json
    with metadata_file.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"Đã cập nhật metadata cho {model_key}!")

if __name__ == "__main__":
    REPO_ID = os.getenv("REPO_ID_1")
    FILENAME = os.getenv("MODEL_FILENAME_1")
    LOCAL_FILENAME = os.getenv("LOCAL_MODEL_FILENAME_1")  # Tên file bạn muốn lưu ở máy local
    download_and_update_metadata(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_filename=LOCAL_FILENAME
    )
    