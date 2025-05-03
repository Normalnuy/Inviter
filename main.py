import datetime, asyncio
from utils import *

from telethon import TelegramClient
from telethon.tl.functions.messages import AddChatUserRequest, GetHistoryRequest

from telethon.errors import FloodWaitError, ChatAdminRequiredError, ChatIdInvalidError, InputUserDeactivatedError
from telethon.errors import PeerIdInvalidError, UsersTooMuchError, UserAlreadyParticipantError, UserIdInvalidError
from telethon.errors import UserNotMutualContactError, UserPrivacyRestrictedError, PeerFloodError, UserIsBlockedError


async def main():
    try:
        create_config()
        await create_clients()

        if os.path.exists(f"{script_dir}\\users.txt"):
            print("Файл с пользователями уже существует.")
            start_invite = get_user_input("Хотите начать процесс приглашения? (y/n): ", {"y", "n"})
            
            if start_invite == "n":
                os.remove(f"{script_dir}\\users.txt")
                amount, success, failed = await handle_parsing_and_inviting()
            else:
                invite_link = get_link("Введите ссылку на группу для добавления участников: ")
                amount, success, failed = await invite_users(invite_link)
        else:
            amount, success, failed = await handle_parsing_and_inviting()

        show_results(amount, success, failed)
    except Exception as e:
        print('\n' + str(e))
    finally:
        program_over()



def get_user_input(prompt: str, valid_inputs: set) -> str:
    while (user_input := input(prompt).lower()) not in valid_inputs:
        print(f"Некорректный ввод. Введите {' или '.join(valid_inputs)}.")
    return user_input


async def handle_parsing_and_inviting():
    parsing_link = get_link("Введите ссылку на группу для парсинга участников: ")
    await parsing(parsing_link)
    invite_link = get_link("Введите ссылку на группу для добавления участников: ")
    amount, success, failed = await invite_users(invite_link)
    return amount, success, failed
    


async def parsing(parsing_link: str):
    config = read_config()
    phones = config.get("phones", [])
    client = await check_client(config, phones[0])
    
    group_name = parsing_link.split("https://t.me/")[-1]
    if group_name.startswith("+"):
        group_name = f"https://t.me/joinchat/{group_name[1:]}"
    channel = await client.get_entity(group_name)
    
    users = []
    all_participants = await get_all_participants(client, channel)
    if len(all_participants) != 0:
        for user in all_participants:
            users.append(user.username)
    else:
        print("\nПоиск пользователей не сработал.")
        print("Начинаем поиск по сообщениям за последние 7 дней.")
        print("Это может занять больше времени.")
        
        messages = await fetch_messages(client, group_name)
        print(f"Найдено {len(messages)} сообщений за последние 7 дней.")
        
        users = await get_usernames(client, messages)
        print(f"Найдено {len(users)} юзернеймов.")
    
    with open("users.txt", "w", encoding="utf-8") as f:
        for user in users:
            f.write(f"@{user}\n")
    
    await client.disconnect()
    print(f"\nПарсинг завершен. Найдено {len(users)} пользователей.")


