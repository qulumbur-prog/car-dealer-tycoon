import flet as ft
from ui.theme import COLORS

def create_loading_overlay():
    """Создает оверлей с анимацией загрузки"""

    spinner = ft.ProgressRing(
        color=COLORS["accent"],
        bgcolor=COLORS["border"],
        stroke_width=5,
        width=60,
        height=60
    )

    loading_text = ft.Text(
        "Обработка...",
        size=16,
        color=COLORS["text_primary"],
        weight=ft.FontWeight.BOLD
    )

    # Используем Stack, чтобы быть поверх всего
    overlay = ft.Stack([
        ft.Container(
            content=ft.Column([
                spinner,
                ft.Container(height=10),
                loading_text
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER),

            bgcolor="#000000CC", # Более непрозрачный фон
            expand=True,
        )
    ], expand=True, visible=False)

    return overlay

def show_loading(page: ft.Page):
    """Показать оверлей загрузки"""
    if hasattr(page, '_loading_overlay'):
        page._loading_overlay.visible = True
        # Важно: обновляем страницу, чтобы изменения применились
        page.update()

def hide_loading(page: ft.Page):
    """Скрыть оверлей загрузки"""
    if hasattr(page, '_loading_overlay'):
        page._loading_overlay.visible = False
        page.update()