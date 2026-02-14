import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

# Конфигурация
BOT_TOKEN = "8026414941:AAEcvRAwxeJdGr5Hga-T6ljAgcnsUZuIVXY"
ADMIN_IDS = [6838204402, 8003390315]  # ID администраторов
PRICE_PER_HOUR = 30  # Рублей за час
LOLZ_PAYMENT_URL = "https://lolz.live/payment/balance-transfer?user_id=9414807&hold=1&_noRedirect=1"

# Список читов с серверами
CHEATS = {
    "nursultan": {"servers": 2, "online": [False, False], "parsec_links": ["", ""]},
    "expensive": {"servers": 2, "online": [False, False], "parsec_links": ["", ""]},
    "wexside": {"servers": 1, "online": [False], "parsec_links": [""]},
    "catlavan": {"servers": 1, "online": [False], "parsec_links": [""]},
    "energy": {"servers": 1, "online": [False], "parsec_links": [""]},
    "celestial": {"servers": 1, "online": [False], "parsec_links": [""]},
    "excelent": {"servers": 1, "online": [False], "parsec_links": [""]},
    "wild": {"servers": 1, "online": [False], "parsec_links": [""]},
    "everlast": {"servers": 1, "online": [False], "parsec_links": [""]}
}

# FSM States
class BuyStates(StatesGroup):
    choosing_cheat = State()
    choosing_tariff = State()
    custom_hours = State()
    choosing_payment = State()
    lolz_payment = State()

class AdminStates(StatesGroup):
    choosing_cheat_to_host = State()
    choosing_server_number = State()
    entering_parsec_link = State()

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# База данных
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, cheat TEXT, 
                  hours INTEGER, price INTEGER, purchase_date TEXT, expiry_date TEXT,
                  parsec_link TEXT, server_number INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS servers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, cheat TEXT,
                  server_number INTEGER, parsec_link TEXT, is_active INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def add_purchase(user_id, cheat, hours, price, parsec_link, server_number):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expiry_date = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO purchases (user_id, cheat, hours, price, purchase_date, expiry_date, parsec_link, server_number)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
              (user_id, cheat, hours, price, purchase_date, expiry_date, parsec_link, server_number))
    conn.commit()
    conn.close()

def get_active_purchases(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT * FROM purchases WHERE user_id=? AND expiry_date > ?", (user_id, now))
    purchases = c.fetchall()
    conn.close()
    return purchases

def add_server(user_id, cheat, server_number, parsec_link):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO servers (user_id, cheat, server_number, parsec_link) VALUES (?, ?, ?, ?)",
              (user_id, cheat, server_number, parsec_link))
    conn.commit()
    conn.close()

def get_available_server(cheat):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT server_number, parsec_link FROM servers WHERE cheat=? AND is_active=1 LIMIT 1", (cheat,))
    server = c.fetchone()
    conn.close()
    return server

# Клавиатуры
def main_menu_kb(is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="💰 Купить время", callback_data="buy")],
        [InlineKeyboardButton(text="📋 Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Стать сервером", callback_data="become_server")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Список серверов", callback_data="server_list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return kb

def cheats_kb():
    buttons = []
    for cheat in CHEATS.keys():
        buttons.append([InlineKeyboardButton(text=cheat.capitalize(), callback_data=f"cheat_{cheat}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tariff_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час - 30₽", callback_data="tariff_1")],
        [InlineKeyboardButton(text="3 часа - 90₽", callback_data="tariff_3")],
        [InlineKeyboardButton(text="24 часа - 720₽", callback_data="tariff_24")],
        [InlineKeyboardButton(text="⚙️ Кастом", callback_data="tariff_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_cheats")]
    ])
    return kb

def payment_kb(amount):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{amount}")],
        [InlineKeyboardButton(text="💎 Lolz переводы", callback_data=f"pay_lolz_{amount}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tariff")]
    ])
    return kb

