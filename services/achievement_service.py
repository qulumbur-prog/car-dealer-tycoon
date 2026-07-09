from database import execute_query, execute_update, execute_insert

def get_all_achievements():
    """Получить все достижения"""
    query = """
        SELECT id, code, name, description, icon, category, 
               condition_type, condition_value, reward_money, reward_xp
        FROM achievements
        ORDER BY category, condition_value
    """
    return execute_query(query)

def get_player_achievements(player_id):
    """Получить достижения игрока"""
    query = """
        SELECT a.id, a.code, a.name, a.description, a.icon, a.category,
               a.condition_type, a.condition_value, a.reward_money, a.reward_xp,
               pa.unlocked_day, pa.unlocked_at
        FROM achievements a
        LEFT JOIN player_achievements pa ON pa.achievement_id = a.id AND pa.player_id = %s
        ORDER BY a.category, a.condition_value
    """
    return execute_query(query, (player_id,))

def get_player_stats_for_achievements(player_id):
    """Получить статистику для проверки достижений"""
    query = """
        SELECT current_level, total_deals, total_profit, total_cars_bought, 
               total_cars_sold, total_repair_invested, total_saved_on_torg
        FROM players WHERE id = %s
    """
    result = execute_query(query, (player_id,))
    if not result:
        return None

    level, deals, profit, bought, sold, repair_invested, saved_torg = result[0]
    return {
        'level': level,
        'deals': deals,
        'profit': profit,
        'cars_bought': bought,
        'cars_sold': sold,
        'repair_invested': repair_invested,
        'saved_on_torg': saved_torg
    }

def has_achievement(player_id, achievement_code):
    """Проверить, есть ли у игрока достижение"""
    query = """
        SELECT 1 FROM player_achievements pa
        JOIN achievements a ON a.id = pa.achievement_id
        WHERE pa.player_id = %s AND a.code = %s
    """
    result = execute_query(query, (player_id, achievement_code))
    return bool(result)

def unlock_achievement(player_id, achievement_id):
    """Разблокировать достижение и выдать награды"""
    from services.game_service import get_current_day
    from services.player_service import add_balance
    from services.level_service import add_xp

    # Получаем информацию о достижении
    query = """
        SELECT code, name, icon, reward_money, reward_xp
        FROM achievements WHERE id = %s
    """
    result = execute_query(query, (achievement_id,))
    if not result:
        return None

    code, name, icon, reward_money, reward_xp = result[0]

    # Проверяем, не разблокировано ли уже
    if has_achievement(player_id, code):
        return None

    # Сохраняем достижение
    current_day = get_current_day(player_id)
    query = """
        INSERT INTO player_achievements (player_id, achievement_id, unlocked_day)
        VALUES (%s, %s, %s)
    """
    execute_update(query, (player_id, achievement_id, current_day))

    # Выдаём награды
    if reward_money > 0:
        add_balance(player_id, reward_money)
    if reward_xp > 0:
        add_xp(player_id, reward_xp)

    return {
        'code': code,
        'name': name,
        'icon': icon,
        'reward_money': reward_money,
        'reward_xp': reward_xp
    }

def check_achievements(player_id, special_conditions=None):
    """
    Проверить все достижения и разблокировать новые.
    special_conditions: dict с доп. условиями типа {'bought_premium': True}
    """
    if special_conditions is None:
        special_conditions = {}

    stats = get_player_stats_for_achievements(player_id)
    if not stats:
        return []

    all_achievements = get_all_achievements()
    newly_unlocked = []

    for ach in all_achievements:
        ach_id, code, name, desc, icon, category, cond_type, cond_value, reward_money, reward_xp = ach

        # Проверяем, не разблокировано ли уже
        if has_achievement(player_id, code):
            continue

        # Проверяем условие
        unlocked = False

        if cond_type == 'cars_bought':
            unlocked = stats['cars_bought'] >= cond_value
        elif cond_type == 'cars_sold':
            unlocked = stats['cars_sold'] >= cond_value
        elif cond_type == 'total_profit':
            unlocked = stats['profit'] >= cond_value
        elif cond_type == 'repairs_done':
            unlocked = stats['deals'] >= cond_value  # deals = все сделки
        elif cond_type == 'repair_invested':
            unlocked = stats['repair_invested'] >= cond_value
        elif cond_type == 'saved_on_torg':
            unlocked = stats['saved_on_torg'] >= cond_value
        elif cond_type == 'level_reached':
            unlocked = stats['level'] >= cond_value
        elif cond_type == 'bought_premium':
            unlocked = special_conditions.get('bought_premium', False)
        elif cond_type == 'bought_luxury':
            unlocked = special_conditions.get('bought_luxury', False)

        if unlocked:
            result = unlock_achievement(player_id, ach_id)
            if result:
                newly_unlocked.append(result)

    return newly_unlocked