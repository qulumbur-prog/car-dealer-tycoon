import flet as ft

# Цветовая палитра
COLORS = {
    "bg_primary": "#1E1E2E",
    "bg_card": "#2A2A3C",
    "border": "#424242",
    "accent": "#00BCD4",
    "success": "#69F0AE",
    "danger": "#FF5252",
    "warning": "#FF9800",
    "text_primary": "#FFFFFF",
    "text_secondary": "#BDBDBD",
    "text_muted": "#9E9E9E",
}

def get_condition_color(condition):
    """Цвет для состояния узла"""
    if condition > 70:
        return ft.Colors.GREEN
    elif condition > 40:
        return ft.Colors.ORANGE
    return ft.Colors.RED

def apply_theme(page: ft.Page):
    """Применить тему к странице"""
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COLORS["bg_primary"]
    page.padding = 20
    page.window.width = 1200
    page.window.height = 800

def make_border(width=1, color=None):
    """Создать рамку для контейнера"""
    if color is None:
        color = COLORS["border"]
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)