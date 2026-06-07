import os
import subprocess
import time
import threading
import re
from dotenv import load_dotenv
from utils import setup_logger

# 1. Khởi tạo logger riêng cho module ghi hình
logger = setup_logger("camera_recorder", "camera_recorder.log")

# Load các biến từ file .env
load_dotenv(override=True)

RTSP_URL = os.getenv("RTSP_URL_1")
ROOT_DIR = os.getenv("ROOT_DIR_1")

def monitor_ffmpeg_logs(process):
    """
    Hàm này chạy trong một luồng riêng để:
    1. Tiêu thụ stderr, tránh lỗi tràn bộ đệm làm treo FFmpeg.
    2. Bắt sự kiện lưu file thành công để ghi vào file log.
    """
    # Regex để bắt dòng log FFmpeg tạo file mới
    # FFmpeg thường báo log dạng: [segment @ ...] Opening '/path/to/file.mp4' for writing
    pattern = re.compile(r"Opening '(.*?)' for writing")
    
    # Đọc liên tục từng dòng từ stderr
    for line in iter(process.stderr.readline, b''):
        # Decode dòng log
        decoded_line = line.decode('utf-8', errors='ignore').strip()
        
        # Bắt tên file mỗi khi một segment mới bắt đầu ghi
        match = pattern.search(decoded_line)
        if match:
            filepath = match.group(1)
            logger.info(f"💾 Chuyển sang file video mới: {filepath}")
            
        # Tùy chọn: Nếu bạn muốn log luôn cả các lỗi nghiêm trọng từ luồng camera
        if "error" in decoded_line.lower():
            logger.warning(f"FFmpeg Warning/Error: {decoded_line}")

def start_recording():
    output_pattern = os.path.join(ROOT_DIR, "%Y-%m-%d", "%H%M%S.mp4")
    
    # Tự động tạo thư mục ROOT_DIR nếu chưa có để tránh lỗi ffmpeg không ghi được
    os.makedirs(ROOT_DIR, exist_ok=True)
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', RTSP_URL,
        '-c:v', 'copy',             
        '-c:a', 'aac',               
        '-f', 'segment',
        '-segment_time', '900',
        '-segment_format', 'mp4',
        '-reset_timestamps', '1',
        '-strftime', '1',
        output_pattern
    ]

    logger.info("🚀 Bắt đầu tiến trình ghi hình camera vào luồng daemon...")
    try:
        process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.DEVNULL, # Ẩn log rác
            stderr=subprocess.PIPE     # Đẩy lỗi/log quá trình vào pipe để Python đọc
        )
        
        # Khởi tạo và chạy luồng giám sát stderr
        log_thread = threading.Thread(
            target=monitor_ffmpeg_logs, 
            args=(process,), 
            daemon=True # Daemon thread sẽ tự động tắt khi chương trình chính tắt
        )
        log_thread.start()
        
        return process
    except FileNotFoundError:
        logger.error("❌ Lỗi: Không tìm thấy FFmpeg trong hệ thống.")
        return None

if __name__ == "__main__":
    if RTSP_URL and ROOT_DIR:
        proc = start_recording()
        if proc:
            try:
                logger.info("📌 Hệ thống đang giám sát luồng ghi hình 24/7. Nhấn Ctrl+C để dừng.")
                while proc.poll() is None:
                    time.sleep(60)  
                
                logger.warning(f"⚠️ Tiến trình FFmpeg đã tự thoát đột ngột với mã lỗi: {proc.returncode}")
                
            except KeyboardInterrupt:
                logger.info("🛑 Đang dừng ghi hình an toàn theo yêu cầu người dùng...")
                proc.terminate()
                proc.wait()
                logger.info("✅ Đã giải phóng luồng ghi hình thành công.")
    else:
        logger.error("❌ Lỗi: Kiểm tra lại file .env, đảm bảo có đủ RTSP_URL và ROOT_DIR.")
        