# Команды
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    add_user(user_id, username)
    
    is_admin = user_id in ADMIN_IDS
    
    if is_admin:
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "☁️ Добро пожаловать в Aesthetic cloud!\n"
            "🎮 Аренда читов для Minecraft через Parsec\n\n"
            "⚡️ Ты администратор - доступны дополнительные функции.",
            reply_markup=main_menu_kb(is_admin=True)
        )
    else:
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "☁️ Добро пожаловать в Aesthetic cloud!\n"
            "🎮 Аренда читов для Minecraft через Parsec\n"
            "🕹 Играй с любого устройства!\n\n"
            "💰 Цена: 30₽/час",
            reply_markup=main_menu_kb(is_admin=False)
        )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🔧 Админ-панель:", reply_markup=admin_menu_kb())
    else:
        await message.answer("❌ У вас нет доступа к админ-панели.")

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id in ADMIN_IDS:
        await callback.message.edit_text("🔧 Админ-панель:", reply_markup=admin_menu_kb())
    else:
        await callback.answer("❌ У вас нет доступа к админ-панели.", show_alert=True)
    await callback.answer()

# Callback handlers
@dp.callback_query(F.data == "buy")
async def buy_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎮 Выбери чит:", reply_markup=cheats_kb())
    await state.set_state(BuyStates.choosing_cheat)
    await callback.answer()

@dp.callback_query(F.data.startswith("cheat_"))
async def cheat_selected(callback: types.CallbackQuery, state: FSMContext):
    cheat = callback.data.split("_")[1]
    await state.update_data(cheat=cheat)
    await callback.message.edit_text(f"✅ Выбран чит: {cheat.capitalize()}\n\n⏱ Выбери тариф:", reply_markup=tariff_kb())
    await state.set_state(BuyStates.choosing_tariff)
    await callback.answer()

@dp.callback_query(F.data.startswith("tariff_"))
async def tariff_selected(callback: types.CallbackQuery, state: FSMContext):
    tariff = callback.data.split("_")[1]
    
    if tariff == "custom":
        await callback.message.edit_text("⚙️ Введи количество часов (число):")
        await state.set_state(BuyStates.custom_hours)
        await callback.answer()
        return
    
    hours = int(tariff)
    amount = hours * PRICE_PER_HOUR
    await state.update_data(hours=hours, amount=amount)
    
    await callback.message.edit_text(
        f"💰 К оплате: {amount}₽\n⏱ Время: {hours} ч\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_kb(amount)
    )
    await state.set_state(BuyStates.choosing_payment)
    await callback.answer()

@dp.message(BuyStates.custom_hours)
async def custom_hours_handler(message: types.Message, state: FSMContext):
    try:
        hours = int(message.text)
        if hours <= 0:
            await message.answer("❌ Количество часов должно быть больше 0!")
            return
        
        amount = hours * PRICE_PER_HOUR
        await state.update_data(hours=hours, amount=amount)
        
        await message.answer(
            f"💰 К оплате: {amount}₽\n⏱ Время: {hours} ч\n\n"
            "Выбери способ оплаты:",
            reply_markup=payment_kb(amount)
        )
        await state.set_state(BuyStates.choosing_payment)
    except ValueError:
        await message.answer("❌ Введи корректное число!")

