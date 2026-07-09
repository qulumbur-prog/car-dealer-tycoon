import flet as ft
from ui.theme import COLORS, get_condition_color, make_border
from services.car_service import get_car_details, negotiate_price, buy_car
from services.level_service import add_xp
from database import execute_update
from ui.components.loading_overlay import show_loading, hide_loading

def show_achievement_popup(page: ft.Page, achievement):
    """Показать всплывающее окно с достижением"""
    rewards = []
    if achievement['reward_money'] > 0:
        rewards.append(f"+{achievement['reward_money']:,} ₽")
    if achievement['reward_xp'] > 0:
        rewards.append(f"+{achievement['reward_xp']} XP")
    rewards_text = " | ".join(rewards) if rewards else ""

    dialog = ft.AlertDialog(
        modal=False,
        title=ft.Row([
            ft.Text(achievement['icon'], size=40),
            ft.Column([
                ft.Text("🏆 ДОСТИЖЕНИЕ!", size=14, weight=ft.FontWeight.BOLD, color=COLORS["accent"]),
                ft.Text(achievement['name'], size=20, weight=ft.FontWeight.BOLD)
            ])
        ], spacing=15),
        content=ft.Text(rewards_text, size=16, color=COLORS["success"]),
        actions=[
            ft.ElevatedButton("Отлично!", bgcolor=COLORS["accent"], color="#000000",
                            on_click=lambda e: close_ach_dialog())
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    def close_ach_dialog():
        dialog.open = False
        page.update()

    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_car_details(page: ft.Page, car_id: int, player_id: int, on_refresh: callable, refresh_balance: callable):
    """Показать диалог с деталями машины"""

    car = get_car_details(car_id)
    if not car:
        return

    (cid, brand, model, gen, year, mileage, price, market_val, color_ext, color_int,
     engine_cond, trans_cond, susp_cond, paint_cond, int_cond,
     has_acc, acc_count, service_hist, owners, vin) = car

    current_deal_price = [price]

    def update_price_display():
        price_value.value = f"{current_deal_price[0]:,} ₽"
        page.update()

    def on_negotiate(e):
        offered = int(negotiate_input.value.replace(' ', '')) if negotiate_input.value else 0

        if offered <= 0:
            snack = ft.SnackBar(content=ft.Text("Введите корректную сумму"), bgcolor=COLORS["danger"])
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        show_loading(page)
        try:
            success, final_price, message = negotiate_price(car_id, offered)
        finally:
            hide_loading(page)

        if success:
            current_deal_price[0] = final_price
            update_price_display()
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=COLORS["success"])
        else:
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=COLORS["warning"])

        page.overlay.append(snack)
        snack.open = True
        page.update()

    def on_buy(e):
        final_price = current_deal_price[0]

        show_loading(page)
        try:
            result = buy_car(car_id, player_id, final_price)
            success = result[0]
            message = result[1]
            new_achievements = result[2] if len(result) > 2 else []

            if success and final_price < price:
                saved = price - final_price
                query = "UPDATE players SET total_saved_on_torg = total_saved_on_torg + %s WHERE id = %s"
                execute_update(query, (saved, player_id))

                from services.achievement_service import check_achievements
                torg_achievements = check_achievements(player_id)
                new_achievements.extend(torg_achievements)
        finally:
            hide_loading(page)

        close_dialog()

        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=COLORS["success"] if success else COLORS["danger"]
        )
        page.overlay.append(snack)
        snack.open = True

        if new_achievements:
            import time
            for ach in new_achievements:
                time.sleep(0.3)
                show_achievement_popup(page, ach)

        if success:
            on_refresh()
            refresh_balance()

        page.update()

    def close_dialog():
        dialog.open = False
        for control in list(page.overlay):
            if isinstance(control, ft.AlertDialog):
                control.open = False
        page.update()

    # === Создание контента диалога (УВЕЛИЧЕННЫЕ РАЗМЕРЫ) ===
    header = ft.Column([
        ft.Text(f"{brand} {model}", size=28, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
        ft.Text(gen, size=18, color=COLORS["accent"]),
        ft.Text(f"{year} • {mileage:,} км • {color_ext}", size=16, color=COLORS["text_muted"])
    ], spacing=5)

    def _cond_item(label, value):
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=12, color=COLORS["text_muted"]),
                ft.Text(f"{value}/100", size=18, weight=ft.FontWeight.BOLD, color=get_condition_color(value))
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=100,
            padding=10,
            bgcolor="#2A2A3C",
            border_radius=8
        )

    conditions = ft.Row([
        _cond_item("🔥 Двигатель", engine_cond),
        _cond_item("⚙️ КПП", trans_cond),
        _cond_item("🛞 Подвеска", susp_cond),
        _cond_item("🎨 Кузов", paint_cond),
        _cond_item("💺 Салон", int_cond),
    ], wrap=True, spacing=15)

    price_section = ft.Container(
        content=ft.Column([
            ft.Text("Цена продавца:", size=16, color=COLORS["text_muted"]),
            price_value := ft.Text(f"{price:,} ₽", size=32, weight=ft.FontWeight.BOLD, color=COLORS["success"]),
            ft.Divider(height=20),
            ft.Row([
                negotiate_input := ft.TextField(
                    label="Ваша цена",
                    keyboard_type=ft.KeyboardType.NUMBER,
                    expand=True,
                    value=str(int(price * 0.9)),
                    text_size=16
                ),
                ft.ElevatedButton("Торг", bgcolor=COLORS["accent"], color="#000000", on_click=on_negotiate, height=50)
            ]),
            ft.ElevatedButton(
                "Купить",
                bgcolor=COLORS["success"],
                color="#000000",
                width=float('inf'),
                on_click=on_buy,
                height=50,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=18))
            )
        ], spacing=10),
        padding=20,
        bgcolor="#1A1A2A",
        border_radius=12
    )

    info_list = ft.Column([
        ft.Text(f"👤 Владельцев: {owners}", size=15),
        ft.Text(f"📄 ПТС: {'Оригинал' if owners < 3 else 'Дубликат'}", size=15),
        ft.Text(f"🚗 Аварии: {'Да' if has_acc else 'Нет'}", size=15, color=COLORS["danger"] if has_acc else COLORS["text_muted"]),
        ft.Text(f"🔧 Сервисная книжка: {'Есть' if service_hist else 'Нет'}", size=15),
    ], spacing=8)

    content_column = ft.Column([
        header,
        ft.Divider(height=20),
        ft.Text("Состояние узлов:", size=20, weight=ft.FontWeight.BOLD),
        conditions,
        ft.Divider(height=20),
        info_list,
        ft.Divider(height=20),
        price_section
    ], spacing=15, scroll=ft.ScrollMode.AUTO)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Детали автомобиля", size=24, weight=ft.FontWeight.BOLD),
        content=ft.Container(content=content_column, width=800, height=750), # ⭐ Увеличили ширину и высоту
        actions=[
            ft.TextButton("Закрыть", on_click=lambda e: close_dialog())
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )



    page.overlay.append(dialog)
    dialog.open = True
    page.update()