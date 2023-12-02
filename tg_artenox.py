import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

tasks = []
state = ''
task_text = ''
priority = ''
notification_time = ''

bot = Bot(token='6627524866:AAFEXPYuJRwRs2c2B_CYeYHsBgIWVgLaBqM')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.callback_query_handler(lambda callback_query: callback_query.data == '4')
async def roll_dice_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    await bot.send_dice(callback_query.from_user.id)

    await asyncio.sleep(3)

    await start(types.Message(chat=callback_query.message.chat))


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Добавить задачу", callback_data='1'))
    keyboard.add(InlineKeyboardButton("Список задач", callback_data='2'))
    keyboard.add(InlineKeyboardButton("Удаление задач", callback_data='3'))
    keyboard.add(InlineKeyboardButton("Бросить кубик 🎲", callback_data='4'))
    keyboard.add(InlineKeyboardButton("Поддержка", callback_data='support'))
    await message.answer('Выберите действие:', reply_markup=keyboard)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'support')
async def support_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await bot.send_message(callback_query.from_user.id, "Если у вас есть замечания, ошибки или идеи для бота, "
                                                      "вы можете написать текстом ниже. Если хотите вернуться назад, "
                                                      "используйте /start.")
    await state.set_state('support')


@dp.message_handler(state='support')
async def handle_support_message(message: types.Message, state: FSMContext):
    if message.text.lower() == '/start':
        await state.finish()
        await start(message)
        return

    user_username = message.from_user.username
    user_id = message.from_user.id
    support_text = message.text

    user_info = f"`@{user_username}`" if user_username else f"`ID: {user_id}`"

    await bot.send_message(OWNER_CHAT_ID, f"Поддержка от пользователя {user_info}:\n\n{support_text}",
                           parse_mode=types.ParseMode.MARKDOWN)

    await bot.send_message(user_id, "Ваше сообщение отправлено в поддержку. Спасибо!")

    if not user_username:
        await bot.send_message(OWNER_CHAT_ID, "К сожалению, пользователь не установил юзернейм. ")

    await state.finish()
    await start(message)


OWNER_CHAT_ID = '5956033204'


@dp.callback_query_handler(lambda callback_query: callback_query.data in ['1', '2', '3'])
async def process_callback(callback_query: types.CallbackQuery):
    global state
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == '1':
        state = 'add'
        await bot.send_message(callback_query.from_user.id, "Введите задачу:")
    elif callback_query.data == '2':
        task_list = "\n".join(
            [f"{i + 1}) {task['text']} (Приоритет: {task['priority']}, Время: {task['time']})" for i, task in enumerate(tasks)])
        await bot.send_message(callback_query.from_user.id, f"Список задач:\n{task_list}")
        await start(types.Message(chat=callback_query.message.chat))
    elif callback_query.data == '3':
        state = 'delete_by_number'
        task_list = "\n".join(
            [f"{i + 1}) {task['text']} (Приоритет: {task['priority']}, Время: {task['time']})" for i, task in enumerate(tasks)])
        await bot.send_message(callback_query.from_user.id, f"Выберите номер задачи для удаления:\n{task_list}")


@dp.message_handler()
async def handle_message(message: types.Message):
    global state, task_text, priority, notification_time
    if state == 'add':
        task_text = message.text
        await message.reply("Введите приоритет задачи (от 1 до 3):")
        state = 'priority'
    elif state == 'priority':
        priority = message.text
        await message.reply("Введите время для уведомления (формат: HH:MM или в секундах):")
        state = 'time'
    elif state == 'time':
        try:
            if ':' in message.text:
                notification_time = datetime.strptime(message.text, '%H:%M').time()
            else:
                seconds = int(message.text)
                notification_time = (datetime.now() + timedelta(seconds=seconds)).time()
            tasks.append({"id": len(tasks) + 1, "text": task_text, "priority": priority, "time": notification_time})
            await message.reply(
                f"Задача '{task_text}' добавлена с приоритетом '{priority}' и временем уведомления '{notification_time}'.")
            state = ''
            await start(message)
            await schedule_task(notification_time, task_text, priority, message.from_user.id)
        except ValueError:
            await message.reply("Неверный формат времени. Введите время в формате HH:MM или в секундах.")
            state = 'time'
    elif state == 'delete_by_number':
        try:
            task_number = int(message.text)
            if 1 <= task_number <= len(tasks):
                deleted_task = tasks.pop(task_number - 1)
                await message.reply(f"Задача '{deleted_task['text']}' удалена.")
            else:
                await message.reply("Неверный номер задачи.")
            state = ''
            await start(message)
        except ValueError:
            await message.reply("Введите корректный номер задачи.")
            state = 'delete_by_number'


async def schedule_task(notification_time, task_text, priority, user_id):
    now = datetime.now()
    scheduled_time = datetime.combine(now.date(), notification_time)

    if scheduled_time < now:
        scheduled_time += timedelta(days=1)

    delay = (scheduled_time - now).total_seconds()
    await asyncio.sleep(delay)

    if task_text in [task["text"] for task in tasks]:
        await bot.send_message(user_id, f"Пора выполнить задачу: {task_text}\n(Приоритет: {priority})")

        keyboard = InlineKeyboardMarkup()
        task_id = [task["id"] for task in tasks if task["text"] == task_text][0]
        keyboard.add(InlineKeyboardButton("Удалить задачу", callback_data=f'delete_{task_id}'))

        await bot.send_message(user_id, 'Выберите действие:', reply_markup=keyboard)

gif_links = [
    "https://i.gifer.com/3QeI.gif",
    "https://i.gifer.com/ImPS.gif",
    "https://i.gifer.com/IEa2.gif",
    "https://i.gifer.com/XcfJ.gif",
    "https://i.gifer.com/1uhE.gif",
    "https://i.gifer.com/Tvnq.gif",
    "https://i.gifer.com/3QeI.gif",
    "https://i.gifer.com/Wtya.gif",
    "https://i.gifer.com/VDRf.gif",
    "https://i.gifer.com/fyCM.gif",
    "https://i.gifer.com/XO6O.gif",
    "https://i.gifer.com/Qi5m.gif",
    "https://i.gifer.com/TfGL.gif",
    "https://i.gifer.com/Xax4.gif",
    "https://i.gifer.com/Xbah.gif",
]


async def send_random_gif(user_id):
    random_gif_url = random.choice(gif_links)
    await bot.send_message(user_id, random_gif_url)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('delete_'))
async def delete_task_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    task_id = int(callback_query.data.split('_')[1])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if task:
        tasks.remove(task)
        await bot.send_message(callback_query.from_user.id, f"Задача '{task['text']}' удалена.")

        await send_random_gif(callback_query.from_user.id)
    else:
        await bot.send_message(callback_query.from_user.id, "Ошибка при удалении задачи.")

    await start(types.Message(chat=callback_query.message.chat))

if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, on_shutdown=lambda dp: dp.storage.close())
    asyncio.run(dp.storage.wait_closed())
