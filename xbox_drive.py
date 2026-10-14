import time
import os
from gpiozero import PWMOutputDevice
import pygame
from forklift_control import lift_down, lift_stop, lift_up

LIFT_UP_BUTTON = 4      # Xbox Y
LIFT_DOWN_BUTTON = 0    # Xbox A

# --- БЕЗМОНИТОРНЫЙ РЕЖИМ ДЛЯ PYGAME ---
# Позволяет запускать скрипт по SSH без подключения экрана к Pi
os.environ["SDL_VIDEODRIVER"] = "dummy"

# --- НАСТРОЙКА ТВОИХ ПИНОВ (Левые моторы перевернуты) ---
# Передний левый мотор
FL_in1 = PWMOutputDevice(22)
FL_in2 = PWMOutputDevice(23)

# Передний правый мотор
FR_in1 = PWMOutputDevice(6)
FR_in2 = PWMOutputDevice(5)

# Задний левый мотор
RL_in1 = PWMOutputDevice(17)
RL_in2 = PWMOutputDevice(27)

# Задний правый мотор
RR_in1 = PWMOutputDevice(16)
RR_in2 = PWMOutputDevice(19)

def set_motor(pin1, pin2, speed):
    """
    Подает ШИМ на один мотор.
    speed: значение от -1.0 (назад) до 1.0 (вперед)
    """
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
    """
    Математика меканум-колес.
    x - стрейф / езда боком (Левый стик по горизонтали)
    y - газ / вперед-назад (Левый стик по вертикали)
    r - разворот на месте (Правый стик по горизонтали)
    """
    # Смешиваем сигналы для каждого колеса
    speed_FL = y + x + r
    speed_FR = y - x - r
    speed_RL = y - x + r
    speed_RR = y + x - r

    # Нормализуем скорости, чтобы они не превышали лимит ШИМ (1.0)
    max_val = max(abs(speed_FL), abs(speed_FR), abs(speed_RL), abs(speed_RR))
    if max_val > 0.6:
        speed_FL /= max_val
        speed_FR /= max_val
        speed_RL /= max_val
        speed_RR /= max_val

    # Отправляем команды на драйверы
    set_motor(FL_in1, FL_in2, speed_FL)
    set_motor(FR_in1, FR_in2, speed_FR)
    set_motor(RL_in1, RL_in2, speed_RL)
    set_motor(RR_in1, RR_in2, speed_RR)

def main():
    # Инициализация pygame для работы с джойстиком
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0:
        print("❌ Геймпад не найден! Подключи Xbox контроллер по Bluetooth или кабелю.")
        return

    # Подключаем первый найденный джойстик
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"🤖 Успешно подключен геймпад: {joystick.get_name()}")
    print("\n🎮 СХЕМА УПРАВЛЕНИЯ:")
    print(" Левый стик (Вверх/Вниз)  ->  Езда вперед/назад")
    print(" Левый стик (Влево/Вправо)->  Езда боком (стрейф)")
    print(" Правый стик (Влево/Вправо)-> Разворот на месте")
    print(" Y -> Поднять вилы, A -> Опустить вилы")
    print(" Для выхода нажми CTRL+C")

    try:
        while True:
            # Опрашиваем состояние геймпада
            pygame.event.pump()

            # Считываем оси стиков (значения от -1.0 до 1.0)
            # Ось 0: Левый стик Влево/Вправо
            # Ось 1: Левый стик Вверх/Вниз (инвертируем, так как у pygame "вверх" это минус)
            # Ось 3: Правый стик Влево/Вправо (на некоторых геймпадах это может быть Ось 2)
            x = joystick.get_axis(0)
            y = -joystick.get_axis(1)
            r = joystick.get_axis(3)

            # Мертвая зона стиков (чтобы робот не полз и не пищал, когда ты не трогаешь джойстик)
            deadzone = 0.15
            if abs(x) < deadzone: x = 0.0
            if abs(y) < deadzone: y = 0.0
            if abs(r) < deadzone: r = 0.0

            # Отправляем вычисленные значения на моторы
            drive_mecanum(x, y, r)

            # The lift has its own DRV8833 channel and stops when released.
            if joystick.get_button(LIFT_UP_BUTTON):
                lift_up()
            elif joystick.get_button(LIFT_DOWN_BUTTON):
                lift_down()
            else:
                lift_stop()

            # Пауза 20 мс, чтобы не перегружать процессор малинки
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nВыход из программы...")
    finally:
        # При остановке скрипта обязательно глушим все моторы!
        drive_mecanum(0, 0, 0)
        lift_stop()
        pygame.quit()
        print("Робот остановлен и обесточен.")

if __name__ == "__main__":
    main()