@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    hours = data['hours']
    cheat = data['cheat']
    
    prices = [LabeledPrice(label=f"{cheat.capitalize()} - {hours}ч", amount=amount)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Аренда {cheat.capitalize()}",
        description=f"Время игры: {hours} часов",
        payload=json.dumps({"cheat": cheat, "hours": hours}),
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message, state: FSMContext):
    payload = json.loads(message.successful_payment.invoice_payload)
    cheat = payload['cheat']
    hours = payload['hours']
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    is_admin = user_id in ADMIN_IDS
    
    # Уведомляем админов о покупке через Stars
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⭐️ Новая покупка через Stars!\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"🎮 Чит: {cheat.capitalize()}\n"
                f"⏱ Время: {hours} ч\n"
                f"� Сумма: {hours * PRICE_PER_HOUR}₽"
            )
        except:
            pass
    
    server = get_available_server(cheat)
    if server:
        server_number, parsec_link = server
        add_purchase(user_id, cheat, hours, hours * PRICE_PER_HOUR, parsec_link, server_number)
        
        expiry = datetime.now() + timedelta(hours=hours)
        await message.answer(
            f"✅ Оплата прошла успешно!\n\n"
            f"🎮 Чит: {cheat.capitalize()}\n"
            f"⏱ Время: {hours} ч\n"
            f"📅 Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}\n"
            f"🖥 Сервер #{server_number}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📖 ГАЙД ПО ПОДКЛЮЧЕНИЮ:\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"1️⃣ Скачай Parsec:\n"
            f"🔗 https://parsec.app/downloads\n\n"
            f"2️⃣ Установи и запусти Parsec\n\n"
            f"3️⃣ Нажми на эту ссылку:\n"
            f"🔗 {parsec_link}\n\n"
            f"4️⃣ Parsec автоматически подключится к серверу\n\n"
            f"5️⃣ Готово! Можешь играть 🎮\n\n"
            f"💡 Совет: Для лучшего качества используй проводной интернет",
            reply_markup=main_menu_kb(is_admin=is_admin)
        )
    else:
        await message.answer(
            "❌ К сожалению, все серверы заняты. Попробуй позже или выбери другой чит.",
            reply_markup=main_menu_kb(is_admin=is_admin)
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("pay_lolz_"))
async def pay_lolz_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    
    # Создаем кнопку с ссылкой на оплату
    payment_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Оплатить на Lolz", url=LOLZ_PAYMENT_URL)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="lolz_paid")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tariff")]
    ])
    
    await callback.message.edit_text(
        f"💎 Оплата через Lolz переводы\n\n"
        f"💰 Сумма: {amount}₽\n\n"
        f"📋 Инструкция:\n"
        f"1. Нажми кнопку 'Оплатить на Lolz'\n"
        f"2. Введи сумму: {amount}\n"
        f"3. Отправь перевод\n"
        f"4. Нажми 'Я оплатил'\n\n"
        f"⚠️ После оплаты администратор проверит платеж и активирует доступ.",
        reply_markup=payment_kb
    )
    await callback.answer()

