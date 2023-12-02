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
    keyboard.add(InlineKeyboardButton("Add Task", callback_data='1'))
    keyboard.add(InlineKeyboardButton("Task List", callback_data='2'))
    keyboard.add(InlineKeyboardButton("Delete Task", callback_data='3'))
    keyboard.add(InlineKeyboardButton("Roll the Dice 🎲", callback_data='4'))
    keyboard.add(InlineKeyboardButton("Support", callback_data='support'))
    await message.answer('Choose an action:', reply_markup=keyboard)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'support')
async def support_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await bot.send_message(callback_query.from_user.id, "If you have comments, errors, or ideas for the bot, "
                                                      "you can write them below. If you want to go back, "
                                                      "use /start.")
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

    await bot.send_message(OWNER_CHAT_ID, f"Support from user {user_info}:\n\n{support_text}",
                           parse_mode=types.ParseMode.MARKDOWN)

    await bot.send_message(user_id, "Your message has been sent to support. Thank you!")

    if not user_username:
        await bot.send_message(OWNER_CHAT_ID, "Unfortunately, the user has not set a username.")

    await state.finish()
    await start(message)


OWNER_CHAT_ID = '5956033204'


@dp.callback_query_handler(lambda callback_query: callback_query.data in ['1', '2', '3'])
async def process_callback(callback_query: types.CallbackQuery):
    global state
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == '1':
        state = 'add'
        await bot.send_message(callback_query.from_user.id, "Enter the task:")
    elif callback_query.data == '2':
        task_list = "\n".join(
            [f"{i + 1}) {task['text']} (Priority: {task['priority']}, Time: {task['time']})" for i, task in enumerate(tasks)])
        await bot.send_message(callback_query.from_user.id, f"Task List:\n{task_list}")
        await start(types.Message(chat=callback_query.message.chat))
    elif callback_query.data == '3':
        state = 'delete_by_number'
        task_list = "\n".join(
            [f"{i + 1}) {task['text']} (Priority: {task['priority']}, Time: {task['time']})" for i, task in enumerate(tasks)])
        await bot.send_message(callback_query.from_user.id, f"Choose the task number to delete:\n{task_list}")


@dp.message_handler()
async def handle_message(message: types.Message):
    global state, task_text, priority, notification_time
    if state == 'add':
        task_text = message.text
        await message.reply("Enter the task priority (from 1 to 3):")
        state = 'priority'
    elif state == 'priority':
        priority = message.text
        await message.reply("Enter the notification time (format: HH:MM or in seconds):")
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
                f"Task '{task_text}' added with priority '{priority}' and notification time '{notification_time}'.")
            state = ''
            await start(message)
            await schedule_task(notification_time, task_text, priority, message.from_user.id)
        except ValueError:
            await message.reply("Invalid time format. Enter the time in the format HH:MM or in seconds.")
            state = 'time'
    elif state == 'delete_by_number':
        try:
            task_number = int(message.text)
            if 1 <= task_number <= len(tasks):
                deleted_task = tasks.pop(task_number - 1)
                await message.reply(f"Task '{deleted_task['text']}' deleted.")
            else:
                await message.reply("Invalid task number.")
            state = ''
            await start(message)
        except ValueError:
            await message.reply("Enter a valid task number.")
            state = 'delete_by_number'


async def schedule_task(notification_time, task_text, priority, user_id):
    now = datetime.now()
    scheduled_time = datetime.combine(now.date(), notification_time)

    if scheduled_time < now:
        scheduled_time += timedelta(days=1)

    delay = (scheduled_time - now).total_seconds()
    await asyncio.sleep(delay)

    if task_text in [task["text"] for task in tasks]:
        await bot.send_message(user_id, f"It's time to complete the task: {task_text}\n(Priority: {priority})")

        keyboard = InlineKeyboardMarkup()
        task_id = [task["id"] for task in tasks if task["text"] == task_text][0]
        keyboard.add(InlineKeyboardButton("Delete Task", callback_data=f'delete_{task_id}'))

        await bot.send_message(user_id, 'Choose an action:', reply_markup=keyboard)

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
        await bot.send_message(callback_query.from_user.id, f"Task '{task['text']}' deleted.")

        await send_random_gif(callback_query.from_user.id)
    else:
        await bot.send_message(callback_query.from_user.id, "Error deleting the task.")

    await start(types.Message(chat=callback_query.message.chat))

if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, on_shutdown=lambda dp: dp.storage.close())
    asyncio.run(dp.storage.wait_closed())
