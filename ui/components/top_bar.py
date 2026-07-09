import flet as ft
from ui.theme import COLORS
from services.player_service import get_player
from services.game_service import get_current_day, next_day, get_pending_offers
from services.level_service import get_level_progress, check_level_up
from services.event_service import get_active_events
from services.reputation_service import get_reputation, get_reputation_tier
from ui.components.offer_dialog import show_offer_dialog
from ui.components.loading_overlay import create_loading_overlay, show_loading, hide_loading

def create_top_bar(page: ft.Page, player_id: int, on_market_click, on_garage_click, on_achievements_click):
    """Создать верхнюю панель с балансом, днём, уровнем, репутацией и событиями"""

    player = get_player(player_id)
    balance = player[2] if player else 0
    current_day = get_current_day(player_id)
    progress = get_level_progress(player_id)
    reputation = get_reputation(player_id)
    rep_tier, rep_name, rep_icon = get_reputation_tier(reputation)

    # === Текстовые элементы ===
    balance_text = ft.Text(
        f"💰 {balance:,} ₽",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=COLORS["success"]
    )

    day_text = ft.Text(
        f"📅 День: {current_day}",
        size=14,
        color=COLORS["text_muted"]
    )

    # === Уровень и прогресс-бар ===
    level_text = ft.Text(
        f"⭐ Ур. {progress['current_level']}",
        size=14,
        weight=ft.FontWeight.BOLD,
        color=COLORS["accent"]
    )

    if progress['is_max']:
        xp_text = ft.Text("MAX", size=12, color=COLORS["text_muted"])
        level_bar = ft.ProgressBar(value=1.0, color=COLORS["accent"], bgcolor=COLORS["border"], height=8)
        conditions_text = ft.Text("Максимальный уровень достигнут!", size=11, color=COLORS["success"])
    else:
        xp_text = ft.Text(f"{progress['xp']}/{progress['req_xp']} XP", size=12, color=COLORS["text_muted"])
        level_bar = ft.ProgressBar(
            value=progress['progress'] / 100,
            color=COLORS["accent"],
            bgcolor=COLORS["border"],
            height=8
        )

        conditions = []
        if progress['xp'] >= progress['req_xp']:
            conditions.append(f"✅ XP: {progress['xp']}/{progress['req_xp']}")
        else:
            conditions.append(f"❌ XP: {progress['xp']}/{progress['req_xp']}")

        if progress['deals'] >= progress['req_deals']:
            conditions.append(f"✅ Сделки: {progress['deals']}/{progress['req_deals']}")
        else:
            conditions.append(f"❌ Сделки: {progress['deals']}/{progress['req_deals']}")

        if progress['profit'] >= progress['req_profit']:
            conditions.append(f"✅ Прибыль: {progress['profit']:,}/{progress['req_profit']:,} ₽")
        else:
            conditions.append(f"❌ Прибыль: {progress['profit']:,}/{progress['req_profit']:,} ₽")

        if progress['current_day'] >= progress['req_day']:
            conditions.append(f"✅ День: {progress['current_day']}/{progress['req_day']}")
        else:
            conditions.append(f"❌ День: {progress['current_day']}/{progress['req_day']}")

        conditions_text = ft.Text(" | ".join(conditions), size=11, color=COLORS["text_muted"])

    # === Репутация ===
    def get_rep_color(rep):
        if rep >= 60:
            return COLORS["success"]
        elif rep >= 40:
            return COLORS["warning"]
        return COLORS["danger"]

    reputation_text = ft.Text(
        f"{rep_icon} {rep_name} ({reputation}/100)",
        size=14,
        weight=ft.FontWeight.BOLD,
        color=get_rep_color(reputation)
    )

    reputation_bar = ft.ProgressBar(
        value=reputation / 100,
        color=get_rep_color(reputation),
        bgcolor=COLORS["border"],
        height=6
    )

    # === Callback для обновления текущего экрана ===
    current_screen_refresh = [None]

    def refresh_balance():
        nonlocal balance_text, day_text, level_text, xp_text, level_bar, conditions_text
        nonlocal reputation_text, reputation_bar, events_container

        p = get_player(player_id)
        balance_text.value = f"💰 {p[2]:,} ₽"
        day_text.value = f"📅 День: {get_current_day(player_id)}"

        # Обновляем уровень
        prog = get_level_progress(player_id)
        level_text.value = f"⭐ Ур. {prog['current_level']}"

        if prog['is_max']:
            xp_text.value = "MAX"
            level_bar.value = 1.0
            conditions_text.value = "Максимальный уровень достигнут!"
        else:
            xp_text.value = f"{prog['xp']}/{prog['req_xp']} XP"
            level_bar.value = prog['progress'] / 100

            conditions = []
            if prog['xp'] >= prog['req_xp']:
                conditions.append(f"✅ XP: {prog['xp']}/{prog['req_xp']}")
            else:
                conditions.append(f"❌ XP: {prog['xp']}/{prog['req_xp']}")

            if prog['deals'] >= prog['req_deals']:
                conditions.append(f"✅ Сделки: {prog['deals']}/{prog['req_deals']}")
            else:
                conditions.append(f"❌ Сделки: {prog['deals']}/{prog['req_deals']}")

            if prog['profit'] >= prog['req_profit']:
                conditions.append(f"✅ Прибыль: {prog['profit']:,}/{prog['req_profit']:,} ₽")
            else:
                conditions.append(f"❌ Прибыль: {prog['profit']:,}/{prog['req_profit']:,} ₽")

            if prog['current_day'] >= prog['req_day']:
                conditions.append(f"✅ День: {prog['current_day']}/{prog['req_day']}")
            else:
                conditions.append(f"❌ День: {prog['current_day']}/{prog['req_day']}")

            conditions_text.value = " | ".join(conditions)

        # ⭐ Обновляем репутацию
        rep = get_reputation(player_id)
        tier, name, icon = get_reputation_tier(rep)
        reputation_text.value = f"{icon} {name} ({rep}/100)"
        reputation_text.color = get_rep_color(rep)
        reputation_bar.value = rep / 100
        reputation_bar.color = get_rep_color(rep)

        # Обновляем события
        active_evts = get_active_events()
        if active_evts:
            events_row = ft.Row(
                [ft.Text(ev[2], size=11, color=COLORS["warning"]) for ev in active_evts],
                wrap=True
            )
            events_container.content = ft.Column([
                ft.Text("🎯 Активные события:", size=11, weight=ft.FontWeight.BOLD, color=COLORS["accent"]),
                events_row
            ], spacing=3)
            events_container.visible = True
        else:
            events_container.visible = False

        page.update()

    def set_screen_refresh(refresh_func):
        current_screen_refresh[0] = refresh_func

    def show_offers_dialog():
        offers = get_pending_offers(player_id)

        if not offers:
            snack = ft.SnackBar(
                content=ft.Text("Нет новых предложений от покупателей"),
                bgcolor=COLORS["text_muted"]
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        offer_id = offers[0][0]
        show_offer_dialog(page, offer_id, player_id, refresh_balance, refresh_balance)

    def on_next_day(e):
        # ⭐ Включаем загрузку через глобальные функции page
        page.show_loading()

        try:
            result = next_day(player_id)

            messages = [f"📅 Наступил день {result['day']}"]

            if result['new_offers']:
                messages.append(f"💰 Получено {len(result['new_offers'])} предложений!")

            if result.get('new_event'):
                snack = ft.SnackBar(
                    content=ft.Text(result['new_event'], size=14, weight=ft.FontWeight.BOLD),
                    bgcolor=COLORS["accent"],
                    duration=4000
                )
                page.overlay.append(snack)
                snack.open = True

            for msg in messages:
                snack = ft.SnackBar(
                    content=ft.Text(msg),
                    bgcolor=COLORS["success"] if "предложений" in msg else COLORS["accent"]
                )
                page.overlay.append(snack)
                snack.open = True

            leveled_up, level_msg = check_level_up(player_id)
            if leveled_up:
                snack = ft.SnackBar(
                    content=ft.Text(level_msg),
                    bgcolor=COLORS["success"]
                )
                page.overlay.append(snack)
                snack.open = True

            refresh_balance()

            if current_screen_refresh[0]:
                current_screen_refresh[0]()

            if result['new_offers']:
                import time
                time.sleep(0.5)
                show_offers_dialog()

        finally:
            # ⭐ Выключаем загрузку
            page.hide_loading()

        page.update()

        if current_screen_refresh[0]:
            current_screen_refresh[0]()

        if result['new_offers']:
            import time
            time.sleep(0.5)
            show_offers_dialog()

    # === Кнопки навигации ===
    market_btn = ft.TextButton(
        "🚗 Рынок",
        on_click=on_market_click,
        style=ft.ButtonStyle(color=COLORS["text_primary"])
    )

    garage_btn = ft.TextButton(
        "🏠 Гараж",
        on_click=on_garage_click,
        style=ft.ButtonStyle(color=COLORS["text_primary"])
    )

    achievements_btn = ft.TextButton(
        "🏆 Ачивки",
        on_click=on_achievements_click,
        style=ft.ButtonStyle(color=COLORS["text_primary"])
    )

    offers_btn = ft.ElevatedButton(
        "💰 Предложения",
        bgcolor=COLORS["warning"],
        color="#000000",
        on_click=lambda e: show_offers_dialog()
    )

    next_day_btn = ft.ElevatedButton(
        "Следующий день ⏭️",
        bgcolor=COLORS["accent"],
        color="#000000",
        on_click=on_next_day
    )

    # === Индикатор активных событий ===
    active_events = get_active_events()
    if active_events:
        events_row = ft.Row(
            [ft.Text(ev[2], size=11, color=COLORS["warning"]) for ev in active_events],
            wrap=True
        )
        events_container = ft.Container(
            content=ft.Column([
                ft.Text("🎯 Активные события:", size=11, weight=ft.FontWeight.BOLD, color=COLORS["accent"]),
                events_row
            ], spacing=3),
            padding=ft.Padding(10, 8, 10, 8),
            bgcolor="#2A2A3C",
            border_radius=8,
            border=ft.Border(
                top=ft.BorderSide(1, COLORS["accent"]),
                bottom=ft.BorderSide(1, COLORS["accent"]),
                left=ft.BorderSide(1, COLORS["accent"]),
                right=ft.BorderSide(1, COLORS["accent"]),
            )
        )
    else:
        events_container = ft.Container(visible=False)

    # === Собираем шапку ===
    top_content = ft.Column([
        # Строка 1: навигация + баланс + действия
        ft.Row([
            ft.Row([market_btn, garage_btn, achievements_btn], spacing=10),
            ft.Container(expand=True),
            balance_text,
            ft.Container(width=15),
            offers_btn,
            ft.Container(width=10),
            next_day_btn
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        # Строка 2: день + уровень + XP
        ft.Row([
            day_text,
            ft.Container(width=20),
            level_text,
            ft.Container(width=10),
            ft.Container(content=level_bar, width=200),
            ft.Container(width=10),
            xp_text
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

        # Строка 3: условия уровня
        conditions_text,

        # Строка 4: ⭐ РЕПУТАЦИЯ
        ft.Row([
            ft.Text("📊 Репутация:", size=12, color=COLORS["text_muted"]),
            reputation_text,
            ft.Container(width=10),
            ft.Container(content=reputation_bar, width=150),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),

        # Строка 5: события
        events_container
    ], spacing=8)

    return ft.Container(
        content=top_content,
        padding=ft.Padding(15, 10, 15, 10),
        bgcolor=COLORS["bg_card"],
        border_radius=12,
        margin=ft.Margin(bottom=15)
    ), refresh_balance, set_screen_refresh