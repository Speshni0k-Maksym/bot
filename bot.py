import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    print("Error: bot token not found")
else:
    print("Bot token loaded successfully")


API_BASE_URL = "http://127.0.0.1:8000"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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

async def api_request(method: str, endpoint: str, data: dict = None):
    url = f"{API_BASE_URL}{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    return await response.json()
            elif method == "PUT":
                async with session.put(url, json=data) as response:
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url) as response:
                    return await response.json()
        except Exception as e:
            print(f"API Error: {e}")
            return None

@dp.message(F.text == "Почати")
async def process_start_button(message: Message):
    await cmd_start(message)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    
    await api_request("POST", f"/users/{user_id}/tasks", {
        "text": "Привітальна задача",
        "status": "pending"
    })
    
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
    
    tasks = await api_request("GET", f"/users/{user_id}/tasks")
    
    if not tasks:
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
    
    if action in ["mark_completed", "mark_pending"]:
        new_status = "completed" if action == "mark_completed" else "pending"
        result = await api_request("PUT", f"/users/{user_id}/tasks/{task_id}", {
            "status": new_status
        })
        
        if result:
            await callback.answer(f"Задачу відмічено як {'виконану' if new_status == 'completed' else 'в процесі'}!")
            
            task = result["task"]
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
    
    elif action == "delete":
        result = await api_request("DELETE", f"/users/{user_id}/tasks/{task_id}")
        
        if result:
            await callback.answer("Задачу видалено!")
            
            tasks = await api_request("GET", f"/users/{user_id}/tasks")
            
            if tasks:
                await show_tasks_list(callback.from_user.id, callback.message)
            else:
                await callback.message.edit_text(
                    "У вас немає задач. Додайте нову задачу!",
                    reply_markup=get_back_to_main_keyboard()
                )

async def show_tasks_list(user_id: int, message: types.Message):
    user_id = str(user_id)
    tasks = await api_request("GET", f"/users/{user_id}/tasks")
    
    if not tasks:
        await message.edit_text(
            "У вас немає задач. Додайте нову задачу!",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    keyboard = []
    for i, task in enumerate(tasks):
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
    
    new_text = f"Ваші задачі ({len(tasks)}):"
    new_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        await message.edit_text(new_text, reply_markup=new_markup)
    except Exception:
        pass

@dp.callback_query(F.data.startswith("view_task:"))
async def view_task(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    task_id = int(callback.data.split(":")[1])
    
    task = await api_request("GET", f"/users/{user_id}/tasks/{task_id}")
    
    if task:
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
    
    result = await api_request("POST", f"/users/{user_id}/tasks", {
        "text": message.text,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    if result:
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