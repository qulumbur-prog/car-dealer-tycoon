import flet as ft
from ui.theme import COLORS, get_condition_color, make_border
from services.car_service import get_player_cars, sell_car
from ui.components.loading_overlay import create_loading_overlay, show_loading, hide_loading

def create_garage_screen(page: ft.Page, player_id: int, refresh_balance: callable, on_navigate_to_repair: callable = None):
    """Создать экран гаража"""

    header = ft.Text(
        "🏠 Мой гараж",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text_primary"],
    )

    cars_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=350,
        child_aspect_ratio=0.85,
        spacing=15,
        run_spacing=15,
    )

    def load_cars(e=None):
        cars_grid.controls.clear()
        cars = get_player_cars(player_id)

        if not cars:
            cars_grid.controls.append(
                ft.Text("У вас пока нет машин. Купите первую на рынке!",
                       color=COLORS["text_muted"], size=16)
            )
            return

        for car in cars:
            card = create_owned_car_card(car, page, player_id, load_cars, refresh_balance, on_navigate_to_repair)
            cars_grid.controls.append(card)

    def create_owned_car_card(car_data, page, player_id, on_refresh, refresh_balance, on_navigate_to_repair):
        car_id, brand, model, gen, year, mileage, market_val, color, engine_cond, purchase_price, status, selling_price, listed_day = car_data

        profit = market_val - purchase_price
        profit_color = COLORS["success"] if profit > 0 else COLORS["danger"]
        profit_text = f"+{profit:,}" if profit > 0 else f"{profit:,}"

        is_selling = status == 'selling'

        def on_sell(e):
            # ⭐ Сначала закрываем диалог, если он открыт!
            if hasattr(page, '_sell_dialog') and page._sell_dialog.open:
                page._sell_dialog.open = False

            show_loading(page) # Включаем спиннер

            try:
                success, message, new_achievements, rep_change = sell_car(car_id, player_id, market_val)
            finally:
                hide_loading(page) # Выключаем спиннер

            snack = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=COLORS["success"] if success else COLORS["danger"]
            )
            page.overlay.append(snack)
            snack.open = True

            if success:
                if new_achievements:
                    import time
                    for ach in new_achievements:
                        time.sleep(0.3)
                        from ui.components.car_details import show_achievement_popup
                        show_achievement_popup(page, ach)

                on_refresh() # Обновляем список машин

            page.update() # Обязательно обновляем страницу в конце

        def on_repair(e):
            """Открыть экран ремонта через навигацию"""
            if on_navigate_to_repair:
                on_navigate_to_repair(car_id)

        if is_selling:
            action_button = ft.Container(
                content=ft.Text("⏳ Ожидает покупателя...", size=14,
                               color=COLORS["warning"], weight=ft.FontWeight.BOLD),
                padding=ft.Padding(10, 10, 10, 10),
                bgcolor="#2A2A1A",
                border_radius=8,
                expand=True
            )
            price_info = ft.Column([
                ft.Text("Выставлена за", size=11, color=COLORS["text_muted"]),
                ft.Text(f"{selling_price:,} ₽", size=16, weight=ft.FontWeight.BOLD,
                       color=COLORS["warning"])
            ])
            repair_btn = None
        else:
            action_button = ft.ElevatedButton(
                "💰 Продать",
                bgcolor=COLORS["accent"],
                color="#000000",
                on_click=on_sell,
                expand=True
            )
            price_info = ft.Column([
                ft.Text("Рыночная", size=11, color=COLORS["text_muted"]),
                ft.Text(f"{market_val:,} ₽", size=16, weight=ft.FontWeight.BOLD,
                       color=COLORS["success"])
            ])
            repair_btn = ft.ElevatedButton(
                "🔧 Ремонт",
                bgcolor=COLORS["warning"],
                color="#000000",
                on_click=on_repair,
                expand=True
            )

        buttons_column = ft.Column([action_button], spacing=5)
        if repair_btn:
            buttons_column.controls.insert(0, repair_btn)

        return ft.Container(
            content=ft.Column([
                ft.Text(f"{brand} {model}", size=18, weight=ft.FontWeight.BOLD,
                       color=COLORS["text_primary"]),
                ft.Text(gen, size=12, color=COLORS["accent"]),

                ft.Text(f"{year} • {mileage:,} км", size=14, color=COLORS["text_secondary"]),
                ft.Text(color, size=13, color=COLORS["text_muted"]),

                ft.Divider(height=20, color=COLORS["border"]),

                ft.Row([
                    ft.Column([
                        ft.Text("Куплено за", size=11, color=COLORS["text_muted"]),
                        ft.Text(f"{purchase_price:,} ₽", size=16, weight=ft.FontWeight.BOLD)
                    ]),
                    price_info
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                ft.Container(
                    content=ft.Text(f"Потенциальная прибыль: {profit_text} ₽", size=14,
                                   weight=ft.FontWeight.BOLD, color=profit_color),
                    margin=ft.Margin(top=10)
                ),

                buttons_column
            ], spacing=5),

            border_radius=12,
            padding=15,
            bgcolor=COLORS["bg_card"],
            border=make_border(1, COLORS["border"]),
        )

    load_cars()

    return ft.Column([header, cars_grid], expand=True), load_cars