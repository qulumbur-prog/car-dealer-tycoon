import psycopg2
import random
import string

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
DB_CONFIG = {
    "dbname": "carsell_db",
    "user": "qulumbur",
    "password": "simplepass",
    "host": "localhost",
    "port": "5432"
}

# --- СПРАВОЧНИКИ ---
EXT_COLORS = ["Белый перламутр", "Черный металлик", "Серый уран", "Серебристый", "Красный кристалл", "Синий неон", "Бежевый песок"]
INT_COLORS = ["Черный", "Бежевый", "Коричневый", "Серый", "Рыжий"]
CITIES = ["Москва", "Санкт-Петербург", "Курск", "Воронеж", "Казань", "Екатеринбург", "Нижний Новгород"]

def generate_vin():
    chars = string.ascii_uppercase + string.digits
    valid_chars = [c for c in chars if c not in ['I', 'O', 'Q']]
    return ''.join(random.choice(valid_chars) for _ in range(17))

def get_condition(base=70):
    base = int(base)
    return random.randint(max(30, base - 25), min(100, base + 10))

def calculate_price(real_2026_price, trim_premium, age, mileage, conditions, has_accidents, pts_type, keys, car_class):
    """Расчет цены от РЕАЛЬНОЙ цены новой машины в 2026"""

    full_new_price = real_2026_price * (1 + trim_premium / 100)

    # Коэффициенты износа
    age_factor = 0.95 ** age
    mileage_factor = max(0.85, 1 - (mileage / 1500000))
    avg_cond = sum(conditions.values()) / len(conditions)
    condition_factor = avg_cond / 100

    market_val = int(full_new_price * age_factor * mileage_factor * condition_factor)

    # ⚠️ ЖЁСТКИЙ МИНИМУМ ПО ВОЗРАСТУ (реалии 2026)
    if age <= 3:
        min_price = int(full_new_price * 0.80)  # 3-летка не дешевле 80% от новой
    elif age <= 5:
        min_price = int(full_new_price * 0.70)  # 5-летка не дешевле 70%
    elif age <= 7:
        min_price = int(full_new_price * 0.60)  # 7-летка не дешевле 60%
    elif age <= 10:
        min_price = int(full_new_price * 0.45)  # 10-летка не дешевле 45%
    else:
        min_price = int(full_new_price * 0.25)  # Старше 10 лет — не дешевле 25%

    # Абсолютные минимумы по классам
    class_mins = {
        'luxury': 5000000,
        'premium': 2000000,
        'mid': 1000000,
        'budget': 500000,
        'basic': 80000
    }
    class_min = class_mins.get(car_class, 80000)
    min_price = max(min_price, class_min)

    if market_val < min_price:
        market_val = min_price

    # Штрафы за историю
    if has_accidents: market_val *= 0.92
    if pts_type == 'duplicate': market_val *= 0.98
    if keys < 2: market_val *= 0.99

    return int(market_val)

def generate_fleet(cars_per_model=5):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # ⚠️ Используем real_2026_price вместо base_price_new
    cur.execute("SELECT id, COALESCE(real_2026_price, base_price_new), year_start, year_end, car_class FROM car_models")
    models = cur.fetchall()

    total_created = 0

    for model in models:
        model_id, real_price, year_start, year_end, car_class = model

        end_year = year_end if year_end else 2026
        if year_start > end_year: continue

        for _ in range(cars_per_model):
            cur.execute("SELECT id, price_premium_percent FROM trim_levels WHERE model_id = %s", (model_id,))
            trims = cur.fetchall()
            if not trims: continue
            trim_id, trim_premium = random.choice(trims)

            year = random.randint(year_start, end_year)
            age = 2026 - year
            mileage = random.randint(age * 10000, age * 22000)
            owners = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]

            wear_base = max(50, int(100 - (age * 3) - (mileage / 10000)))
            conditions = {
                'paint': get_condition(wear_base),
                'interior': get_condition(wear_base),
                'engine': get_condition(wear_base),
                'trans': get_condition(wear_base),
                'susp': get_condition(wear_base),
                'elec': get_condition(wear_base),
                'tires': get_condition(wear_base)
            }

            has_accidents = random.random() < 0.25
            accident_count = random.randint(1, 3) if has_accidents else 0
            service_history = random.random() < 0.4
            keys = random.choice([1, 2, 2, 3])
            pts_type = 'duplicate' if (owners > 2 or has_accidents) and random.random() < 0.5 else 'original'

            # ⚠️ Передаём real_price и car_class
            market_val = calculate_price(real_price, trim_premium, age, mileage, conditions, has_accidents, pts_type, keys, car_class)
            selling_price = int(market_val * random.uniform(1.03, 1.12))

            try:
                cur.execute("""
                    INSERT INTO cars (
                        model_id, trim_id, vin, year, mileage, owners_count,
                        color_exterior, color_interior,
                        paint_condition, interior_condition, engine_condition,
                        transmission_condition, suspension_condition, electronics_condition, tire_condition,
                        has_accidents, accident_count, service_history, keys_count, pts_type,
                        market_value, selling_price, status, location_city
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    model_id, trim_id, generate_vin(), year, mileage, owners,
                    random.choice(EXT_COLORS), random.choice(INT_COLORS),
                    conditions['paint'], conditions['interior'], conditions['engine'],
                    conditions['trans'], conditions['susp'], conditions['elec'], conditions['tires'],
                    has_accidents, accident_count, service_history, keys, pts_type,
                    market_val, selling_price, 'market', random.choice(CITIES)
                ))
                total_created += 1
            except Exception as e:
                print(f"Ошибка (Model ID: {model_id}): {e}")
                conn.rollback()
            else:
                conn.commit()

    cur.close()
    conn.close()
    print(f"Готово! Создано {total_created} автомобилей.")

if __name__ == "__main__":
    generate_fleet()