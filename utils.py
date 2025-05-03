import os, json, sys, datetime, random, asyncio

script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))



def show_results(amount: int, success: int, failed: int):
    print("\n\nРезультаты выполнения:")
    print("===================================")
    print(f"Всего пользователей: {amount}")
    print(f"Из них добавлено успешно: {success}")
    print(f"Не удалось добавить: {failed}.")


async def antiflood():
    delay = random.uniform(1, 10)
    await asyncio.sleep(delay)


def rewrite_users(users: list, user: str):
    users.remove(f"@{user}")
    with open("users.txt", "w", encoding="utf-8") as f:
        for user in users:
            f.write(f"@{user}\n")


def get_users():
    with open(f"{script_dir}\\users.txt", "r", encoding="utf-8") as f:
        users = [line.strip().lstrip("@") for line in f if line.strip()]
    return users


def get_link(string):
    while True:
        link = input(string)
        if link.startswith("https://t.me/"):
            return link
        print("Некорректная ссылка. Попробуйте снова.")


def create_config():
    config: dict = read_config()
    api_id = config.get("api_id", None)
    api_hash = config.get("api_hash", None)
    if not api_id or not api_hash:
        print("Необходимо зарегистрировать клиент в Telegram.")
        print("Для этого перейдите по ссылке: https://my.telegram.org/")
        config["api_id"] = input("Введите api_id: ")
        config["api_hash"] = input("Введите api_hash: ")
        save_config(config)


def read_config():
    with open(f'{script_dir}\\config.json', 'r') as f:
        data = f.read()
        config = json.loads(data)
    return config

def save_config(config):
    with open(f'{script_dir}\\config.json', 'w') as f:
        data = f.write(json.dumps(config))
        config = json.dumps(data)


def program_over():
    print("\nВыполнение окончено.")
    while True:
        pass


class ProgressBar:
    def __init__(self, total, length=40, fill='█', empty='-', prefix=f'{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')} Прогресс'):
        """
        :param total: Общее количество шагов
        :param length: Длина прогресс-бара в символах
        :param fill: Символ заполнения
        :param empty: Символ пустого места
        :param prefix: Текст перед прогресс-баром
        :param suffix: Текст после прогресс-бара
        """
        self.total = total
        self.length = length
        self.fill = fill
        self.empty = empty
        self.prefix = prefix
        self.current = 0

    def next(self, string=None):
        """
        Увеличивает прогресс на 1 шаг и обновляет отображение.
        :param string: Дополнительный текст, отображаемый перед прогресс-баром
        """
        self.current += 1
        self._print_bar(string)

    def end(self, string=None):
        """Завершает прогресс-бар."""
        self.current = self.total
        self._print_bar(string)

    def _print_bar(self, string=None):
        percent = self.current / self.total
        filled_length = int(self.length * percent)
        bar = self.fill * filled_length + self.empty * (self.length - filled_length)
        text = f'\r{self.prefix}: |{bar}| {int(percent * 100)}%'
        if string:
            text += f' - {string}'
        sys.stdout.write(text)
        sys.stdout.flush()

        if self.current == self.total:
            print()

    def reset(self):
        """Сбрасывает прогресс."""
        self.current = 0