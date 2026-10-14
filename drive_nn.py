import time
import cv2
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from gpiozero import PWMOutputDevice
from forklift_control import lift_stop

# --- НАСТРОЙКИ ---
IMG_WIDTH = 160
IMG_HEIGHT = 80

# Архитектура сети (ОБЯЗАТЕЛЬНО должна совпадать с тем, на чем обучал!)
class LineFollowerNet(nn.Module):
    def __init__(self):
        super(LineFollowerNet, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU()
        )
        self.fc = nn.Sequential(
            nn.Linear(64 * 7 * 20, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 3) # Выходы: y (газ), x (стрейф), r (поворот)
        )

    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)

# --- НАСТРОЙКА МОТОРОВ ---
FL_in1, FL_in2 = PWMOutputDevice(22), PWMOutputDevice(23)
FR_in1, FR_in2 = PWMOutputDevice(6), PWMOutputDevice(5)
RL_in1, RL_in2 = PWMOutputDevice(17), PWMOutputDevice(27)
RR_in1, RR_in2 = PWMOutputDevice(16), PWMOutputDevice(19)

def set_motor(pin1, pin2, speed):
    if speed > 0:
        pin1.value = min(speed, 1.0)
        pin2.value = 0
    elif speed < 0:
        pin1.value = 0
        pin2.value = min(abs(speed), 1.0)
    else:
        pin1.value, pin2.value = 0, 0

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

    # Поправочные коэффициенты под твою ходовую
    set_motor(FL_in1, FL_in2, speed_FL)
    set_motor(FR_in1, FR_in2, speed_FR)
    set_motor(RL_in1, RL_in2, speed_RL)
    set_motor(RR_in1, RR_in2, speed_RR)

def main():
    device = torch.device("cpu") # На Raspberry Pi работаем на процессоре
    print("🧠 Загрузка модели...")
    model = LineFollowerNet()
    model.load_state_dict(torch.load("line_follower_model.pth", map_location=device))
    model.eval()

    print("📷 Инициализация камеры...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_HEIGHT)
    transform = transforms.ToTensor()

    print("🚀 Автономный режим запущен! Поставь робота на линию. Для остановки нажми Ctrl+C")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Обрезка кадра (точно такая же, как при сборе датасета и обучении)
            crop_frame = frame[25:80, 0:160]
            rgb_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2RGB)
            
            # Превращаем картинку в тензор PyTorch
            input_tensor = transform(rgb_frame).unsqueeze(0).to(device)

            # Нейросеть предсказывает команды
            with torch.no_grad():
                predictions = model(input_tensor).squeeze(0).numpy()
                print(f"Предсказание сети -> Y(газ): {predictions[0]:.2f}, X(стрейф): {predictions[1]:.2f}, R(поворот): {predictions[2]:.2f}")

            # Получаем сырые предсказания из сети (например, 0.13)
            pred_y = predictions[0]
            pred_x = predictions[1]
            pred_r = predictions[2]

            # 1. УМНОЖАЕМ значения, чтобы дать моторам больше тока
            SPEED_MULTIPLIER = 4.0  # Подбери это число (попробуй 3.0, 4.0 или 5.0)

            pred_y = pred_y * SPEED_MULTIPLIER
            pred_x = pred_x * SPEED_MULTIPLIER
            pred_r = pred_r * SPEED_MULTIPLIER

            # 2. ОГРАНИЧИВАЕМ значения, чтобы они не вышли за пределы [-1.0, 1.0]
            # Функция clip не даст отправить на моторы больше 100% мощности
            import numpy as np # добавь в начало файла, если еще нет
            pred_y = np.clip(pred_y, -1.0, 1.0)
            pred_x = np.clip(pred_x, -1.0, 1.0)
            pred_r = np.clip(pred_r, -1.0, 1.0)

            # Дальше отправляешь эти усиленные значения в свою функцию drive_mecanum()

            # Отправляем предсказания на моторы
            drive_mecanum(pred_x, pred_y, pred_r)
            
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n🛑 Остановка робота...")
    finally:
        drive_mecanum(0, 0, 0)
        lift_stop()
        cap.release()

if __name__ == "__main__":
    main()
