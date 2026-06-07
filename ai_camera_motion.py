import os
import time

import cv2


from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from ultralytics import YOLO

from notification import send_discord_alert
from utils import setup_logger

# 1. Khởi tạo logger riêng cho module AI
logger = setup_logger("fire_detection", "fire_detection.log")

# Load các biến môi trường
load_dotenv(override=True)

RTSP_URL = os.getenv("RTSP_URL_1")
ROOT_ALERT_DIR = os.getenv("ROOT_ALERT_DIR")
MODEL_PATH = "models/model_1.pt"
DETECTION_INTERVAL = 5  
SCORE_THRESHOLD = 0.6  

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

    # Kết nối luồng Camera
    logger.info("📹 Đang kết nối tới Camera_1")
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        logger.error("❌ Lỗi: Không thể kết nối luồng RTSP.")
        return

    logger.info(f"🔥 Hệ thống AI kích hoạt thành công! Quét mỗi {DETECTION_INTERVAL} giây...")
    last_processed_time = time.time()

    try:
        is_interrupted = False
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
                
                # Chạy AI dự đoán
                results = model(frame, conf=0.25, verbose=False)
                result = results[0]

                if len(result.boxes) > 0:
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    alert_filename = alert_dir / f"ALERT_{now_str}.jpg"
                    
                    detected_objects = []
                    is_alert = False
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        label = model.names[cls_id]
                        conf_score = float(box.conf[0]) * 100
                        if conf_score >= SCORE_THRESHOLD * 100:
                            is_alert = True
                        detected_objects.append(f"{label} ({conf_score:.1f}%)")
                    
                    if is_alert:
                        logger.info(f"🚨 [CẢNH BÁO] Phát hiện: {', '.join(detected_objects)}")
                        result.save(filename=str(alert_filename))
                        logger.info(f"💾 Đã lưu bằng chứng tại: {alert_filename}")
                        msg = f"Phát hiện nguy hiểm lúc {datetime.now().strftime('%H:%M:%S')}: {', '.join(detected_objects)}"
                        logger.info(f"🚨 Gửi cảnh báo Discord")
                        
                        # Lưu ảnh
                        result.save(filename=str(alert_filename))
                        
                        # Gửi cảnh báo Discord
                        send_discord_alert(msg, image_path=str(alert_filename))
                        
                        logger.info("✅ Đã gửi cảnh báo thành công!")
                    
    except KeyboardInterrupt:
        logger.info("🛑 Đang đóng hệ thống giám sát AI...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("✅ Hệ thống đã được giải phóng an toàn.")

if __name__ == "__main__":
    run_ai_monitor()
    