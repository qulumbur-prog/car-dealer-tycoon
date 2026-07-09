from database import execute_query, execute_update
from services.player_service import get_player_balance, deduct_balance, add_balance
from services.game_service import get_current_day
from services.level_service import add_xp, record_deal, check_level_up, get_unlocked_classes
from services.event_service import get_event_modifier
from services.reputation_service import on_car_sold, change_reputation

def refresh_market_listings(limit=12):
    """Обновить список машин на рынке"""
    execute_update("UPDATE cars SET is_on_market_today = FALSE WHERE status = 'market'")
    query = """
        UPDATE cars
        SET is_on_market_today = TRUE
        WHERE id IN (
            SELECT id FROM cars
            WHERE status = 'market'
            ORDER BY RANDOM()
            LIMIT %s
        )
    """
    execute_update(query, (limit,))

def get_market_cars(limit=50, offset=0, filters=None, allowed_classes=None):
    if filters is None: filters = {}
    if allowed_classes is None: allowed_classes = ['basic']

    query = """
        SELECT c.id, cm.brand, cm.model, cm.generation, c.year, c.mileage, 
               c.selling_price, c.color_exterior, c.engine_condition, c.has_accidents,
               cm.car_class
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.status = 'market' AND c.is_on_market_today = TRUE
          AND cm.car_class = ANY(%s)
    """
    params = [allowed_classes]
    conditions = []

    if filters.get('brand'):
        conditions.append("cm.brand ILIKE %s")
        params.append(f"%{filters['brand']}%")
    if filters.get('min_price'):
        conditions.append("c.selling_price >= %s")
        params.append(filters['min_price'])
    if filters.get('max_price'):
        conditions.append("c.selling_price <= %s")
        params.append(filters['max_price'])
    if filters.get('min_year'):
        conditions.append("c.year >= %s")
        params.append(filters['min_year'])
    if filters.get('max_year'):
        conditions.append("c.year <= %s")
        params.append(filters['max_year'])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY c.selling_price LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    raw_cars = execute_query(query, tuple(params))

    # ⭐ Применяем модификатор цен от событий
    result = []
    for car in raw_cars:
        car_id, brand, model, gen, year, mileage, price, color, engine_cond, has_acc, car_class = car
        price_modifier = get_event_modifier('price', car_class)
        adjusted_price = int(price * price_modifier)
        result.append((car_id, brand, model, gen, year, mileage, adjusted_price, color, engine_cond, has_acc))

    return result

def get_market_cars_count(filters=None, allowed_classes=None):
    """Получить количество машин на рынке"""
    if filters is None:
        filters = {}
    if allowed_classes is None:
        allowed_classes = ['basic']

    query = """
        SELECT COUNT(*)
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.status = 'market' AND c.is_on_market_today = TRUE
          AND cm.car_class = ANY(%s)
    """
    params = [allowed_classes]
    conditions = []

    if filters.get('brand'):
        conditions.append("cm.brand ILIKE %s")
        params.append(f"%{filters['brand']}%")

    if filters.get('min_price'):
        conditions.append("c.selling_price >= %s")
        params.append(filters['min_price'])

    if filters.get('max_price'):
        conditions.append("c.selling_price <= %s")
        params.append(filters['max_price'])

    if filters.get('min_year'):
        conditions.append("c.year >= %s")
        params.append(filters['min_year'])

    if filters.get('max_year'):
        conditions.append("c.year <= %s")
        params.append(filters['max_year'])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    result = execute_query(query, tuple(params))
    return result[0][0] if result else 0

def add_car_to_market_today(car_id):
    """Добавить машину в активные сегодня"""
    query = "UPDATE cars SET is_on_market_today = TRUE WHERE id = %s AND status = 'market'"
    execute_update(query, (car_id,))

def get_car_details(car_id):
    """Получить полную информацию о машине"""
    query = """
        SELECT c.id, cm.brand, cm.model, cm.generation, c.year, c.mileage, 
               c.selling_price, c.market_value, c.color_exterior, c.color_interior,
               c.engine_condition, c.transmission_condition, c.suspension_condition,
               c.paint_condition, c.interior_condition, c.has_accidents, c.accident_count,
               c.service_history, c.owners_count, c.vin
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.id = %s
    """
    result = execute_query(query, (car_id,))
    return result[0] if result else None

def get_available_brands(allowed_classes=None):
    """Получить список марок машин на рынке"""
    if allowed_classes is None:
        allowed_classes = ['basic']
    query = """
        SELECT DISTINCT cm.brand
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.status = 'market' AND c.is_on_market_today = TRUE
          AND cm.car_class = ANY(%s)
        ORDER BY cm.brand
    """
    return [row[0] for row in execute_query(query, (allowed_classes,))]

