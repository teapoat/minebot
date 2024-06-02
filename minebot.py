import os
import re
import time
from telegram import Bot
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение токена и chat_id из переменных окружения
TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LOG_FILE_PATH = '/home/ubuntu/minecraft/screenlog.0'

# Список ключевых слов для отправки сообщений
KEYWORDS = re.compile(
    r'died|was|walked into|drowned|experienced kinetic energy|blew up|hit the ground|fell|went|burned to death|was burnt|tried to swim|discovered the floor|froze to death|starved to|suffocated in a wall|t want to live|withered away|has made the advancement|has completed the challenge|has reached the goal'
)

# Телеграм-бот
bot = Bot(token=TOKEN)

# Хранилище последних строк
last_lines = ['', '']

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = open(file_path, 'r')
        self.file.seek(0, os.SEEK_END)  # Перейти в конец файла

    def on_modified(self, event):
        if event.src_path == self.file_path:
            self.check_new_lines()

    def check_new_lines(self):
        global last_lines

        lines = self.file.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('>'):
                continue

            # Удаляем символы '[K' в начале строки
            line = line.replace('[K', '')

            # Проверяем, содержит ли строка одно из ключевых слов
            if KEYWORDS.search(line):
                # Очистка мусора из строки
                clean_line = re.sub(r'\[[0-9]+m|\[[0-9]+;[0-9]+m', '', line)
                clean_line = clean_line.strip()

                if clean_line != last_lines[-1] and clean_line != last_lines[-2]:
                    bot.send_message(chat_id=CHAT_ID, text=clean_line)
                    last_lines = [last_lines[-1], clean_line]

if __name__ == "__main__":
    event_handler = LogFileHandler(LOG_FILE_PATH)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(LOG_FILE_PATH), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