@dp.callback_query(F.data == "lolz_paid")
async def lolz_paid_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cheat = data['cheat']
    hours = data['hours']
    amount = data['amount']
    user_id = callback.from_user.id
    username = callback.from_user.username or "Без username"
    is_admin = user_id in ADMIN_IDS
    
    # Уведомляем админов о платеже
    for admin_id in ADMIN_IDS:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{user_id}_{cheat}_{hours}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
        ])
        
        try:
            await bot.send_message(
                admin_id,
                f"💰 Новый платеж Lolz!\n\n"
                f"👤 Пользователь: @{username} (ID: {user_id})\n"
                f"🎮 Чит: {cheat.capitalize()}\n"
                f"⏱ Время: {hours} ч\n"
                f"💵 Сумма: {amount}₽\n\n"
                f"Проверь платеж на Lolz и подтверди.",
                reply_markup=admin_kb
            )
        except:
            pass
    
    await callback.message.edit_text(
        "✅ Заявка отправлена!\n\n"
        "⏳ Ожидай подтверждения от администратора.\n"
        "Обычно это занимает несколько минут.",
        reply_markup=main_menu_kb(is_admin=is_admin)
    )
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[1])
    cheat = parts[2]
    hours = int(parts[3])
    amount = hours * PRICE_PER_HOUR
    
    server = get_available_server(cheat)
    if server:
        server_number, parsec_link = server
        add_purchase(user_id, cheat, hours, amount, parsec_link, server_number)
        
        expiry = datetime.now() + timedelta(hours=hours)
        
        # Проверяем является ли пользователь админом
        is_user_admin = user_id in ADMIN_IDS
        
        try:
            await bot.send_message(
                user_id,
                f"✅ Платеж подтвержден!\n\n"
                f"🎮 Чит: {cheat.capitalize()}\n"
                f"⏱ Время: {hours} ч\n"
                f"📅 Действует до: {expiry.strftime('%d.%m.%Y %H:%M')}\n"
                f"🖥 Сервер #{server_number}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📖 ГАЙД ПО ПОДКЛЮЧЕНИЮ:\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"1️⃣ Скачай Parsec:\n"
                f"� https://parsec.app/downloads\n\n"
                f"2️⃣ Установи и запусти Parsec\n\n"
                f"3️⃣ Нажми на эту ссылку:\n"
                f"🔗 {parsec_link}\n\n"
                f"4️⃣ Parsec автоматически подключится к серверу\n\n"
                f"5️⃣ Готово! Можешь играть 🎮\n\n"
                f"💡 Совет: Для лучшего качества используй проводной интернет",
                reply_markup=main_menu_kb(is_admin=is_user_admin)
            )
            
            await callback.message.edit_text(
                f"✅ Платеж подтвержден!\n\n"
                f"Пользователю выдан доступ к {cheat.capitalize()}\n"
                f"Сервер #{server_number}"
            )
        except:
            await callback.answer("❌ Не удалось отправить сообщение пользователю", show_alert=True)
    else:
        await callback.answer("❌ Нет свободных серверов", show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split("_")[1])
    
    try:
        await bot.send_message(
            user_id,
            "❌ Платеж не подтвержден.\n\n"
            "Возможные причины:\n"
            "• Платеж не найден\n"
            "• Неверная сумма\n\n"
            "Обратись к администратору для уточнения.",
            reply_markup=main_menu_kb()
        )
        
        await callback.message.edit_text("❌ Платеж отклонен. Пользователь уведомлен.")
    except:
        await callback.answer("❌ Не удалось отправить сообщение пользователю", show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data == "my_purchases")
async def my_purchases_handler(callback: types.CallbackQuery):
    purchases = get_active_purchases(callback.from_user.id)
    
    if not purchases:
        await callback.message.edit_text(
            "📋 У тебя нет активных покупок.",
            reply_markup=main_menu_kb(is_admin=callback.from_user.id in ADMIN_IDS)
        )
    else:
        text = "📋 Твои активные покупки:\n\n"
        for p in purchases:
            text += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎮 {p[2].capitalize()}\n"
                f"⏱ {p[3]} ч\n"
                f"📅 До: {p[6]}\n"
                f"� Сервер #{p[8]}\n\n"
                f"� Подключение:\n"
                f"1. Скачай Parsec: https://parsec.app/downloads\n"
                f"2. Нажми на ссылку: {p[7]}\n"
                f"3. Играй! 🎮\n\n"
            )
        await callback.message.edit_text(text, reply_markup=main_menu_kb(is_admin=callback.from_user.id in ADMIN_IDS))
    
    await callback.answer()

@dp.callback_query(F.data == "info")
async def info_handler(callback: types.CallbackQuery):
    cheats_list = "\n".join([f"• {c.capitalize()}" for c in CHEATS.keys()])
    await callback.message.edit_text(
        f"☁️ Aesthetic cloud - Информация\n\n"
        f"💰 Цена: 30₽/час\n"
        f"🎮 Доступные читы:\n{cheats_list}\n\n"
        f"⏱ Тарифы:\n"
        f"• 1 час - 30₽\n"
        f"• 3 часа - 90₽\n"
        f"• 24 часа - 720₽\n"
        f"• Кастом - любое количество часов\n\n"
        f"🕹 Игра через Parsec",
        reply_markup=main_menu_kb(is_admin=callback.from_user.id in ADMIN_IDS)
    )
    await callback.answer()

