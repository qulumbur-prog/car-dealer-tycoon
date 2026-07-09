import flet as ft
from ui.theme import apply_theme
from ui.components.top_bar import create_top_bar
from ui.screens.market_screen import create_market_screen
from ui.screens.garage_screen import create_garage_screen
from ui.screens.repair_screen import create_repair_screen
from ui.screens.achievements_screen import create_achievements_screen
from services.car_service import refresh_market_listings
from services.level_service import get_unlocked_classes
from ui.components.loading_overlay import create_loading_overlay, show_loading, hide_loading

PLAYER_ID = 1

def main(page: ft.Page):
    page.title = "Car Dealer Tycoon 2026"
    apply_theme(page)

    # Контейнеры
    content_container = ft.Container(expand=True)
    refresh_balance_ref = [None]
    set_screen_refresh_ref = [None]

    # === ГЛОБАЛЬНЫЙ ОВЕРЛЕЙ ЗАГРУЗКИ ===
    loading_spinner = ft.ProgressRing(
        color="#FFD700",
        bgcolor="#333333",
        stroke_width=5,
        width=60,
        height=60
    )

    loading_text = ft.Text("Обработка...", size=18, color="#FFFFFF", weight=ft.FontWeight.BOLD)

    global_overlay = ft.Container(
        content=ft.Column([
            loading_spinner,
            ft.Container(height=15),
            loading_text
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER),

        bgcolor="#000000CC",
        expand=True,
        visible=False,
    )

    # Функции управления загрузкой
    def show_loading():
        global_overlay.visible = True
        page.update()

    def hide_loading():
        global_overlay.visible = False
        page.update()

    page.show_loading = show_loading
    page.hide_loading = hide_loading
    # ==============================

    def show_market(e=None):
        allowed = get_unlocked_classes(PLAYER_ID)
        market_content, load_cars = create_market_screen(page, PLAYER_ID, refresh_balance_ref[0], allowed)
        content_container.content = market_content
        if set_screen_refresh_ref[0]:
            set_screen_refresh_ref[0](load_cars)
        page.update()

    def show_garage(e=None):
        garage_content, load_cars = create_garage_screen(page, PLAYER_ID, refresh_balance_ref[0], show_repair)
        content_container.content = garage_content
        if set_screen_refresh_ref[0]:
            set_screen_refresh_ref[0](load_cars)
        page.update()

    def show_repair(car_id):
        repair_content = create_repair_screen(page, PLAYER_ID, car_id, show_garage, refresh_balance_ref[0])
        content_container.content = repair_content
        if set_screen_refresh_ref[0]:
            set_screen_refresh_ref[0](None)
        page.update()

    def show_achievements(e=None):
        ach_content, load_ach = create_achievements_screen(page, PLAYER_ID)
        content_container.content = ach_content
        if set_screen_refresh_ref[0]:
            set_screen_refresh_ref[0](None)
        page.update()

    top_bar, refresh_balance, set_screen_refresh = create_top_bar(
        page, PLAYER_ID, show_market, show_garage, show_achievements
    )
    refresh_balance_ref[0] = refresh_balance
    set_screen_refresh_ref[0] = set_screen_refresh

    # Используем Stack. global_overlay добавлен ВТОРЫМ, значит он будет ПОВЕРХ.
    root_stack = ft.Stack([
        ft.Column([top_bar, content_container], expand=True),
        global_overlay
    ], expand=True)

    page.add(root_stack)

    refresh_market_listings(limit=12)
    show_market()

if __name__ == "__main__":
    ft.run(main)