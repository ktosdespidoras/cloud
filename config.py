import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
LOLZ_TOKEN = os.getenv('LOLZ_TOKEN')

# Тарифы (цена за час)
PRICE_PER_HOUR = 30

# Читы и их серверы
CHEATS = {
    'nursultan': {'servers': 2, 'name': 'Nursultan'},
    'expensive': {'servers': 2, 'name': 'Expensive'},
    'wexside': {'servers': 2, 'name': 'Wexside'},
    'catlava': {'servers': 2, 'name': 'Catlava'},
    'nenergycelestial': {'servers': 2, 'name': 'Nenergycelestial'},
    'excelent': {'servers': 2, 'name': 'Excelent'},
    'wild': {'servers': 2, 'name': 'Wild'},
    'everlast': {'servers': 2, 'name': 'Everlast'}
}

# Тарифные планы
TARIFFS = {
    '1h': {'hours': 1, 'name': '1 час'},
    '3h': {'hours': 3, 'name': '3 часа'},
    '24h': {'hours': 24, 'name': '24 часа'},
    'custom': {'hours': 0, 'name': 'Кастом'}
}
