from database import execute_query, execute_update

def get_reputation(player_id):
    """Получить текущую репутацию игрока"""
    query = "SELECT reputation FROM players WHERE id = %s"
    result = execute_query(query, (player_id,))
    return result[0][0] if result else 50

def change_reputation(player_id, amount, reason):
    """
    Изменить репутацию игрока.
    amount: положительное или отрицательное число
    reason: причина изменения
    """
    from services.game_service import get_current_day

    current_rep = get_reputation(player_id)
    new_rep = max(0, min(100, current_rep + amount))

    if new_rep == current_rep:
        return new_rep, False

    # Обновляем репутацию
    query = "UPDATE players SET reputation = %s WHERE id = %s"
    execute_update(query, (new_rep, player_id))

    # Сохраняем в историю
    current_day = get_current_day(player_id)
    query = """
        INSERT INTO reputation_history (player_id, change_amount, reason, created_day)
        VALUES (%s, %s, %s, %s)
    """
    execute_update(query, (player_id, amount, reason, current_day))

    return new_rep, True

def get_reputation_tier(reputation):
    """Получить тир репутации"""
    if reputation >= 80:
        return 'excellent', 'Отличная', '💎'
    elif reputation >= 60:
        return 'good', 'Хорошая', '⭐'
    elif reputation >= 40:
        return 'neutral', 'Нейтральная', '😐'
    elif reputation >= 20:
        return 'poor', 'Плохая', '⚠️'
    else:
        return 'terrible', 'Ужасная', '💀'

def get_offer_modifier(reputation):
    """
    Получить модификатор предложений от покупателей на основе репутации.
    Возвращает множитель для цены предложения.
    """
    if reputation >= 80:
        return 1.15  # +15% к предложениям
    elif reputation >= 60:
        return 1.05  # +5%
    elif reputation >= 40:
        return 1.0   # без изменений
    elif reputation >= 20:
        return 0.85  # -15%
    else:
        return 0.70  # -30%

def get_offer_chance_modifier(reputation):
    """
    Получить модификатор шанса получения предложений.
    """
    if reputation >= 80:
        return 1.3  # +30% шанс
    elif reputation >= 60:
        return 1.15  # +15%
    elif reputation >= 40:
        return 1.0   # без изменений
    elif reputation >= 20:
        return 0.7   # -30%
    else:
        return 0.3   # -70% (почти не приходят)

def check_honest_sale(car_id, selling_price):
    """
    Проверить, честная ли продажа.
    Возвращает (is_honest, reason, rep_change)
    """
    query = """
        SELECT c.has_accidents, c.engine_condition, c.transmission_condition,
               c.suspension_condition, c.paint_condition, c.interior_condition,
               c.market_value, c.purchase_price
        FROM cars c WHERE c.id = %s
    """
    result = execute_query(query, (car_id,))
    if not result:
        return True, "", 0

    has_acc, engine, trans, susp, paint, interior, market_val, purchase_price = result[0]

    # Средняя оценка состояния
    avg_condition = (engine + trans + susp + paint + interior) / 5

    # Проверки
    if has_acc and selling_price > market_val * 1.1:
        return False, "Продажа битой машины по завышенной цене", -15

    if avg_condition < 50 and selling_price > market_val * 1.2:
        return False, "Продажа убитой машины по завышенной цене", -10

    if selling_price > market_val * 1.5:
        return False, "Сильно завышенная цена", -8

    # Честная сделка
    if selling_price <= market_val * 1.05:
        return True, "Честная сделка", 3

    return True, "", 1

def on_car_sold(car_id, selling_price, player_id):
    """
    Обработка продажи машины.
    Проверяет честность и изменяет репутацию.
    """
    is_honest, reason, rep_change = check_honest_sale(car_id, selling_price)

    if rep_change != 0:
        new_rep, changed = change_reputation(player_id, rep_change, reason)
        if changed:
            return new_rep, rep_change, reason

    return get_reputation(player_id), 0, ""

def on_quick_sale(player_id, days_on_market):
    """Бонус за быструю продажу"""
    if days_on_market <= 2:
        return change_reputation(player_id, 2, "Быстрая продажа")
    elif days_on_market <= 5:
        return change_reputation(player_id, 1, "Продажа в срок")
    return get_reputation(player_id), False