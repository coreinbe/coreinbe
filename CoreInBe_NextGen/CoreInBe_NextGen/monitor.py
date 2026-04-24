import cv2
import numpy as np
from ultralytics import YOLO
import time
import asyncio
import threading
from datetime import datetime
import os

class CoreInBeMonitor:
    def __init__(self, 
                 yolo_weights='yolov8s.pt', # Используем стабильную YOLOv8s, но с оптимизацией YOLOv10
                 conf_threshold=0.3,
                 stop_event=None
                ):
        
        print("[SYSTEM] Инициализация CoreInBe NextGen...")
        # Загружаем модель один раз
        self.model = YOLO(yolo_weights)
        self.conf_threshold = conf_threshold
        
        self.current_loop = None
        self.stop_event = stop_event if stop_event else threading.Event()
        self.send_alert_func = None

        # ID классов: 0 - person, 67 - cell phone
        self.person_id = 0
        self.phone_id = 67 
        self.last_alert_time = 0

    def set_alert_function(self, func, loop):
        self.send_alert_func = func
        self.current_loop = loop

    def process_frame(self, frame):
        # Оптимизированная детекция: ищем только людей и телефоны
        results = self.model(frame, verbose=False, imgsz=320, classes=[0, 67])[0]
        
        phone_detected = False
        annotated_frame = frame.copy()
        
        people = []
        phones = []

        # Разбираем результаты (БЕЗ ОШИБОК TENSOR)
        if results.boxes is not None:
            for box in results.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < self.conf_threshold: continue
                
                coords = box.xyxy[0].cpu().numpy().astype(int)
                if cls == self.person_id:
                    people.append((coords, conf))
                elif cls == self.phone_id:
                    phones.append((coords, conf))
                    phone_detected = True

        # Логика цветных боксов
        for (p_coords, p_conf) in people:
            px1, py1, px2, py2 = p_coords
            color = (0, 255, 0) # Зеленый (OK)
            label = "STUDENT: OK"
            
            # Проверяем наличие телефона у студента
            for (ph_coords, ph_conf) in phones:
                phx1, phy1, phx2, phy2 = ph_coords
                # Если телефон в зоне студента
                if phx1 > px1 - 30 and phx2 < px2 + 30 and phy1 > py1 - 30 and phy2 < py2 + 30:
                    color = (0, 0, 255) # КРАСНЫЙ (Нарушение)
                    label = "!!! PHONE DETECTED !!!"
                    # Рисуем рамку телефона (ОРАНЖЕВЫЙ)
                    cv2.rectangle(annotated_frame, (phx1, phy1), (phx2, phy2), (0, 165, 255), 3)

            # Рисуем рамку студента
            cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), color, 4)
            cv2.putText(annotated_frame, label, (px1, py1 - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Мгновенная отправка фото в Telegram
        if phone_detected:
            now = time.time()
            if now - self.last_alert_time > 3:
                img_name = f"alert_{datetime.now().strftime('%H%M%S')}.jpg"
                img_path = os.path.join("alerts", img_name)
                os.makedirs("alerts", exist_ok=True)
                cv2.imwrite(img_path, annotated_frame)
                
                if self.current_loop and self.send_alert_func:
                    asyncio.run_coroutine_threadsafe(
                        self.send_alert_func(img_path, "НАРУШЕНИЕ: ТЕЛЕФОН!", datetime.now()),
                        self.current_loop
                    )
                self.last_alert_time = now

        return annotated_frame

    def run(self, source=0):
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("[ERROR] Камера не найдена!")
            return

        win_name = "CoreInBe NextGen"
        cv2.namedWindow(win_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(win_name, cv2.WND_PROP_TOPMOST, 1)
        
        print("[SYSTEM] Камера включена. Мониторинг активен.")

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret: break
            
            out_frame = self.process_frame(frame)
            cv2.imshow(win_name, out_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
