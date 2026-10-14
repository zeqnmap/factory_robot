import RPi.GPIO as GPIO
import time

TRIG = 20
ECHO = 21

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Стабилизация датчика перед замером
    GPIO.output(TRIG, False)
    time.sleep(0.05)

    # Посылаем импульс
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    stop_time = time.time()
    
    # Защита от вечного зависания / вылета (таймаут)
    timeout = time.time() + 0.1

    # Ждем начала эхо-сигнала
    while GPIO.input(ECHO) == 0:
        start_time = time.time()
        if start_time > timeout:
            return -1  # Датчик не ответил

    # Ждем конца эхо-сигнала
    timeout = time.time() + 0.1
    while GPIO.input(ECHO) == 1:
        stop_time = time.time()
        if stop_time > timeout:
            return -2  # Сигнал завис в верхнем уровне

    time_elapsed = stop_time - start_time
    distance = (time_elapsed * 34300) / 2
    return distance

print("Старт теста датчика расстояния... (Для выхода: Ctrl+C)")

try:
    while True:
        dist = get_distance()
        if dist == -1:
            print("[Ошибка] Датчик не отвечает. Проверь пин TRIG и GND.")
        elif dist == -2:
            print("[Ошибка] Сигнал ECHO не падает в ноль. Проверь делитель напряжения и пин ECHO.")
        else:
            print(f"Расстояние: {dist:.1f} см")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nТест завершен.")
    GPIO.cleanup()