import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
from datetime import datetime

API_TOKEN = "8571820554:AAFuvPpbdK4jewtTMvaWon4ScSn5r4A_fIE"
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = "tasks.json"

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tasks(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

user_tasks = load_tasks()

def get_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Почати")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Додати задачу", callback_data="add_task")],
        [InlineKeyboardButton(text="Мої задачі", callback_data="list_tasks")],
        [InlineKeyboardButton(text="Допомога", callback_data="help")]
    ])
    return keyboard

def get_task_actions_keyboard(task_id: str, current_status: str):
    status_text = "Виконано" if current_status == "completed" else "В процесі"
    status_callback = "mark_pending" if current_status == "completed" else "mark_completed"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Статус: {status_text}", callback_data=f"{status_callback}:{task_id}")],
        [InlineKeyboardButton(text="Видалити", callback_data=f"delete:{task_id}")],
        [InlineKeyboardButton(text="Назад до списку", callback_data="list_tasks")]
    ])
    return keyboard

def get_back_to_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Головне меню", callback_data="main_menu")]
    ])
    return keyboard

@dp.message(F.text == "Почати")
async def process_start_button(message: Message):
    await cmd_start(message)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_tasks:
        user_tasks[user_id] = []
        save_tasks(user_tasks)
    
    welcome_text = (
        "Вітаю! Я бот для управління задачами.\n\n"
        "За допомогою мене ви можете:\n"
        "• Додавати нові задачі\n"
        "• Переглядати список задач\n"
        "• Змінювати статус задач\n"
        "• Видаляти задачі\n\n"
        "Оберіть дію з меню нижче:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Доступні команди:\n\n"
        "/start - Запустити бота\n"
        "/help - Показати доступні команди\n"
        "/tasks - Переглянути всі задачі\n\n"
        "Ви також можете використовувати кнопки меню для навігації."
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

@dp.message(Command("tasks"))
async def cmd_tasks(message: Message):
    await show_tasks_list(message.from_user.id, message)

@dp.callback_query(F.data == "add_task")
async def process_add_task(callback: CallbackQuery):
    await callback.message.edit_text(
        "Введіть текст нової задачі (або надішліть /cancel для скасування):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Скасувати", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "list_tasks")
async def process_list_tasks(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in user_tasks or not user_tasks[user_id]:
        await callback.message.edit_text(
            "У вас немає задач. Додайте нову задачу!",
            reply_markup=get_back_to_main_keyboard()
        )
    else:
        await show_tasks_list(callback.from_user.id, callback.message)
    
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Головне меню. Оберіть дію:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "help")
async def process_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "Допомога по боту:\n\n"
        "• Щоб додати задачу, натисніть 'Додати задачу'\n"
        "• Щоб переглянути задачі, натисніть 'Мої задачі'\n"
        "• Клікніть на задачу, щоб змінити її статус або видалити\n"
        "• Задачі зберігаються автоматично",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Головне меню", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith(("mark_completed:", "mark_pending:", "delete:")))
async def process_task_action(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    action, task_id = callback.data.split(":")
    task_id = int(task_id)
    
    if user_id in user_tasks and 0 <= task_id < len(user_tasks[user_id]):
        task = user_tasks[user_id][task_id]
        
        if action == "mark_completed":
            task["status"] = "completed"
            task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            await callback.answer("Задачу відмічено як виконану!")
            
        elif action == "mark_pending":
            task["status"] = "pending"
            task.pop("completed_at", None)
            await callback.answer("Задачу відмічено як в процесі!")
            
        elif action == "delete":
            user_tasks[user_id].pop(task_id)
            save_tasks(user_tasks)
            await callback.answer("Задачу видалено!")
            
            if user_tasks[user_id]:
                await show_tasks_list(callback.from_user.id, callback.message)
            else:
                await callback.message.edit_text(
                    "У вас немає задач. Додайте нову задачу!",
                    reply_markup=get_back_to_main_keyboard()
                )
            return
        
        save_tasks(user_tasks)
        
        status_text = "Виконано" if task["status"] == "completed" else "В процесі"
        
        task_text = (
            f"Задача #{task_id + 1}\n\n"
            f"{task['text']}\n\n"
            f"Статус: {status_text}\n"
            f"Створено: {task['created_at']}"
        )
        
        if "completed_at" in task:
            task_text += f"\nВиконано: {task['completed_at']}"
        
        await callback.message.edit_text(
            task_text,
            reply_markup=get_task_actions_keyboard(task_id, task["status"])
        )

async def show_tasks_list(user_id: int, message: types.Message):
    user_id = str(user_id)
    
    keyboard = []
    for i, task in enumerate(user_tasks[user_id]):
        task_text = task["text"]
        if len(task_text) > 30:
            task_text = task_text[:27] + "..."
        
        button = InlineKeyboardButton(
            text=f"{task_text}",
            callback_data=f"view_task:{i}"
        )
        keyboard.append([button])
    
    keyboard.append([
        InlineKeyboardButton(text="Додати задачу", callback_data="add_task"),
        InlineKeyboardButton(text="Головне меню", callback_data="main_menu")
    ])
    
    new_text = f"Ваші задачі ({len(user_tasks[user_id])}):"
    new_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        await message.edit_text(new_text, reply_markup=new_markup)
    except Exception:
        pass

@dp.callback_query(F.data.startswith("view_task:"))
async def view_task(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    
    if user_id in user_tasks and 0 <= task_id < len(user_tasks[user_id]):
        task = user_tasks[user_id][task_id]
        
        status_text = "Виконано" if task["status"] == "completed" else "В процесі"
        
        task_text = (
            f"Задача #{task_id + 1}\n\n"
            f"{task['text']}\n\n"
            f"Статус: {status_text}\n"
            f"Створено: {task['created_at']}"
        )
        
        if "completed_at" in task:
            task_text += f"\nВиконано: {task['completed_at']}"
        
        await callback.message.edit_text(
            task_text,
            reply_markup=get_task_actions_keyboard(task_id, task["status"])
        )
    
    await callback.answer()

@dp.message(F.text)
async def handle_text(message: Message):
    if message.text.startswith('/'):
        return
    
    user_id = str(message.from_user.id)
    
    if user_id not in user_tasks:
        user_tasks[user_id] = []
    
    new_task = {
        "text": message.text,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    user_tasks[user_id].append(new_task)
    save_tasks(user_tasks)
    
    await message.answer(
        f"Задачу додано!\n\n{message.text}",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    await message.answer(
        "Дію скасовано. Повертаємось до головного меню.",
        reply_markup=get_main_keyboard()
    )

async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)

asyncio.run(main())