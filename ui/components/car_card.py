import flet as ft
from ui.theme import COLORS, get_condition_color, make_border

def create_car_card(car_data, on_click):
    """Создать карточку машины"""
    car_id, brand, model, gen, year, mileage, price, color, engine_cond, has_accident = car_data

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text(f"{brand} {model}", size=18, weight=ft.FontWeight.BOLD,
                       color=COLORS["text_primary"]),
                ft.Container(
                    content=ft.Text(gen, size=10, color="#000000"),
                    bgcolor=COLORS["accent"],
                    border_radius=4,
                    padding=ft.Padding(6, 2, 6, 2)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Text(f"{year} • {mileage:,} км", size=14, color=COLORS["text_secondary"]),
            ft.Text(color, size=13, color=COLORS["text_muted"]),

            ft.Divider(height=20, color=COLORS["border"]),

            ft.Row([
                ft.Column([
                    ft.Text("Цена", size=11, color=COLORS["text_muted"]),
                    ft.Text(f"{price:,} ₽", size=20, weight=ft.FontWeight.BOLD,
                           color=COLORS["success"])
                ]),
                ft.Column([
                    ft.Text("Двигатель", size=11, color=COLORS["text_muted"]),
                    ft.Text(f"{engine_cond}/100", size=16, weight=ft.FontWeight.BOLD,
                           color=get_condition_color(engine_cond))
                ], alignment=ft.CrossAxisAlignment.END)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Container(
                content=ft.Text("⚠️ БИТАЯ", size=11, weight=ft.FontWeight.BOLD,
                               color=COLORS["text_primary"]),
                bgcolor=COLORS["danger"],
                border_radius=4,
                padding=ft.Padding(8, 4, 8, 4),
                visible=has_accident,
                margin=ft.Margin(top=8)
            )
        ], spacing=5),

        border_radius=12,
        padding=15,
        bgcolor=COLORS["bg_card"],
        border=make_border(1, COLORS["border"]),
        ink=True,
        on_click=lambda e: on_click(),  # Упростили вызов
        # Убрали анимацию, чтобы карточка сразу была активной
    )