import os
import subprocess
import time
import threading
import re


from dotenv import load_dotenv

from notification import send_discord_camera_alert
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
        send_discord_camera_alert("❌ Lỗi: Không tìm thấy FFmpeg trong hệ thống. Vui lòng cài đặt FFmpeg và đảm bảo nó có trong PATH.")
        return None

if __name__ == "__main__":
    if RTSP_URL and ROOT_DIR:
        
        # --- CẤU HÌNH LOGIC RESTART ---
        MAX_RESTARTS = 3
        STABLE_UPTIME_SECONDS = 1 * 60  # 15 phút (tính bằng giây)
        restart_count = 0
        
        try:
            while True:
                # Logic 1: Kiểm tra giới hạn khởi động lại
                if restart_count >= MAX_RESTARTS:
                    logger.error(f"❌ Đã sập {MAX_RESTARTS} lần liên tục. Ngừng cố gắng khởi động lại để bảo vệ hệ thống!")
                    send_discord_camera_alert(f"🚨 **BÁO ĐỘNG ĐỎ:** Camera mất kết nối hoàn toàn. Đã thử khởi động lại {MAX_RESTARTS} lần nhưng thất bại. Vui lòng kiểm tra phần cứng hoặc mạng ngay lập tức!")
                    break  # Thoát hẳn khỏi vòng lặp vô hạn

                proc = start_recording()
                
                if not proc:
                    break 

                logger.info(f"📌 Hệ thống đang giám sát luồng ghi hình 24/7 (Lần thử: {restart_count}/{MAX_RESTARTS}).")
                
                # Ghi nhận thời điểm FFmpeg bắt đầu chạy
                process_start_time = time.time()
                
                while proc.poll() is None:
                    time.sleep(5) 
                    
                    # Logic 2: Reset bộ đếm nếu hệ thống sống sót qua 15 phút
                    current_uptime = time.time() - process_start_time
                    if current_uptime >= STABLE_UPTIME_SECONDS and restart_count > 0:
                        logger.info("✅ Luồng ghi hình đã hoạt động ổn định liên tục 15 phút. Khôi phục lại bộ đếm restart về 0.")
                        restart_count = 0  # Reset bộ đếm
                
                # Nếu code chạy xuống đây, tức là FFmpeg đã sập
                restart_count += 1
                logger.warning(f"⚠️ Tiến trình FFmpeg tự thoát (Mã lỗi: {proc.returncode}). Chuẩn bị khởi động lại lần {restart_count}...")
                send_discord_camera_alert(f"⚠️ Tiến trình ghi hình văng (Mã lỗi: {proc.returncode}). Đang thử khởi động lại lần {restart_count}/{MAX_RESTARTS} sau 10 giây...")
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("🛑 Đang dừng ghi hình an toàn theo yêu cầu người dùng...")
            if 'proc' in locals() and proc and proc.poll() is None:
                proc.terminate()
                proc.wait()
            logger.info("✅ Đã giải phóng luồng ghi hình thành công và thoát hẳn.")
            
    else:
        logger.error("❌ Lỗi: Kiểm tra lại file .env, đảm bảo có đủ RTSP_URL và ROOT_DIR.")
        send_discord_camera_alert("❌ Lỗi cấu hình: Kiểm tra lại file .env, đảm bảo có đủ RTSP_URL và ROOT_DIR.")
        