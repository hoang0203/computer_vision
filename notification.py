import os

import requests


from dotenv import load_dotenv

from utils import setup_logger

# Khởi tạo logger cho hệ thống thông báo
logger = setup_logger("notifier", "notification.log")

load_dotenv(override=True)
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_discord_alert(message, image_path=None):
    """Gửi tin nhắn và ảnh cảnh báo qua Discord Webhook"""
    if not DISCORD_WEBHOOK:
        logger.error("❌ DISCORD_WEBHOOK chưa được cấu hình trong file .env")
        return

    data = {
        "content": f"🚨 **CẢNH BÁO HỆ THỐNG** 🚨\n{message}"
    }
    
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as file:
                files = {"file": (os.path.basename(image_path), file, "image/jpeg")}
                response = requests.post(DISCORD_WEBHOOK, data=data, files=files)
        else:
            response = requests.post(DISCORD_WEBHOOK, json=data)
            
        if response.status_code in [200, 204]:
            logger.info("✅ Đã gửi cảnh báo qua Discord thành công!")
        else:
            logger.error(f"❌ Lỗi khi gửi Discord: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Lỗi hệ thống khi gửi Discord: {e}")
        