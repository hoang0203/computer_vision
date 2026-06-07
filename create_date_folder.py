import os

from datetime import datetime, timedelta

from dotenv import load_dotenv

from utils import setup_logger

# Load biến từ file .env
load_dotenv(override=True)
ROOT_DIR = os.getenv("ROOT_DIR_1")

# Khởi tạo logger riêng cho file này
logger = setup_logger("folder_setup", "folder_setup.log")

def create_date_folders():
    """Tạo thư mục cho ngày hiện tại và 30 ngày tiếp theo"""
    for offset in range(0, 31):
        target_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
        os.makedirs(os.path.join(ROOT_DIR, target_date), exist_ok=True)

if __name__ == "__main__":
    if ROOT_DIR:
        logger.info(f"📌 Đường dẫn gốc: {ROOT_DIR}")
        try:
            create_date_folders()
            logger.info("🚀 Đã tạo thư mục cho ngày hiện tại và 30 ngày tiếp theo.")
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo thư mục: {e}")
    else:
        logger.error("❌ Lỗi: ROOT_DIR_1 chưa được định nghĩa trong file .env.")
        