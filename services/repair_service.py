from database import execute_query, execute_update
from services.player_service import get_player_balance, deduct_balance
from services.level_service import add_xp
from services.event_service import get_event_modifier

def get_applicable_repairs(car_id):
    """Получить типы ремонта, подходящие для конкретной машины"""
    query = """
        SELECT rt.id, rt.name, rt.description, rt.node_type, rt.cost, rt.improvement, rt.repair_time_days
        FROM repair_types rt
        JOIN cars c ON c.id = %s
        JOIN car_models cm ON cm.id = c.model_id
        WHERE 
            (NOT rt.requires_turbo OR cm.engine_type LIKE '%%турбо%%')
            AND (NOT rt.requires_auto_trans OR cm.transmission_type IN ('АКПП', 'DSG', 'вариатор', 'робот'))
            AND (NOT rt.requires_diesel OR cm.fuel_type = 'дизель')
            AND (NOT rt.requires_injection OR cm.engine_type IN ('инжектор', 'турбо'))
            AND (NOT rt.requires_carburetor OR cm.engine_type = 'карбюратор')
            AND cm.power_hp >= rt.min_power_hp
            AND cm.power_hp <= rt.max_power_hp
            AND c.year >= rt.min_year
            AND c.year <= rt.max_year
        ORDER BY rt.node_type, rt.cost
    """
    return execute_query(query, (car_id,))

def get_car_repair_status(car_id):
    """Получить текущее состояние узлов машины"""
    query = """
        SELECT engine_condition, transmission_condition, suspension_condition,
               paint_condition, interior_condition
        FROM cars
        WHERE id = %s
    """
    result = execute_query(query, (car_id,))
    if not result:
        return None

    engine, trans, susp, paint, interior = result[0]
    return {
        'engine': engine,
        'transmission': trans,
        'suspension': susp,
        'paint': paint,
        'interior': interior
    }

def repair_node(car_id, repair_type_id, player_id):
    query = """
        SELECT node_type, cost, improvement, repair_time_days
        FROM repair_types WHERE id = %s
    """
    result = execute_query(query, (repair_type_id,))
    if not result:
        return False, "Тип ремонта не найден", 0

    node_type, cost, improvement, repair_time = result[0]

    # ⭐ Применяем модификатор стоимости ремонта
    repair_modifier = get_event_modifier('repair_cost')
    actual_cost = int(cost * repair_modifier)

    balance = get_player_balance(player_id)
    if balance < actual_cost:
        return False, f"Недостаточно средств. Нужно {actual_cost:,} ₽, у вас {balance:,} ₽", 0

    car_status = get_car_repair_status(car_id)
    if not car_status:
        return False, "Машина не найдена", 0

    current_condition = car_status[node_type]
    new_condition = min(100, current_condition + improvement)

    deduct_balance(player_id, actual_cost)

    query = f"""
        UPDATE cars SET {node_type}_condition = %s
        WHERE id = %s AND owner_id = %s AND status = 'owned'
    """
    execute_update(query, (new_condition, car_id, player_id))

    query = "UPDATE cars SET repair_investments = repair_investments + %s WHERE id = %s"
    execute_update(query, (actual_cost, car_id))

 # ⭐ Опыт за ремонт
    xp_modifier = get_event_modifier('xp')
    xp_earned = int(max(5, actual_cost / 10000) * xp_modifier)
    add_xp(player_id, xp_earned)

    # ⭐ Считаем вложения в ремонт
    query = "UPDATE players SET total_repair_invested = total_repair_invested + %s WHERE id = %s"
    execute_update(query, (actual_cost, player_id))

    update_market_value(car_id)

    # ⭐ Проверяем достижения
    from services.achievement_service import check_achievements
    new_achievements = check_achievements(player_id)

    cost_note = f" (обычная цена {cost:,} ₽)" if repair_modifier != 1.0 else ""
    return True, f"Ремонт выполнен! {current_condition} → {new_condition} | -{actual_cost:,} ₽{cost_note} | +{xp_earned} XP", new_condition, new_achievements

def update_market_value(car_id):
    """Пересчитать рыночную стоимость после ремонта"""
    query = """
        SELECT c.engine_condition, c.transmission_condition, c.suspension_condition,
               c.paint_condition, c.interior_condition, 
               COALESCE(cm.real_2026_price, cm.base_price_new),
               c.mileage, c.year, c.purchase_price, c.repair_investments, cm.car_class
        FROM cars c
        JOIN car_models cm ON c.model_id = cm.id
        WHERE c.id = %s
    """
    result = execute_query(query, (car_id,))
    if not result:
        return

    engine, trans, susp, paint, interior, real_2026_price, mileage, year, purchase_price, repair_investments, car_class = result[0]

    avg_condition = (engine + trans + susp + paint + interior) / 5
    age = 2026 - year

    age_factor = 0.95 ** age
    mileage_factor = max(0.85, 1 - (mileage / 1500000))
    condition_factor = avg_condition / 100

    calculated_value = int(real_2026_price * age_factor * mileage_factor * condition_factor)

    repair_bonus = int(repair_investments * 0.8)
    min_value = purchase_price + repair_bonus
    new_market_value = max(calculated_value, min_value)

    # Жёсткий минимум по возрасту
    if age <= 3:
        min_price = int(real_2026_price * 0.80)
    elif age <= 5:
        min_price = int(real_2026_price * 0.70)
    elif age <= 7:
        min_price = int(real_2026_price * 0.60)
    elif age <= 10:
        min_price = int(real_2026_price * 0.45)
    else:
        min_price = int(real_2026_price * 0.25)

    class_mins = {
        'luxury': 5000000,
        'premium': 2000000,
        'mid': 1000000,
        'budget': 500000,
        'basic': 80000
    }
    class_min = class_mins.get(car_class, 80000)
    min_price = max(min_price, class_min)

    new_market_value = max(min_price, new_market_value)

    query = "UPDATE cars SET market_value = %s WHERE id = %s"
    execute_update(query, (new_market_value, car_id))