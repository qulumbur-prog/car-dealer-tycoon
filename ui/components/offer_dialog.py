import flet as ft
from ui.theme import COLORS, get_condition_color, make_border
from services.game_service import get_offer_details, accept_offer, reject_offer, counter_offer
from services.player_service import add_balance
from services.reputation_service import on_quick_sale, change_reputation
from database import execute_update  # ⭐ Добавили этот импорт

def show_offer_dialog(page: ft.Page, offer_id: int, player_id: int, on_response: callable, refresh_balance: callable):
    """Показать диалог с предложением от покупателя"""
    print(f"Открываем предложение ID: {offer_id}")

    offer = get_offer_details(offer_id)
    if not offer:
        print("Предложение не найдено!")
        return

    (oid, car_id, offered_price, status, selling_price, market_val, purchase_price,
     brand, model, gen, year, mileage) = offer

    # Текущая договорная цена
    current_deal_price = [offered_price]

    # Поле для ввода встречного предложения
    counter_field = ft.TextField(
        label="Ваше встречное предложение (₽)",
        value=str(offered_price),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200
    )

    # Текст с текущей ценой продажи
    deal_price_text = ft.Text(
        f"К продаже: {offered_price:,} ₽",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=COLORS["success"]
    )

    def close_dialog(e=None):
        dialog.open = False
        page.update()

    def on_accept(e):
        """Принять текущую цену"""
        final_price = current_deal_price[0]

        success, message = accept_offer(offer_id, final_price)

        if success:
            add_balance(player_id, final_price)

            # ⭐ Бонус за быструю продажу
            from services.game_service import get_current_day
            current_day = get_current_day(player_id)

            # Получаем день выставления
            query = "SELECT listed_day FROM cars WHERE id = %s"
            from database import execute_query
            res = execute_query(query, (car_id,))
            listed_day = res[0][0] if res else current_day - 1
            days_on_market = current_day - listed_day

            new_rep, quick_bonus = on_quick_sale(player_id, days_on_market)

            # ⭐ Добавляем в статистику
            query = "UPDATE players SET total_cars_sold = total_cars_sold + 1 WHERE id = %s"
            execute_update(query, (player_id,))

            # ⭐ Бонус за честную сделку
            query = "SELECT market_value, purchase_price FROM cars WHERE id = %s"
            res = execute_query(query, (car_id,))
            if res:
                market_val, purchase_price = res[0]
                profit = final_price - purchase_price
                from services.level_service import record_deal
                record_deal(player_id, profit)

        close_dialog()

        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=COLORS["success"] if success else COLORS["danger"]
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

        if success:
            on_response()
            refresh_balance()

    def on_reject(e):
        """Отклонить предложение"""
        print(f"Отклоняем предложение ID: {offer_id}")

        success, message = reject_offer(offer_id)

        close_dialog()

        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=COLORS["warning"]
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

        if success:
            on_response()

    def on_counter(e):
        """Предложить встречную цену"""
        try:
            counter_price = int(counter_field.value.replace(' ', '').replace(',', ''))
        except ValueError:
            snack = ft.SnackBar(
                content=ft.Text("Введите корректную цену!"),
                bgcolor=COLORS["danger"]
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        print(f"Предлагаем встречную цену: {counter_price}")

        # Логика торга при продаже (аналогично покупке)
        if counter_price <= offered_price:
            # Покупатель согласится, если цена ниже или равна его предложению
            final_price = counter_price
            message = f"Покупатель согласился на {final_price:,} ₽!"
            success = True
        elif counter_price <= offered_price * 1.10:
            # Компромисс: покупатель уступает половину
            compromise = (counter_price - offered_price) / 2
            final_price = int(offered_price + compromise)
            message = f"Покупатель готов заплатить {final_price:,} ₽"
            success = True
        else:
            message = f"Покупатель отклонил ваше предложение. Слишком дорого!"
            success = False
            final_price = offered_price

        if success:
            current_deal_price[0] = final_price
            counter_field.value = str(final_price)
            deal_price_text.value = f"К продаже: {final_price:,} ₽"
            page.update()

        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=COLORS["success"] if success else COLORS["warning"]
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # Рассчитываем прибыль
    profit = current_deal_price[0] - purchase_price
    profit_color = COLORS["success"] if profit > 0 else COLORS["danger"]
    profit_text = f"+{profit:,}" if profit > 0 else f"{profit:,}"

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"💰 Предложение от покупателя", size=24, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([
                ft.Text(f"{brand} {model} {gen}", size=18, weight=ft.FontWeight.BOLD,
                       color=COLORS["accent"]),
                ft.Text(f"{year} год • {mileage:,} км", size=14, color=COLORS["text_secondary"]),

                ft.Divider(),

                ft.Row([
                    ft.Column([
                        ft.Text("Вы просили", size=11, color=COLORS["text_muted"]),
                        ft.Text(f"{selling_price:,} ₽", size=18, weight=ft.FontWeight.BOLD,
                               color=COLORS["text_secondary"])
                    ]),
                    ft.Column([
                        ft.Text("Покупатель предлагает", size=11, color=COLORS["text_muted"]),
                        ft.Text(f"{offered_price:,} ₽", size=22, weight=ft.FontWeight.BOLD,
                               color=COLORS["success"])
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                ft.Divider(),

                ft.Container(
                    content=ft.Row([
                        ft.Text("Ваша прибыль:", size=14, color=COLORS["text_muted"]),
                        ft.Text(f"{profit_text} ₽", size=18, weight=ft.FontWeight.BOLD,
                               color=profit_color)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(10, 10, 10, 10),
                    bgcolor="#1A1A2A",
                    border_radius=8
                ),

                ft.Divider(),

                ft.Text("💬 Торговаться:", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    counter_field,
                    ft.ElevatedButton(
                        "Предложить",
                        bgcolor=COLORS["accent"],
                        color="#000000",
                        on_click=on_counter
                    )
                ], spacing=10),

                ft.Container(
                    content=ft.Row([
                        ft.Text("Итог:", size=14, color=COLORS["text_muted"]),
                        deal_price_text
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding(10, 10, 10, 10),
                    bgcolor="#1A1A2A",
                    border_radius=8,
                    margin=ft.Margin(top=10)
                )

            ], spacing=10, tight=True),
            width=600,
            padding=20
        ),
        actions=[
            ft.TextButton("Отклонить", on_click=on_reject),
            ft.ElevatedButton(
                "Принять",
                bgcolor=COLORS["success"],
                color="#000000",
                on_click=on_accept
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page._sell_dialog = dialog # Сохраняем ссылку
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
    print("Диалог предложения открыт!")