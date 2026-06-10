import os
import time

import cv2


from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from ultralytics import YOLO

from notification import send_discord_fire_alert
from utils import setup_logger

# 1. Khởi tạo logger riêng cho module AI
logger = setup_logger("fire_detection", "fire_detection.log")

# Load các biến môi trường
load_dotenv(override=True)

RTSP_URL = os.getenv("RTSP_URL_1")
ROOT_ALERT_DIR = os.getenv("ROOT_ALERT_DIR")
MODEL_PATH = Path("models") / os.getenv("LOCAL_MODEL_FILENAME_1")
DETECTION_INTERVAL = int(os.getenv("DETECTION_INTERVAL", 5))
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", 0.6))  # Mặc định 0.6 nếu .env thiếu

def run_ai_monitor():
    # Kiểm tra cấu hình môi trường
    if not RTSP_URL or not ROOT_ALERT_DIR:
        logger.error("❌ Lỗi: Thiếu RTSP_URL_1 hoặc ROOT_ALERT_DIR trong file .env")
        return

    model_file = Path(MODEL_PATH)
    if not model_file.exists():
        logger.error(f"❌ Lỗi: Không tìm thấy file model tại: {MODEL_PATH}")
        return

    # Khởi tạo Mô hình AI
    logger.info("🤖 Đang nạp mô hình YOLOv8 Fire & Smoke...")
    model = YOLO(str(model_file))
    
    alert_dir = Path(ROOT_ALERT_DIR)
    alert_dir.mkdir(exist_ok=True, parents=True)
    source_dir = Path(os.getenv("ROOT_SOURCE_DIR", ""))
    source_dir.mkdir(exist_ok=True, parents=True)

    # 🔥 FIX 1: Ép OpenCV sử dụng giao thức TCP để giữ kết nối ổn định 24/7 với Gateway
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

    # Kết nối luồng Camera
    logger.info("📹 Đang kết nối tới Camera_1 (Qua kết nối TCP)...")
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        logger.error("❌ Lỗi: Không thể kết nối luồng RTSP.")
        return

    logger.info(f"🔥 Hệ thống AI kích hoạt thành công! Quét mỗi {DETECTION_INTERVAL} giây...")
    last_processed_time = time.time()
    is_interrupted = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("⚠️ Mất tín hiệu luồng Camera. Đang kết nối lại...")
                time.sleep(2)
                cap = cv2.VideoCapture(RTSP_URL)
                is_interrupted = True
                continue
            
            if is_interrupted:
                logger.info("✅ Kết nối lại thành công. Tiếp tục giám sát...")
                is_interrupted = False
                
            current_time = time.time()
            if current_time - last_processed_time >= DETECTION_INTERVAL:
                last_processed_time = current_time
                
                # 🔥 FIX 4: Đưa ALERT_THRESHOLD thẳng vào YOLO để lọc từ gốc, tăng tốc độ xử lý
                results = model(frame, conf=ALERT_THRESHOLD, verbose=False)
                result = results[0]

                if len(result.boxes) > 0:
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    source_filename = source_dir / f"ALERT_{now_str}.jpg"
                    alert_filename = alert_dir / f"ALERT_{now_str}.jpg"
                    
                    detected_objects = []
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        label = model.names[cls_id]
                        conf_score = float(box.conf[0]) * 100
                        detected_objects.append(f"{label} ({conf_score:.1f}%)")
                    
                    logger.info(f"🚨 [CẢNH BÁO] Phát hiện nguy hiểm: {', '.join(detected_objects)}")
                    
                    # 🔥 FIX 3: Dọn dẹp code trùng lặp ghi file, chỉ ghi ảnh 1 lần duy nhất
                    result.save(filename=str(alert_filename))
                    cv2.imwrite(str(source_filename), frame)
                    logger.info(f"💾 Đã lưu bằng chứng tại: {alert_filename}")
                    
                    # Gửi cảnh báo Discord
                    msg = f"Phát hiện nguy hiểm lúc {datetime.now().strftime('%H:%M:%S')}: {', '.join(detected_objects)}"
                    logger.info("🚨 Đang bắn cảnh báo lên Discord...")
                    send_discord_fire_alert(msg, image_path=str(alert_filename))
                    logger.info("✅ Đã gửi cảnh báo thành công!")
                
                # 🔥 FIX 2: Chỉ giải phóng các biến AI khi chúng thực sự được tạo ra ở chu kỳ quét
                del results, result

            # Dọn dẹp frame hiện tại ở mỗi vòng lặp để tránh rò rỉ RAM (Memory Leak)
            del frame
                    
    except KeyboardInterrupt:
        logger.info("🛑 Đang đóng hệ thống giám sát AI...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("✅ Hệ thống đã được giải phóng an toàn.")

if __name__ == "__main__":
    run_ai_monitor()
    