from database import execute_query, execute_update
from services.game_service import get_current_day
from services.event_service import get_event_modifier

def get_player_stats(player_id):
    """Получить статистику игрока"""
    query = """
        SELECT current_level, current_xp, total_deals, total_profit, min_day_reached
        FROM players WHERE id = %s
    """
    result = execute_query(query, (player_id,))
    return result[0] if result else (1, 0, 0, 0, 1)

def get_next_level_config(level):
    """Получить конфигурацию следующего уровня"""
    query = "SELECT level, xp_required, deals_required, profit_required, min_day, unlocks_class FROM level_config WHERE level = %s"
    result = execute_query(query, (level + 1,))
    return result[0] if result else None

def get_unlocked_classes(player_id):
    """Получить список классов машин, доступных игроку"""
    level, _, _, _, _ = get_player_stats(player_id)
    query = """
        SELECT ARRAY_AGG(DISTINCT unlocks_class) 
        FROM level_config WHERE level <= %s
    """
    result = execute_query(query, (level,))
    return result[0][0] if result and result[0][0] else ['basic']

def add_xp(player_id, amount):
    # ⭐ Применяем модификатор XP от событий
    xp_modifier = get_event_modifier('xp')
    actual_amount = int(amount * xp_modifier)
    query = "UPDATE players SET current_xp = current_xp + %s WHERE id = %s"
    execute_update(query, (actual_amount, player_id))

def record_deal(player_id, profit):
    """Зафиксировать сделку и прибыль"""
    query = """
        UPDATE players 
        SET total_deals = total_deals + 1, total_profit = total_profit + %s 
        WHERE id = %s
    """
    execute_update(query, (profit, player_id))

def check_level_up(player_id):
    """Проверить, можно ли повысить уровень. Возвращает (success, message)"""
    current_day = get_current_day(player_id)
    level, xp, deals, profit, _ = get_player_stats(player_id)

    next_cfg = get_next_level_config(level)
    if not next_cfg:
        return False, "Максимальный уровень достигнут!"

    _, req_xp, req_deals, req_profit, req_day, new_class = next_cfg

    conditions_met = (
        xp >= req_xp and
        deals >= req_deals and
        profit >= req_profit and
        current_day >= req_day
    )

    if conditions_met:
        query = """
            UPDATE players 
            SET current_level = %s, min_day_reached = %s 
            WHERE id = %s
        """
        execute_update(query, (level + 1, current_day, player_id))

        # Бонус за уровень
        bonus = 50000 * level
        from services.player_service import add_balance
        add_balance(player_id, bonus)

        class_names = {
            'basic': 'Базовые (ВАЗ)',
            'budget': 'Бюджетные (Rio, Solaris, Vesta)',
            'mid': 'Средний класс (Camry, Mazda 6)',
            'premium': 'Премиум (BMW, Mercedes)',
            'luxury': 'Люкс (S-Class, Ferrari)'
        }

        return True, f"🎉 Уровень {level + 1}! Открыт класс: {class_names.get(new_class, new_class)}. Бонус: {bonus:,} ₽"

    return False, None

def get_level_progress(player_id):
    """Получить прогресс до следующего уровня"""
    level, xp, deals, profit, min_day = get_player_stats(player_id)
    next_cfg = get_next_level_config(level)

    if not next_cfg:
        return {
            'is_max': True,
            'current_level': level,
            'progress': 100,
            'xp': xp,
            'req_xp': xp,
            'deals': deals,
            'req_deals': deals,
            'profit': profit,
            'req_profit': profit,
            'current_day': get_current_day(player_id),
            'req_day': min_day,
            'next_class': None
        }

    _, req_xp, req_deals, req_profit, req_day, next_class = next_cfg

    progress = min(100, int((xp / req_xp) * 100)) if req_xp > 0 else 100

    return {
        'is_max': False,
        'current_level': level,
        'next_level': level + 1,
        'xp': xp,
        'req_xp': req_xp,
        'deals': deals,
        'req_deals': req_deals,
        'profit': profit,
        'req_profit': req_profit,
        'current_day': get_current_day(player_id),
        'req_day': req_day,
        'progress': progress,
        'next_class': next_class
    }