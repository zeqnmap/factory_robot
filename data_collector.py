import time
import os
import cv2
from gpiozero import PWMOutputDevice
import pygame
from forklift_control import lift_down, lift_stop, lift_up

LIFT_UP_BUTTON = 4      # Xbox Y
LIFT_DOWN_BUTTON = 0    # Xbox A

# --- НАСТРОЙКИ ---
IMAGE_DIR = "/home/zeqnmap/robot/dataset_photos"
IMG_WIDTH = 160
IMG_HEIGHT = 80
FPS_RECORD = 6 # Записываем 10 кадров в секунду

# Создаем папку, если ее еще нет
os.makedirs(IMAGE_DIR, exist_ok=True)

os.environ["SDL_VIDEODRIVER"] = "dummy"

# --- НАСТРОЙКА ПИНОВ ---
FL_in1 = PWMOutputDevice(22)
FL_in2 = PWMOutputDevice(23)
FR_in1 = PWMOutputDevice(6)
FR_in2 = PWMOutputDevice(5)
RL_in1 = PWMOutputDevice(17)
RL_in2 = PWMOutputDevice(27)
RR_in1 = PWMOutputDevice(16)
RR_in2 = PWMOutputDevice(19)

def set_motor(pin1, pin2, speed):
    if speed > 0:
        pin1.value = speed
        pin2.value = 0
    elif speed < 0:
        pin1.value = 0
        pin2.value = abs(speed)
    else:
        pin1.value = 0
        pin2.value = 0

def drive_mecanum(x, y, r):
    speed_FL = y + x + r
    speed_FR = y - x - r
    speed_RL = y - x + r
    speed_RR = y + x - r

    max_val = max(abs(speed_FL), abs(speed_FR), abs(speed_RL), abs(speed_RR))
    if max_val > 1.0:
        speed_FL /= max_val
        speed_FR /= max_val
        speed_RL /= max_val
        speed_RR /= max_val

    speed_FL = speed_FL
    speed_FR = speed_FR
    speed_RL = speed_RL
    speed_RR = speed_RR
    
    
    set_motor(FL_in1, FL_in2, speed_FL)
    set_motor(FR_in1, FR_in2, speed_FR)
    set_motor(RL_in1, RL_in2, speed_RL)
    set_motor(RR_in1, RR_in2, speed_RR)

def main():
    # --- ИНИЦИАЛИЗАЦИЯ КАМЕРЫ ---
    print("📷 Инициализация камеры...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_HEIGHT)
    time.sleep(2) # Ждем фокус и баланс белого

    if not cap.isOpened():
        print("❌ ОШИБКА: Камера не найдена!")
        return

    # --- ИНИЦИАЛИЗАЦИЯ ДЖОЙСТИКА ---
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0:
        print("❌ Геймпад не найден!")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"🤖 Геймпад подключен: {joystick.get_name()}")
    print(f"📁 Фотографии будут сохраняться в: {IMAGE_DIR}")
    print("\n🚀 Можно ехать! Сбор данных начнется автоматически при движении.")

    frame_count = 0
    # Вычисляем задержку между снимками в секундах (1 / 10 = 0.1 сек)
    save_interval = 1.0 / FPS_RECORD 
    last_save_time = time.time()

    try:
        while True:
            # 1. Читаем джойстик
            pygame.event.pump()
            x = joystick.get_axis(0)
            y = -joystick.get_axis(1)
            r = joystick.get_axis(3)

            deadzone = 0.15
            if abs(x) < deadzone: x = 0.0
            if abs(y) < deadzone: y = 0.0
            if abs(r) < deadzone: r = 0.0
            x = x * 0.4
            y = y * 0.4
            r = r * 0.4
            # 2. Двигаем робота (вызывается постоянно)
            drive_mecanum(x, y, r)

            # The lift is controlled independently from the drive wheels.
            if joystick.get_button(LIFT_UP_BUTTON):
                lift_up()
            elif joystick.get_button(LIFT_DOWN_BUTTON):
                lift_down()
            else:
                lift_stop()

            # 3. Делаем снимки (вызывается только 10 раз в секунду и только при движении)
            current_time = time.time()
            if current_time - last_save_time >= save_interval:
                
                # Если хотя бы один стик нажат (робот не стоит на месте)
                if abs(x) > 0 or abs(y) > 0 or abs(r) > 0:
                    ret, frame = cap.read()
                    
                    if ret:
                        # Формат: НомерКадра_Газ_Стрейф_Поворот.jpg
                        # Пример: 0005_0.80_-0.20_0.00.jpg
                        filename = f"{frame_count:05d}_{y:.2f}_{x:.2f}_{r:.2f}.jpg"
                        filepath = os.path.join(IMAGE_DIR, filename)
                        
                        cv2.imwrite(filepath, frame)
                        frame_count += 1
                        last_save_time = current_time
                        
                        # Выводим инфу каждую 10-ю фотку, чтобы не спамить в консоль
                        if frame_count % 10 == 0:
                            print(f"📸 Собрано кадров: {frame_count} | Последний: {filename}")
                else:
                    # Если робот стоит, всё равно "проглатываем" кадр из буфера камеры, 
                    # чтобы при начале движения картинка была свежей, а не старой
                    cap.read() 
                    last_save_time = current_time

            time.sleep(0.02) # Обновление моторов 50 раз в секунду

    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        drive_mecanum(0, 0, 0)
        lift_stop()
        pygame.quit()
        cap.release()
        print(f"✅ Робот обесточен. Всего собрано фото: {frame_count}")

if __name__ == "__main__":
    main()