async def fetch_messages(client: TelegramClient, group_name: str):
    try:
        if group_name.startswith("+"):
            group_name = f"https://t.me/joinchat/{group_name[1:]}"
        entity = await client.get_entity(group_name)

        date_limit = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        
        all_messages = []
        offset_id = 0
        limit = 100
        
        print(f"Получение сообщений из группы {group_name} за последние 7 дней.")
        print("За 1 запрос обрабатывается 100 сообщений, будет несколько запросов.")
        print("Это может занять некоторое время.")
        print("Пожалуйста, подождите...")
        while True:
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))

            messages = history.messages
            if not messages:
                break
            
            messages_bar = ProgressBar(len(messages), prefix="Прогресс")
            for message in messages:
                messages_bar.next(f"Получение сообщений. | {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
                if message.date < date_limit:
                    messages_bar.end("Получение сообщений. | Завершено. | " + datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
                    return all_messages
                all_messages.append(message.to_dict())
            offset_id = messages[-1].id
    except Exception as e:
        print(f"\nОшибка при получении сообщений: {e}")
        return []


async def get_sender_from_dict(client: TelegramClient, message_dict: dict):
    while True:
        if message_dict is None:
            print("Сообщение отсутствует. Пропуск.")
            return None

        if 'from_id' in message_dict and message_dict['from_id'] is not None:
            if '_' in message_dict['from_id'] and message_dict['from_id']['_'] == 'PeerUser':
                user_id = message_dict['from_id']['user_id']
                sender = await client.get_entity(user_id)
                return sender
            else:
                return None
        else:
            return None


async def get_usernames(client: TelegramClient, all_messages: list):
    print("Получение юзернеймов из сообщений.")
    unique_usernames = set()

    users_bar = ProgressBar(len(all_messages), prefix="Прогресс")
    for message_dict in all_messages:
        users_bar.next(f"Получение юзернеймов. | {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        
        try:
            sender = await get_sender_from_dict(client, message_dict)
            if sender is None: continue
        except FloodWaitError as e:
            for remaining in range(e.seconds, 0, -1):
                sys.stdout.write(f"\rСлишком много запросов. Подождите {remaining} секунд.")
                sys.stdout.flush()
                await asyncio.sleep(1)
            sys.stdout.write("\r" + " " * 50 + "\r")
        
        if sender and sender.username and not sender.bot:
            unique_usernames.add(sender.username)
            
    return unique_usernames


async def get_all_participants(client: TelegramClient, channel):
    print("Получение всех участников группы...")
    
    all_participants = []
    async for user in client.iter_participants(channel):
        if user.username and not user.bot:
            all_participants.append(user)
    return all_participants


async def invite_users(invite_link: str):
    config = read_config()
    phones = config.get("phones", [])
    
    group_name = invite_link.split("https://t.me/")[-1]
    if group_name.startswith("+"):
        group_name = f"https://t.me/joinchat/{group_name[1:]}"
    
    current_client_index = 0
    current_user_index = 0
    
    users = get_users()
    amount = len(users)
    bar = ProgressBar(amount, prefix="Прогресс")
    
    while current_client_index < len(phones):
        phone = phones[current_client_index]
        client = await check_client(config, phone)
        channel = await client.get_entity(group_name)
        
        success = 0
        failed = 0
    
        for i in range(current_user_index, amount):
            user = users[i]
            bar.next(f"Добавление пользователя. | {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
            try:
                await client(AddChatUserRequest(
                    channel.id,
                    user,
                    fwd_limit=0
                ))
                success += 1
                await antiflood()
            except (FloodWaitError, PeerFloodError):
                await handle_flood_error(client, phone)
                current_client_index += 1
                current_user_index = i
                break
            except (InputUserDeactivatedError, PeerIdInvalidError, UserIdInvalidError,
                    UserNotMutualContactError, UserPrivacyRestrictedError, UserIsBlockedError):
                failed += 1
                await antiflood()
            except UserAlreadyParticipantError:
                success += 1
            except (ChatAdminRequiredError, UsersTooMuchError) as e:
                await handle_critical_error(client, phone, group_name, e)
                return amount, success, amount - success
            except Exception:
                await handle_flood_error(client, phone)
                current_client_index += 1
                current_user_index = i
                break     
    
    return amount, success, amount - success


async def handle_flood_error(client: TelegramClient, phone: dict):
    me = await client.get_me()
    print(f"\nСлишком много запросов для {me.username} (phone: {phone['phone']})")
    print("Переход на следующий аккаунт.")
    await client.disconnect()

async def handle_critical_error(client: TelegramClient, phone: dict, group_name, error):
    if isinstance(error, ChatAdminRequiredError):
        print(f"\nКлиент: {phone['session_name']} не является администратором в группе {group_name}.")
    elif isinstance(error, UsersTooMuchError):
        print(f"\nОграничение количества пользователей в группе.")
    elif isinstance(error, ChatIdInvalidError):
        print(f"\nНекорректная ссылка на группу {group_name}.")
    await client.disconnect()


async def check_client(config: dict, phone: dict):
    while True:
        create = not os.path.exists(f'sessions\\{phone["session_name"]}.session')
        client = TelegramClient(f'sessions\\{phone['session_name']}.session', int(config['api_id']), config['api_hash'], 
                                    system_version="4.16.30-vxCUSTOM",
                                    device_model='Windows 11 Pro',
                                    app_version='9.1.2')
        if create:
            await client.start(phone=phone['phone'], password=phone['password'],
                code_callback=lambda: input(f"\nВведите код (phone: {phone['phone']}): "))
        else: await client.connect()
 
        if not await client.is_user_authorized():
            await client.disconnect()
            os.remove(f'sessions\\{phone["session_name"]}.session')
            continue
        
        break
    return client


async def create_clients():
    config = read_config()
    phones = config.get("phones", [])
        
    if len(phones) == 0:
        print("Не указаны данные в конфигурации.")
        return False

    sessions_bar = ProgressBar(len(phones), prefix="Прогресс")
    for phone in phones:
        sessions_bar.next(f"Анализируем валидность сессий. | {phone['session_name']} | {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        client = await check_client(config, phone)
        if client: await client.disconnect()
    
    print("Все сессии авторизованы.")
    
    
    
    
    
    
    
if __name__ == "__main__":
    asyncio.run(main())