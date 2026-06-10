import os
import time
import subprocess


from dotenv import load_dotenv

from utils import setup_logger

# 1. Khởi tạo logger riêng cho module Gateway
logger = setup_logger("gateway", "gateway.log")

# 2. Nạp các biến từ file .env
load_dotenv(override=True)

# 3. Lấy link camera thật từ .env
real_camera_url = os.getenv("RTSP_REAL_CAMERA_1")

if not real_camera_url:
    logger.error("❌ Lỗi: Không tìm thấy biến RTSP_REAL_CAMERA_1 trong file .env")
    exit(1)

# 4. Cấu hình môi trường cho MediaMTX
env_context = os.environ.copy()
env_context["MTX_PATHS_CAMERA1_SOURCE"] = real_camera_url

env_context["MTX_PATHS_CAMERA1_RTSPTRANSPORT"] = "tcp"

# 5. Đường dẫn trỏ tới file mediamtx.exe
mediamtx_dir = os.path.abspath(os.path.join(".", "mediamtx"))
mediamtx_path = os.path.join(mediamtx_dir, "mediamtx.exe")

logger.info("🚀 Đang khởi động MediaMTX Gateway bằng cấu hình từ file .env...")

try:
    # Chạy MediaMTX
    # Sử dụng subprocess.Popen thay vì .run để không làm "đứng" script main.py
    # Ghi log lỗi của MediaMTX vào file gateway.log
    process = subprocess.Popen(
        [mediamtx_path], 
        env=env_context, 
        cwd=mediamtx_dir,
        stdout=subprocess.DEVNULL, # Ẩn output rác ra terminal
        stderr=subprocess.PIPE     # Giữ lại các cảnh báo lỗi để debug nếu cần
    )
    logger.info(f"✅ MediaMTX Gateway đã khởi động với PID: {process.pid}")
    while process.poll() is None:
        time.sleep(1)
            
except FileNotFoundError:
    logger.error(f"❌ Lỗi: Không tìm thấy file thực thi tại {mediamtx_path}. Hãy kiểm tra lại đường dẫn.")
    