# Админ функции
@dp.callback_query(F.data == "become_server")
async def become_server_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Создаем отдельные кнопки для админа
    buttons = []
    for cheat in CHEATS.keys():
        buttons.append([InlineKeyboardButton(text=cheat.capitalize(), callback_data=f"admin_cheat_{cheat}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("🎮 Выбери чит для хостинга:", reply_markup=kb)
    await state.set_state(AdminStates.choosing_cheat_to_host)
    await callback.answer()

@dp.callback_query(AdminStates.choosing_cheat_to_host, F.data.startswith("admin_cheat_"))
async def admin_cheat_selected(callback: types.CallbackQuery, state: FSMContext):
    cheat = callback.data.split("_")[2]
    await state.update_data(cheat=cheat)
    
    max_servers = CHEATS[cheat]['servers']
    buttons = []
    for i in range(1, max_servers + 1):
        buttons.append([InlineKeyboardButton(text=f"Сервер #{i}", callback_data=f"admin_server_{i}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"🖥 Выбери номер сервера для {cheat.capitalize()}:", reply_markup=kb)
    await state.set_state(AdminStates.choosing_server_number)
    await callback.answer()

@dp.callback_query(AdminStates.choosing_server_number, F.data.startswith("admin_server_"))
async def server_number_selected(callback: types.CallbackQuery, state: FSMContext):
    server_number = int(callback.data.split("_")[2])
    await state.update_data(server_number=server_number)
    
    await callback.message.edit_text("🔗 Введи ссылку Parsec:")
    await state.set_state(AdminStates.entering_parsec_link)
    await callback.answer()

@dp.message(AdminStates.entering_parsec_link)
async def parsec_link_entered(message: types.Message, state: FSMContext):
    parsec_link = message.text
    data = await state.get_data()
    cheat = data['cheat']
    server_number = data['server_number']
    
    add_server(message.from_user.id, cheat, server_number, parsec_link)
    
    await message.answer(
        f"✅ Сервер добавлен!\n\n"
        f"🎮 Чит: {cheat.capitalize()}\n"
        f"🖥 Сервер: #{server_number}\n"
        f"🔗 Ссылка: {parsec_link}",
        reply_markup=admin_menu_kb()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM purchases")
    purchases_count = c.fetchone()[0]
    c.execute("SELECT SUM(price) FROM purchases")
    total_revenue = c.fetchone()[0] or 0
    conn.close()
    
    await callback.message.edit_text(
        f"📊 Статистика бота\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"💰 Покупок: {purchases_count}\n"
        f"💵 Выручка: {total_revenue}₽",
        reply_markup=admin_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data == "server_list")
async def server_list_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT cheat, server_number, parsec_link, is_active FROM servers")
    servers = c.fetchall()
    conn.close()
    
    if not servers:
        text = "🖥 Нет активных серверов"
    else:
        text = "🖥 Список серверов:\n\n"
        for s in servers:
            status = "🟢" if s[3] else "🔴"
            text += f"{status} {s[0].capitalize()} - Сервер #{s[1]}\n{s[2]}\n\n"
    
    await callback.message.edit_text(text, reply_markup=admin_menu_kb())
    await callback.answer()

# Навигация
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data == "back_to_cheats")
async def back_to_cheats(callback: types.CallbackQuery):
    await callback.message.edit_text("🎮 Выбери чит:", reply_markup=cheats_kb())
    await callback.answer()

@dp.callback_query(F.data == "back_to_tariff")
async def back_to_tariff(callback: types.CallbackQuery):
    await callback.message.edit_text("⏱ Выбери тариф:", reply_markup=tariff_kb())
    await callback.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔧 Админ-панель:", reply_markup=admin_menu_kb())
    await callback.answer()

# Запуск бота
async def main():
    init_db()
    print("☁️ Aesthetic cloud запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
