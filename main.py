import sys
import subprocess
import time
from utils import setup_logger

# 1. Khởi tạo logger cho hệ thống điều phối (main)
logger = setup_logger("controller", "controller.log")

# --- ĐỊNH NGHĨA CÁC FILE SCRIPT ---
FOLDER_SETUP_SCRIPT = "create_date_folder.py"
GATEWAY_SCRIPT = "run_gateway.py"
SAVE_CAMERA_SCRIPT = "save_camera.py"
AI_CAMERA_SCRIPT = "ai_camera_motion.py"

running_processes = []

def start_system():
    logger.info("🚀 [0/4] Đang khởi động hệ thống...")
    
    try:
        # =====================================================================
        # TIẾN TRÌNH 0: Tạo cấu trúc thư mục (Chờ hoàn tất)
        # =====================================================================
        logger.info(f"📁 [1/4] Đang gọi script thiết lập thư mục: {FOLDER_SETUP_SCRIPT}")
        subprocess.run([sys.executable, FOLDER_SETUP_SCRIPT], check=True)
        logger.info("✅ Đã thiết lập xong cấu trúc thư mục.")

        # =====================================================================
        # TIẾN TRÌNH 1: Gateway
        # =====================================================================
        logger.info(f"🚀 [2/4] Đang gọi Gateway: {GATEWAY_SCRIPT}...")
        p_gateway = subprocess.Popen([sys.executable, GATEWAY_SCRIPT])
        running_processes.append(p_gateway)
        
        logger.info("⏳ Chờ MediaMTX Gateway khởi động...")
        time.sleep(4)

        # =====================================================================
        # TIẾN TRÌNH 2: Ghi hình
        # =====================================================================
        logger.info(f"🎥 [3/4] Đang khởi động luồng ghi video: {SAVE_CAMERA_SCRIPT}...")
        p_save = subprocess.Popen([sys.executable, SAVE_CAMERA_SCRIPT])
        running_processes.append(p_save)

        # =====================================================================
        # TIẾN TRÌNH 3: AI Monitor
        # =====================================================================
        logger.info(f"🧠 [4/4] Đang khởi động mô hình AI: {AI_CAMERA_SCRIPT}...")
        p_ai = subprocess.Popen([sys.executable, AI_CAMERA_SCRIPT])
        running_processes.append(p_ai)

        logger.info("✅ TOÀN BỘ HỆ THỐNG ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
        logger.info("👉 Nhấn [Ctrl + C] tại Terminal này để TẮT TẤT CẢ.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Nhận tín hiệu dừng! Đang giải phóng hệ thống...")
        kill_all_processes()
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Lỗi nghiêm trọng khi khởi động script hệ thống: {e}")

def kill_all_processes():
    for p in running_processes:
        if p.poll() is None:
            try:
                logger.info(f"-> Đang đóng tiến trình PID: {p.pid}")
                p.terminate()
            except Exception as e:
                logger.error(f"❌ Không thể tắt tiến trình {p.pid}: {e}")
                
    for p in running_processes:
        p.wait()
        
    logger.info("🎉 Toàn bộ hệ thống đã được đóng sạch sẽ!")

if __name__ == "__main__":
    start_system()
    