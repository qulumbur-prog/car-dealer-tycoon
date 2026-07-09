from database import execute_query

def debug_offers(player_id=1):
    """Проверить состояние машин и предложений"""

    print("=== Машины игрока ===")
    query = """
        SELECT id, status, selling_price, listed_day, owner_id
        FROM cars
        WHERE owner_id = %s
    """
    cars = execute_query(query, (player_id,))
    for car in cars:
        print(f"ID: {car[0]}, Статус: {car[1]}, Цена: {car[2]}, День: {car[3]}, Владелец: {car[4]}")

    print("\n=== Машины на продаже ===")
    query = """
        SELECT id, selling_price, listed_day
        FROM cars
        WHERE owner_id = %s AND status = 'selling'
    """
    selling = execute_query(query, (player_id,))
    print(f"Найдено машин на продаже: {len(selling)}")
    for car in selling:
        print(f"ID: {car[0]}, Цена: {car[1]}, День выставления: {car[2]}")

    print("\n=== Предложения ===")
    query = """
        SELECT id, car_id, offered_price, status, created_day
        FROM offers
        WHERE player_id = %s
    """
    offers = execute_query(query, (player_id,))
    print(f"Всего предложений: {len(offers)}")
    for offer in offers:
        print(f"ID: {offer[0]}, Машина: {offer[1]}, Цена: {offer[2]}, Статус: {offer[3]}, День: {offer[4]}")

if __name__ == "__main__":
    debug_offers()