def negotiate_price(car_id, offered_price):
    """Попытаться сторговаться"""
    car = get_car_details(car_id)
    if not car:
        return False, 0, "Машина не найдена"

    selling_price = car[6]

    if offered_price >= selling_price:
        return True, selling_price, "Продавец согласился на вашу цену!"

    discount_percent = (selling_price - offered_price) / selling_price * 100

    if discount_percent <= 5:
        final_price = offered_price
        message = f"Продавец согласился! Вы сэкономили {selling_price - final_price:,} ₽"
        return True, final_price, message
    elif discount_percent <= 15:
        compromise = (selling_price - offered_price) / 2
        final_price = int(selling_price - compromise)
        message = f"Продавец готов уступить до {final_price:,} ₽"
        return True, final_price, message
    else:
        message = "Продавец отклонил предложение. Слишком низкая цена!"
        return False, selling_price, message

def buy_car(car_id, player_id, final_price=None):
    """Купить машину"""
    car = get_car_details(car_id)
    if not car:
        return False, "Машина не найдена"

    query = "SELECT id FROM cars WHERE id = %s AND status = 'market' AND is_on_market_today = TRUE"
    result = execute_query(query, (car_id,))
    if not result:
        return False, "Эта машина уже не доступна на рынке"

    price = final_price if final_price else car[6]
    balance = get_player_balance(player_id)

    if balance < price:
        return False, f"Недостаточно средств. Нужно {price:,} ₽, у вас {balance:,} ₽"

    deduct_balance(player_id, price)

    query = """
        UPDATE cars 
        SET status = 'owned', owner_id = %s, purchase_price = %s, is_on_market_today = FALSE
        WHERE id = %s AND status = 'market'
    """
    execute_update(query, (player_id, price, car_id))

    # ⭐ Опыт за покупку
    add_xp(player_id, 15)

    # ⭐ Считаем купленные машины
    query = "UPDATE players SET total_cars_bought = total_cars_bought + 1 WHERE id = %s"
    execute_update(query, (player_id,))

    # ⭐ Проверяем специальные условия для достижений
    from services.car_service import get_car_details as _get_details
    car_full = _get_details(car_id)
    special = {}
    if car_full:
        # Получаем класс машины
        q = """
            SELECT cm.car_class FROM cars c
            JOIN car_models cm ON c.model_id = cm.id
            WHERE c.id = %s
        """
        r = execute_query(q, (car_id,))
        if r:
            car_class = r[0][0]
            if car_class == 'premium':
                special['bought_premium'] = True
            if car_class == 'luxury':
                special['bought_luxury'] = True
                special['bought_premium'] = True

    # ⭐ Проверяем достижения
    from services.achievement_service import check_achievements
    new_achievements = check_achievements(player_id, special)

    # ⭐ Проверяем уровень
    leveled_up, level_msg = check_level_up(player_id)

    msg = f"Машина куплена за {price:,} ₽ (+15 XP)"
    if leveled_up:
        msg += f" | {level_msg}"

    return True, msg, new_achievements  # ⭐ Возвращаем список новых достижений

def get_player_cars(player_id):
    """Получить машины игрока"""
    query = """
        SELECT c.id, cm.brand, cm.model, cm.generation, c.year, c.mileage, 
               c.market_value, c.color_exterior, c.engine_condition, c.purchase_price,
               c.status, c.selling_price, c.listed_day
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.owner_id = %s AND c.status IN ('owned', 'selling')
        ORDER BY c.created_at DESC
    """
    return execute_query(query, (player_id,))

def sell_car(car_id, player_id, selling_price):
    """Выставить машину на продажу"""
    try:
        query = "SELECT purchase_price FROM cars WHERE id = %s"
        res = execute_query(query, (car_id,))
        purchase_price = res[0][0] if res else 0

        query = "SELECT id FROM cars WHERE id = %s AND owner_id = %s AND status = 'owned'"
        result = execute_query(query, (car_id, player_id))

        if not result:
            return False, "Машина не найдена в вашем гараже", []

        from services.game_service import list_car_for_sale
        list_car_for_sale(car_id, player_id, selling_price)

        add_car_to_market_today(car_id)

        # ⭐ Опыт и статистика
        profit = selling_price - purchase_price
        xp_earned = max(20, int(abs(profit) / 1000)) if profit > 0 else 5
        add_xp(player_id, xp_earned)
        record_deal(player_id, profit)

        query = "UPDATE players SET total_cars_sold = total_cars_sold + 1 WHERE id = %s"
        execute_update(query, (player_id,))

        # ⭐ Проверяем достижения
        from services.achievement_service import check_achievements
        new_achievements = check_achievements(player_id)

        leveled_up, level_msg = check_level_up(player_id)

        # ⭐ Проверяем репутацию при выставлении на продажу
        new_rep, rep_change, rep_reason = on_car_sold(car_id, selling_price, player_id)

        msg = f"Машина выставлена за {selling_price:,} ₽ (+{xp_earned} XP)"
        if rep_change != 0:
            sign = "+" if rep_change > 0 else ""
            msg += f"\n📊 Репутация: {sign}{rep_change} ({rep_reason})"
        if leveled_up:
            msg += f"\n{level_msg}"

        return True, msg, new_achievements, rep_change
    except Exception as e:
        return False, f"Ошибка при продаже: {str(e)}", [], 0
