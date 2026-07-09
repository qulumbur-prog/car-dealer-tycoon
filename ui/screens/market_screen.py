import flet as ft
from ui.theme import COLORS
from ui.components.car_card import create_car_card
from ui.components.car_details import show_car_details
from services.car_service import get_market_cars, get_available_brands, get_market_cars_count
from services.level_service import get_unlocked_classes

def create_market_screen(page: ft.Page, player_id: int, refresh_balance: callable, allowed_classes=None):
    """Создать экран рынка с фильтрами"""

    if allowed_classes is None:
        allowed_classes = ['basic']

    # === ФИЛЬТРЫ ===
    brand_dropdown = ft.Dropdown(
        label="Марка",
        width=150,
        options=[ft.dropdown.Option("Все")]
    )

    brands = get_available_brands(allowed_classes)
    brand_dropdown.options.extend([ft.dropdown.Option(brand) for brand in brands])

    min_price_field = ft.TextField(label="Мин. цена", keyboard_type=ft.KeyboardType.NUMBER, width=120)
    max_price_field = ft.TextField(label="Макс. цена", keyboard_type=ft.KeyboardType.NUMBER, width=120)
    min_year_field = ft.TextField(label="От года", keyboard_type=ft.KeyboardType.NUMBER, width=100)
    max_year_field = ft.TextField(label="До года", keyboard_type=ft.KeyboardType.NUMBER, width=100)

    def get_filters():
        filters = {}
        if brand_dropdown.value and brand_dropdown.value != "Все":
            filters['brand'] = brand_dropdown.value
        if min_price_field.value:
            try: filters['min_price'] = int(min_price_field.value.replace(' ', ''))
            except ValueError: pass
        if max_price_field.value:
            try: filters['max_price'] = int(max_price_field.value.replace(' ', ''))
            except ValueError: pass
        if min_year_field.value:
            try: filters['min_year'] = int(min_year_field.value)
            except ValueError: pass
        if max_year_field.value:
            try: filters['max_year'] = int(max_year_field.value)
            except ValueError: pass
        return filters

    header = ft.Text(
        "🚗 Рынок автомобилей",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text_primary"],
    )

    # Индикатор доступных классов
    class_names = {
        'basic': '🚙 Базовые',
        'budget': '🚗 Бюджетные',
        'mid': '🚘 Средний класс',
        'premium': '💎 Премиум',
        'luxury': '👑 Люкс'
    }
    available_text = ", ".join([class_names.get(c, c) for c in allowed_classes])
    class_info = ft.Text(
        f"Доступные классы: {available_text}",
        size=12,
        color=COLORS["accent"]
    )

    filters_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                brand_dropdown,
                min_price_field,
                max_price_field,
                min_year_field,
                max_year_field,
                ft.ElevatedButton("🔍 Применить", bgcolor=COLORS["accent"], color="#000000", on_click=lambda e: apply_filters()),
                ft.ElevatedButton("Сбросить", bgcolor=COLORS["text_muted"], color="#000000", on_click=lambda e: reset_filters())
            ], wrap=True),
        ]),
        padding=ft.Padding(15, 15, 15, 15),
        bgcolor=COLORS["bg_card"],
        border_radius=12,
        margin=ft.Margin(bottom=10)
    )

    cars_grid = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=350,
        child_aspect_ratio=0.75,
        spacing=15,
        run_spacing=15,
    )

    info_text = ft.Text("", size=14, color=COLORS["text_muted"])

    def apply_filters():
        brand_dropdown.options = [ft.dropdown.Option("Все")]
        brands = get_available_brands(allowed_classes)
        brand_dropdown.options.extend([ft.dropdown.Option(brand) for brand in brands])
        load_cars()

    def reset_filters():
        brand_dropdown.value = "Все"
        min_price_field.value = ""
        max_price_field.value = ""
        min_year_field.value = ""
        max_year_field.value = ""
        load_cars()

    def load_cars(e=None):
        cars_grid.controls.clear()

        filters = get_filters()
        cars = get_market_cars(limit=50, offset=0, filters=filters, allowed_classes=allowed_classes)
        total_cars = get_market_cars_count(filters, allowed_classes)

        if not cars:
            cars_grid.controls.append(
                ft.Text("Нет машин по выбранным фильтрам...", color=COLORS["text_muted"], size=16)
            )
            info_text.value = "Показано 0 из 0"
        else:
            for car in cars:
                car_id = car[0]

                def on_card_click(cid=car_id):
                    show_car_details(page, cid, player_id, load_cars, refresh_balance)

                card = create_car_card(car, on_card_click)
                card.scale = 1
                card.opacity = 1
                cars_grid.controls.append(card)

            info_text.value = f"Найдено {total_cars} машин"

        page.update()

    load_cars()

    return ft.Column([
        header,
        class_info,
        filters_panel,
        info_text,
        cars_grid
    ], expand=True), load_cars