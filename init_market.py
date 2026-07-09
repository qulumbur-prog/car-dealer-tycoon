"""
Скрипт для инициализации рынка после генерации машин.
Запускается один раз после generate_cars.py
"""
from services.car_service import refresh_market_listings

if __name__ == "__main__":
    print("Инициализируем рынок...")
    refresh_market_listings(limit=12)
    print("✅ Готово! На рынке 12 случайных машин.")