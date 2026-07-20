"""
Скрипт для автоматической загрузки данных из API в history.csv
Запускается планировщиком задач ежедневно в 1:00
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import sys

# Пути
script_dir = Path(__file__).parent
HISTORY_FILE = script_dir / 'history.csv'

# API endpoint
API_URL = "https://your-api.example.com/api/v1/reports/workers"

def log(message):
    """Логирование в консоль и файл"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # Пишем в лог-файл
    log_file = script_dir / 'fetch_data.log'
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

def save_to_history(df, date):
    """Сохраняет данные в history.csv, добавляя колонку date"""
    df_copy = df.copy()
    df_copy['date'] = date
    
    if HISTORY_FILE.exists():
        # Читаем существующий файл
        history_df = pd.read_csv(HISTORY_FILE)
        
        # Проверяем, есть ли уже данные за эту дату
        if date in history_df['date'].values:
            log(f"⚠️ Данные за {date} уже существуют. Обновляем...")
            # Удаляем старые данные за эту дату
            history_df = history_df[history_df['date'] != date]
            # Дописываем новые данные
            pd.concat([history_df, df_copy], ignore_index=True).to_csv(HISTORY_FILE, index=False)
        else:
            log(f"✅ Дописываем данные за {date}")
            pd.concat([history_df, df_copy], ignore_index=True).to_csv(HISTORY_FILE, index=False)
    else:
        log(f"✅ Создаём новый файл истории с данными за {date}")
        df_copy.to_csv(HISTORY_FILE, index=False)

def fetch_and_save():
    """Основная функция: загрузка из API и сохранение"""
    log("=" * 50)
    log("🚀 Начало загрузки данных из API")
    
    try:
        # Запрос к API
        log(f"📡 Запрос к API: {API_URL}")
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        log(f"📦 Получено записей: {len(data)}")
        
        if not data:
            log("❌ API вернул пустые данные!")
            return False
        
        df = pd.DataFrame(data)
        
        # Проверяем наличие обязательных колонок
        required_columns = ['AZS', 'Filial_name', 'Name_bedolagi', 'Total_cheks']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            log(f"❌ Отсутствуют колонки: {missing}")
            return False
        
        # Дата сегодня
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # Сохраняем в историю
        save_to_history(df, today_str)
        
        log("✅ Загрузка завершена успешно")
        log(f"📊 Итого строк в history.csv: {len(pd.read_csv(HISTORY_FILE))}")
        return True
        
    except requests.exceptions.Timeout:
        log("❌ Таймаут при запросе к API")
        return False
    except requests.exceptions.ConnectionError:
        log("❌ Ошибка подключения к API")
        return False
    except requests.exceptions.HTTPError as e:
        log(f"❌ HTTP ошибка: {e}")
        return False
    except Exception as e:
        log(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    success = fetch_and_save()
    sys.exit(0 if success else 1)
