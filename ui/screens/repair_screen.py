import flet as ft
from ui.theme import COLORS, get_condition_color, make_border
from services.repair_service import get_applicable_repairs, get_car_repair_status, repair_node
from services.car_service import get_car_details
from ui.components.loading_overlay import create_loading_overlay, show_loading, hide_loading

def create_repair_screen(page: ft.Page, player_id: int, car_id: int, on_back: callable, refresh_balance: callable):
    """Создать экран ремонта для конкретной машины"""

    car = get_car_details(car_id)
    if not car:
        return ft.Text("Машина не найдена", color=COLORS["danger"])

    (cid, brand, model, gen, year, mileage, price, market_val, color_ext, color_int,
     engine_cond, trans_cond, susp_cond, paint_cond, int_cond,
     has_acc, acc_count, service_hist, owners, vin) = car

    header = ft.Text(
        f"🔧 Ремонт: {brand} {model} {gen}",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text_primary"],
    )

    car_info = ft.Text(
        f"{year} • {mileage:,} км • {color_ext}",
        size=14,
        color=COLORS["text_secondary"],
    )

    status_container = ft.Container()

    def update_status():
        """Обновить отображение состояния узлов"""
        status = get_car_repair_status(car_id)
        if not status:
            return

        status_container.content = ft.Column([
            ft.Text("Текущее состояние:", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
            ft.Row([
                _create_status_card("🔥 Двигатель", status['engine']),
                _create_status_card("⚙️ КПП", status['transmission']),
                _create_status_card("🛞 Подвеска", status['suspension']),
                _create_status_card("🎨 Кузов", status['paint']),
                _create_status_card("💺 Салон", status['interior'])
            ], spacing=15, wrap=True)
        ], spacing=10)
        page.update()

    def _create_status_card(label, value):
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=12, color=COLORS["text_muted"]),
                ft.Text(f"{value}/100", size=24, weight=ft.FontWeight.BOLD,
                       color=get_condition_color(value))
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(15, 15, 15, 15),
            bgcolor=COLORS["bg_card"],
            border=make_border(1, COLORS["border"]),
            border_radius=8,
            width=150
        )

    repairs_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=400,
        child_aspect_ratio=0.6,
        spacing=15,
        run_spacing=15,
    )

    def load_repairs(e=None):
        """Загрузить список доступных ремонтов (только подходящих для этой машины!)"""
        repairs_grid.controls.clear()

        # Используем новую функцию с фильтрацией
        repairs = get_applicable_repairs(car_id)

        if not repairs:
            repairs_grid.controls.append(
                ft.Text("Для этой машины нет доступных работ.",
                       color=COLORS["text_muted"], size=16)
            )
            return

        current_node = None

        for repair in repairs:
            repair_id, name, description, node_type, cost, improvement, repair_time = repair

            # Заголовок категории
            if node_type != current_node:
                current_node = node_type
                category_names = {
                    'engine': '🔥 Двигатель',
                    'transmission': '⚙️ Трансмиссия',
                    'suspension': '🛞 Подвеска',
                    'paint': '🎨 Кузов',
                    'interior': '💺 Салон'
                }
                repairs_grid.controls.append(
                    ft.Container(
                        content=ft.Text(category_names.get(node_type, node_type),
                                      size=20, weight=ft.FontWeight.BOLD,
                                      color=COLORS["accent"]),
                        col=3
                    )
                )

            card = ft.Container(
                content=ft.Column([
                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
                    ft.Text(description, size=12, color=COLORS["text_muted"]),

                    ft.Divider(height=15, color=COLORS["border"]),

                    ft.Row([
                        ft.Column([
                            ft.Text("Стоимость", size=11, color=COLORS["text_muted"]),
                            ft.Text(f"{cost:,} ₽", size=18, weight=ft.FontWeight.BOLD,
                                   color=COLORS["danger"])
                        ]),
                        ft.Column([
                            ft.Text("Улучшение", size=11, color=COLORS["text_muted"]),
                            ft.Text(f"+{improvement}", size=18, weight=ft.FontWeight.BOLD,
                                   color=COLORS["success"])
                        ], alignment=ft.CrossAxisAlignment.END)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                    ft.Text(f"⏱️ {repair_time} дн.", size=12, color=COLORS["text_muted"]),

                    ft.ElevatedButton(
                        "Выполнить ремонт",
                        bgcolor=COLORS["accent"],
                        color="#000000",
                        on_click=lambda e, rid=repair_id, rname=name: on_repair(rid, rname),
                        expand=True
                    )
                ], spacing=8),

                border_radius=12,
                padding=15,
                bgcolor=COLORS["bg_card"],
                border=make_border(1, COLORS["border"]),
            )

            repairs_grid.controls.append(card)

    def on_repair(repair_id, repair_name):
        print(f"Выполняем ремонт: {repair_name} (ID: {repair_id})")

        # ⭐ Включаем загрузку
        show_loading(page)

        try:
            success, message, new_condition, new_achievements = repair_node(car_id, repair_id, player_id)
        finally:
            # ⭐ Выключаем загрузку
            hide_loading(page)

        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=COLORS["success"] if success else COLORS["danger"]
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

        if success:
            update_status()
            refresh_balance()
            load_repairs()

            if new_achievements:
                import time
                for ach in new_achievements:
                    time.sleep(0.3)
                    from ui.components.car_details import show_achievement_popup
                    show_achievement_popup(page, ach)

    # Кнопка возврата — теперь просто вызываем on_back
    back_btn = ft.ElevatedButton(
        "← Назад в гараж",
        bgcolor=COLORS["text_muted"],
        color="#000000",
        on_click=lambda e: on_back()
    )

    update_status()
    load_repairs()

    return ft.Column([
        ft.Row([back_btn, ft.Container(expand=True)]),
        header,
        car_info,
        ft.Divider(),
        status_container,
        ft.Divider(),
        ft.Text("Доступные работы:", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
        repairs_grid
    ], expand=True)