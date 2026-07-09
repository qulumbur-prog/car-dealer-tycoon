import flet as ft
from ui.theme import COLORS, make_border
from services.achievement_service import get_player_achievements

def create_achievements_screen(page: ft.Page, player_id: int):
    """Создать экран достижений"""

    header = ft.Text(
        "🏆 Достижения",
        size=32,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text_primary"],
    )

    # Статистика
    stats_container = ft.Container()

    def load_stats():
        from services.level_service import get_player_stats
        level, xp, deals, profit, _ = get_player_stats(player_id)

        from database import execute_query
        q = """
            SELECT total_cars_bought, total_cars_sold, total_repair_invested, total_saved_on_torg
            FROM players WHERE id = %s
        """
        r = execute_query(q, (player_id,))
        bought, sold, repair_inv, saved_torg = r[0] if r else (0, 0, 0, 0)

        stats_container.content = ft.Container(
            content=ft.Row([
                _stat_card("🚗 Куплено", f"{bought}"),
                _stat_card("💰 Продано", f"{sold}"),
                _stat_card("📈 Прибыль", f"{profit:,} ₽"),
                _stat_card("🔧 В ремонт", f"{repair_inv:,} ₽"),
                _stat_card("🤝 Сэкономлено", f"{saved_torg:,} ₽"),
            ], wrap=True, spacing=10),
            padding=15,
            bgcolor=COLORS["bg_card"],
            border_radius=12,
            margin=ft.Margin(bottom=20)
        )

    def _stat_card(label, value):
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=11, color=COLORS["text_muted"]),
                ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(15, 10, 15, 10),
            bgcolor="#1A1A2A",
            border_radius=8,
            width=180
        )

    # Список достижений по категориям
    achievements_list = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)

    category_names = {
        'deals': '🤝 Сделки',
        'profit': '💰 Прибыль',
        'repair': '🔧 Ремонт',
        'negotiation': '💬 Торг',
        'level': '⭐ Уровни',
        'special': '✨ Особые'
    }

    def load_achievements():
        achievements_list.controls.clear()

        all_achievements = get_player_achievements(player_id)

        # Группируем по категориям
        by_category = {}
        for ach in all_achievements:
            category = ach[5]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(ach)

        # Считаем общее
        total = len(all_achievements)
        unlocked = sum(1 for a in all_achievements if a[10] is not None)

        progress_text = ft.Text(
            f"Открыто: {unlocked} из {total}",
            size=14,
            color=COLORS["accent"],
            weight=ft.FontWeight.BOLD
        )
        achievements_list.controls.append(progress_text)

        # Для каждой категории
        for category in ['deals', 'profit', 'repair', 'negotiation', 'level', 'special']:
            if category not in by_category:
                continue

            category_header = ft.Text(
                category_names.get(category, category),
                size=20,
                weight=ft.FontWeight.BOLD,
                color=COLORS["accent"]
            )
            achievements_list.controls.append(category_header)

            for ach in by_category[category]:
                ach_id, code, name, desc, icon, cat, cond_type, cond_value, reward_money, reward_xp, unlocked_day, unlocked_at = ach
                is_unlocked = unlocked_day is not None

                # Получаем текущий прогресс
                from services.achievement_service import get_player_stats_for_achievements
                stats = get_player_stats_for_achievements(player_id)

                current_value = 0
                if cond_type == 'cars_bought':
                    current_value = stats['cars_bought']
                elif cond_type == 'cars_sold':
                    current_value = stats['cars_sold']
                elif cond_type == 'total_profit':
                    current_value = stats['profit']
                elif cond_type == 'repairs_done':
                    current_value = stats['deals']
                elif cond_type == 'repair_invested':
                    current_value = stats['repair_invested']
                elif cond_type == 'saved_on_torg':
                    current_value = stats['saved_on_torg']
                elif cond_type == 'level_reached':
                    current_value = stats['level']
                elif cond_type in ('bought_premium', 'bought_luxury'):
                    current_value = 1 if is_unlocked else 0

                progress = min(1.0, current_value / cond_value) if cond_value > 0 else 1.0

                # Награды
                rewards = []
                if reward_money > 0:
                    rewards.append(f"+{reward_money:,} ₽")
                if reward_xp > 0:
                    rewards.append(f"+{reward_xp} XP")
                rewards_text = " | ".join(rewards) if rewards else ""

                card = ft.Container(
                    content=ft.Row([
                        ft.Text(icon, size=40),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD,
                                          color=COLORS["text_primary"] if is_unlocked else COLORS["text_muted"]),
                                    ft.Container(
                                        content=ft.Text("✅" if is_unlocked else "🔒", size=12),
                                        bgcolor=COLORS["success"] if is_unlocked else COLORS["border"],
                                        border_radius=4,
                                        padding=ft.Padding(6, 2, 6, 2)
                                    )
                                ]),
                                ft.Text(desc, size=12, color=COLORS["text_muted"]),
                                ft.Row([
                                    ft.Text(rewards_text, size=11, color=COLORS["success"]),
                                    ft.Container(expand=True),
                                    ft.Text(
                                        f"{min(current_value, cond_value):,}/{cond_value:,}",
                                        size=11,
                                        color=COLORS["text_muted"]
                                    )
                                ]),
                                ft.ProgressBar(
                                    value=progress,
                                    color=COLORS["success"] if is_unlocked else COLORS["accent"],
                                    bgcolor=COLORS["border"],
                                    height=6
                                )
                            ], spacing=5),
                            expand=True
                        )
                    ], spacing=15),
                    padding=15,
                    bgcolor=COLORS["bg_card"],
                    border=make_border(1, COLORS["success"] if is_unlocked else COLORS["border"]),
                    border_radius=12,
                    opacity=1.0 if is_unlocked else 0.7
                )
                achievements_list.controls.append(card)

    load_stats()
    load_achievements()

    return ft.Column([
        header,
        stats_container,
        achievements_list
    ], expand=True), load_achievements