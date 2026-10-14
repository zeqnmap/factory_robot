import os
import asyncio
from dotenv import load_dotenv
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram import Bot, Dispatcher, types


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_cpu_temp():
    """CPU temperature"""
    res = os.popen('vcgencmd measure_temp').readline()
    return res.replace("temp=","").replace("'C\n","")

def get_uptime():
    """system uptime"""
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}min"
    else:
        return f"{hours}h {minutes}min"

def get_disk_usage():
    """free space on the SD card"""
    stat = os.statvfs('/')
    free = stat.f_bavail * stat.f_frsize
    total = stat.f_blocks * stat.f_frsize
    free_gb = free / (1024**3)
    total_gb = total / (1024**3)
    percent = (free / total) * 100
    return f"💾 Free: {free_gb:.1f} GB out of {total_gb:.1f} GB ({percent:.0f}% free)"

def get_ram_usage():
    """RAM usage"""
    res = os.popen('free -h').readlines()
    parts = res[1].split()
    total = parts[1]
    used = parts[2]
    return f"🧠 RAM usage: {used} out of {total}"

async def set_commands():
    commands = [
        BotCommand(command="start", description="start the bot and view commands"),
        BotCommand(command="temp", description="CPU temperature"),
        BotCommand(command="ping", description="check connection latency"),
        BotCommand(command="uptime", description="Raspberry Pi uptime"),
        BotCommand(command="disk", description="check free space on the SD card"),
        BotCommand(command="ram", description="check RAM usage"),
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "01001000 01101001"
    )

@dp.message(Command("temp"))
async def cmd_status(message: types.Message):
    temp = get_cpu_temp()
    status_text = f"🌡CPU temperature: {temp}°C\n\n"
    try:
        temp_float = float(temp)
        if temp_float > 75:
            status_text += "⛔️ CRITICALLY temperature!"
        elif temp_float > 60:
            status_text += "⚠️ high temperature"
        else:
            status_text += "✅ optimal cooling"
    except:
        status_text += "⚠️ cant't determine"
    await message.answer(status_text)

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("🤖")

@dp.message(Command("uptime"))
async def cmd_uptime(message: types.Message):
    uptime_str = get_uptime()
    await message.answer(f"⏱️ system uptime: {uptime_str}")

@dp.message(Command("disk"))
async def cmd_disk(message: types.Message):
    disk_info = get_disk_usage()
    await message.answer(disk_info)

@dp.message(Command("ram"))
async def cmd_ram(message: types.Message):
    ram_info = get_ram_usage()
    await message.answer(ram_info)

async def main():
    print("polling...", flush=True)
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("❌ Interrupted", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()