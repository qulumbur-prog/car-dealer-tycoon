from database import execute_query, execute_update, execute_insert
import random

# Пул всех возможных событий с шансами
EVENTS_POOL = [
    # === ЭКОНОМИЧЕСКИЕ ===
    {
        'type': 'market_crash',
        'description': '📉 Экономический кризис! Цены на рынке упали на 15%',
        'effect_type': 'price',
        'effect_value': 0.85,
        'target_class': 'all',
        'days': 3,
        'weight': 15
    },
    {
        'type': 'market_boom',
        'description': '📈 Экономический бум! Цены на рынке выросли на 10%',
        'effect_type': 'price',
        'effect_value': 1.10,
        'target_class': 'all',
        'days': 2,
        'weight': 10
    },

    # === КЛАССОВЫЕ ===
    {
        'type': 'premium_demand',
        'description': '💎 Ажиотаж на премиум! BMW и Mercedes +20% к цене',
        'effect_type': 'price',
        'effect_value': 1.20,
        'target_class': 'premium',
        'days': 3,
        'weight': 12
    },
    {
        'type': 'suv_season',
        'description': '🚙 Сезон кроссоверов! Sportage, RAV4, Tiguan +15%',
        'effect_type': 'price',
        'effect_value': 1.15,
        'target_class': 'mid',
        'days': 3,
        'weight': 12
    },
    {
        'type': 'budget_drop',
        'description': '🚗 Бюджетные машины подешевели на 10%',
        'effect_type': 'price',
        'effect_value': 0.90,
        'target_class': 'budget',
        'days': 2,
        'weight': 10
    },
    {
        'type': 'luxury_rare',
        'description': '👑 Инвестор в городе! Люкс-машины +25%',
        'effect_type': 'price',
        'effect_value': 1.25,
        'target_class': 'luxury',
        'days': 2,
        'weight': 8
    },

    # === РЕМОНТ ===
    {
        'type': 'parts_shortage',
        'description': '🔧 Дефицит запчастей! Ремонт дороже на 30%',
        'effect_type': 'repair_cost',
        'effect_value': 1.30,
        'target_class': 'all',
        'days': 3,
        'weight': 10
    },
    {
        'type': 'parts_sale',
        'description': '🛠️ Распродажа запчастей! Ремонт дешевле на 20%',
        'effect_type': 'repair_cost',
        'effect_value': 0.80,
        'target_class': 'all',
        'days': 2,
        'weight': 8
    },

    # === ОПЫТ ===
    {
        'type': 'xp_boost',
        'description': '⭐ Удача новичка! Двойной опыт на 2 дня',
        'effect_type': 'xp',
        'effect_value': 2.0,
        'target_class': 'all',
        'days': 2,
        'weight': 8
    },

    # === ДЕНЬГИ ===
    {
        'type': 'tax',
        'description': '💸 Налоговая проверка! Списано 50,000 ₽',
        'effect_type': 'money',
        'effect_value': -50000,
        'target_class': 'all',
        'days': 1,
        'weight': 7
    },
    {
        'type': 'bonus',
        'description': '🎁 Государственная субсидия! +30,000 ₽ на счёт',
        'effect_type': 'money',
        'effect_value': 30000,
        'target_class': 'all',
        'days': 1,
        'weight': 5
    },

    # === ПОКУПАТЕЛИ ===
    {
        'type': 'buyer_boom',
        'description': '🤝 Сезон покупателей! Больше предложений на ваши машины',
        'effect_type': 'offer_chance',
        'effect_value': 1.5,
        'target_class': 'all',
        'days': 3,
        'weight': 10
    },
    {
        'type': 'buyer_drought',
        'description': '😴 Мёртвый сезон. Покупатели редкость...',
        'effect_type': 'offer_chance',
        'effect_value': 0.6,
        'target_class': 'all',
        'days': 2,
        'weight': 8
    },
]

def get_active_events():
    """Получить все активные события"""
    query = """
        SELECT id, event_type, description, effect_type, effect_value, 
               target_class, days_remaining, created_day
        FROM active_events
        WHERE days_remaining > 0
        ORDER BY created_day DESC
    """
    return execute_query(query)

def get_event_modifier(effect_type, target_class='all'):
    """Получить суммарный модификатор для эффекта и класса"""
    events = get_active_events()
    modifier = 1.0

    for event in events:
        _, _, _, e_type, e_value, e_class, _, _ = event
        if e_type == effect_type and (e_class == 'all' or e_class == target_class):
            modifier *= e_value

    return modifier

def generate_daily_event(current_day, player_id):
    """
    С шансом 10% сгенерировать новое событие.
    Возвращает (event_description, is_new) или (None, False)
    """
    # 10% шанс
    if random.random() > 0.10:
        return None, False

    # Нельзя иметь больше 2 активных событий одновременно
    active = get_active_events()
    if len(active) >= 2:
        return None, False

    # Выбираем случайное событие по весам
    weights = [e['weight'] for e in EVENTS_POOL]
    event = random.choices(EVENTS_POOL, weights=weights, k=1)[0]

    # Не дублировать уже активные события того же типа
    active_types = [e[1] for e in active]
    if event['type'] in active_types:
        return None, False

    # Применяем мгновенные эффекты
    if event['effect_type'] == 'money':
        from services.player_service import add_balance
        add_balance(player_id, int(event['effect_value']))

    # Сохраняем событие
    query = """
        INSERT INTO active_events 
        (event_type, description, effect_type, effect_value, target_class, days_remaining, created_day)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    execute_update(query, (
        event['type'],
        event['description'],
        event['effect_type'],
        event['effect_value'],
        event['target_class'],
        event['days'],
        current_day
    ))

    return event['description'], True

def tick_events():
    """Уменьшить длительность всех активных событий на 1 день"""
    query = "UPDATE active_events SET days_remaining = days_remaining - 1"
    execute_update(query)

    # Удаляем истёкшие
    query = "DELETE FROM active_events WHERE days_remaining <= 0"
    execute_update(query)