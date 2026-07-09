from database import execute_query, execute_update, execute_insert
import random
from services.event_service import generate_daily_event, tick_events
from services.event_service import get_event_modifier
from services.reputation_service import get_reputation, get_offer_modifier, get_offer_chance_modifier

def get_current_day(player_id):
    """Получить текущий день игры"""
    query = """
        SELECT current_day FROM game_state
        WHERE player_id = %s
    """
    result = execute_query(query, (player_id,))
    return result[0][0] if result else 1

def next_day(player_id):
    """Перейти к следующему дню"""
    current_day = get_current_day(player_id)
    new_day = current_day + 1

    print(f"=== Переход к дню {new_day} ===")

    # Обновляем день
    query = """
        UPDATE game_state
        SET current_day = %s, last_update = CURRENT_TIMESTAMP
        WHERE player_id = %s
    """
    execute_update(query, (new_day, player_id))

    # ⭐ Уменьшаем длительность старых событий
    tick_events()

    # ⭐ Генерируем новое событие с шансом 10%
    event_desc, is_new = generate_daily_event(new_day, player_id)

    # Обновляем список машин на рынке
    from services.car_service import refresh_market_listings
    refresh_market_listings(limit=12)

    # Генерируем предложения покупателей
    new_offers = generate_buyer_offers(player_id, new_day)

    return {
        'day': new_day,
        'new_offers': new_offers,
        'new_cars': 12,
        'new_event': event_desc if is_new else None  # ⭐ Новое поле
    }

def generate_buyer_offers(player_id, current_day):
    query = """
        SELECT c.id, c.selling_price, c.market_value, c.listed_day
        FROM cars c
        WHERE c.owner_id = %s AND c.status = 'selling'
    """
    selling_cars = execute_query(query, (player_id,))

    # ⭐ Получаем репутацию и модификаторы
    reputation = get_reputation(player_id)
    offer_chance_mod = get_offer_chance_modifier(reputation)
    offer_price_mod = get_offer_modifier(reputation)

    # Модификатор от событий
    from services.event_service import get_event_modifier
    event_offer_mod = get_event_modifier('offer_chance')

    new_offers = []

    for car in selling_cars:
        car_id, selling_price, market_value, listed_day = car

        if listed_day is None:
            listed_day = current_day - 1
            execute_update("UPDATE cars SET listed_day = %s WHERE id = %s", (listed_day, car_id))

        days_on_sale = current_day - listed_day

        base_chance = min(0.95, 0.50 + (days_on_sale * 0.25))
        # ⭐ Применяем модификаторы: репутация + события
        offer_chance = min(0.95, base_chance * offer_chance_mod * event_offer_mod)

        if random.random() < offer_chance:
            # ⭐ Модификатор цены от репутации
            offer_percent = random.uniform(0.75, 1.05) * offer_price_mod
            offered_price = int(selling_price * offer_percent)

            query = """
                INSERT INTO offers (car_id, player_id, offered_price, created_day)
                VALUES (%s, %s, %s, %s) RETURNING id
            """
            result = execute_insert(query, (car_id, player_id, offered_price, current_day))
            offer_id = result[0][0]

            new_offers.append({
                'offer_id': offer_id,
                'car_id': car_id,
                'offered_price': offered_price
            })

    return new_offers

def list_car_for_sale(car_id, player_id, price):
    """Выставить машину на продажу"""
    current_day = get_current_day(player_id)

    print(f"Выставляем машину {car_id} на продажу за {price} ₽, день {current_day}")

    query = """
        UPDATE cars
        SET status = 'selling', selling_price = %s, listed_day = %s
        WHERE id = %s AND owner_id = %s AND status = 'owned'
    """
    execute_update(query, (price, current_day, car_id, player_id))

def get_pending_offers(player_id):
    """Получить все ожидающие предложения"""
    query = """
        SELECT o.id, o.car_id, o.offered_price, o.created_day,
               cm.brand, cm.model, cm.generation, c.year, c.mileage, c.selling_price
        FROM offers o
        JOIN cars c ON o.car_id = c.id
        JOIN car_models cm ON c.model_id = cm.id
        WHERE o.player_id = %s AND o.status = 'pending'
        ORDER BY o.created_at DESC
    """
    return execute_query(query, (player_id,))

def get_offer_details(offer_id):
    """Получить детали предложения"""
    query = """
        SELECT o.id, o.car_id, o.offered_price, o.status,
               c.selling_price, c.market_value, c.purchase_price,
               cm.brand, cm.model, cm.generation, c.year, c.mileage
        FROM offers o
        JOIN cars c ON o.car_id = c.id
        JOIN car_models cm ON c.model_id = cm.id
        WHERE o.id = %s
    """
    result = execute_query(query, (offer_id,))
    return result[0] if result else None

def accept_offer(offer_id, final_price):
    """Принять предложение"""
    current_day = get_current_day_from_db()

    query = """
        UPDATE offers
        SET status = 'accepted', responded_day = %s, final_price = %s
        WHERE id = %s
    """
    execute_update(query, (current_day, final_price, offer_id))

    query = """
        UPDATE cars
        SET status = 'sold', sold_day = %s, is_on_market_today = FALSE
        WHERE id = (SELECT car_id FROM offers WHERE id = %s)
    """
    execute_update(query, (current_day, offer_id))

    return True, f"Машина продана за {final_price:,} ₽!"

def reject_offer(offer_id):
    """Отклонить предложение"""
    current_day = get_current_day_from_db()

    query = """
        UPDATE offers
        SET status = 'rejected', responded_day = %s
        WHERE id = %s
    """
    execute_update(query, (current_day, offer_id))

    return True, "Предложение отклонено"

def counter_offer(offer_id, counter_price):
    """Предложить встречную цену"""
    current_day = get_current_day_from_db()

    query = """
        UPDATE offers
        SET status = 'countered', responded_day = %s, final_price = %s
        WHERE id = %s
    """
    execute_update(query, (current_day, counter_price, offer_id))

    query = """
        UPDATE cars
        SET status = 'sold', sold_day = %s, is_on_market_today = FALSE
        WHERE id = (SELECT car_id FROM offers WHERE id = %s)
    """
    execute_update(query, (current_day, offer_id))

    return True, f"Машина продана за {counter_price:,} ₽!"

def get_current_day_from_db():
    """Получить текущий день (без привязки к игроку)"""
    query = "SELECT MAX(current_day) FROM game_state"
    result = execute_query(query)
    return result[0][0] if result and result[0][0] else 1