from database import execute_query, execute_update

def get_player(player_id):
    """Получить информацию об игроке"""
    query = """
        SELECT id, username, balance, experience, level, reputation
        FROM players
        WHERE id = %s
    """
    result = execute_query(query, (player_id,))
    return result[0] if result else None

def get_player_balance(player_id):
    """Получить баланс игрока"""
    player = get_player(player_id)
    return player[2] if player else 0

def deduct_balance(player_id, amount):
    """Списать деньги с баланса"""
    query = """
        UPDATE players
        SET balance = balance - %s
        WHERE id = %s AND balance >= %s
    """
    execute_update(query, (amount, player_id, amount))

def add_balance(player_id, amount):
    """Добавить деньги на баланс"""
    query = """
        UPDATE players
        SET balance = balance + %s
        WHERE id = %s
    """
    execute_update(query, (amount, player_id))