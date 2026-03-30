from django.contrib import admin
from django.utils.html import format_html
from .models import Habit, TaskTracker, Streak, Achievement, PredefinedHabit


# ==============================================
# АДМИНКА ДЛЯ ПРИВЫЧЕК
# ==============================================
@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    """Управление привычками"""
    list_display = ['name', 'user', 'get_period_display', 'frequency', 'goal', 'creation_time']
    list_filter = ['period', 'user']
    search_fields = ['name', 'user__username']
    readonly_fields = ['creation_time', 'num_of_tasks', 'completion_date']

    def get_period_display(self, obj):
        periods = {
            'daily': 'Ежедневная',
            'weekly': 'Еженедельная',
            'monthly': 'Ежемесячная',
            'annual': 'Ежегодная'
        }
        return periods.get(obj.period, obj.period)

    get_period_display.short_description = 'Период'


# ==============================================
# АДМИНКА ДЛЯ ЗАДАЧ
# ==============================================
@admin.register(TaskTracker)
class TaskTrackerAdmin(admin.ModelAdmin):
    """Управление задачами"""
    list_display = ['habit', 'task_number', 'colored_status', 'due_date', 'task_completion_date']
    list_filter = ['task_status', 'habit__user']
    search_fields = ['habit__name']
    readonly_fields = ['task_number', 'start_date', 'due_date']

    def colored_status(self, obj):
        """Цветной статус на русском"""
        colors = {
            'In progress': 'orange',
            'Completed': 'green',
            'Failed': 'red'
        }
        statuses = {
            'In progress': 'В процессе',
            'Completed': 'Выполнено',
            'Failed': 'Провалено'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.task_status, 'white'),
            statuses.get(obj.task_status, obj.task_status)
        )

    colored_status.short_description = 'Статус'


# ==============================================
# АДМИНКА ДЛЯ СЕРИЙ
# ==============================================
@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    """Управление сериями"""
    list_display = ['habit', 'current_streak', 'longest_streak', 'num_of_completed_tasks', 'num_of_failed_tasks']
    list_filter = ['habit__user']
    search_fields = ['habit__name']


# ==============================================
# АДМИНКА ДЛЯ ДОСТИЖЕНИЙ
# ==============================================
@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    """Управление достижениями"""
    list_display = ['habit', 'get_title_display', 'streak_length', 'date']
    list_filter = ['habit__user']
    search_fields = ['habit__name']

    def get_title_display(self, obj):
        """Перевод названий достижений на русский"""
        titles = {
            '7-Day Streak': '7-дневная серия',
            '14-Day Streak': '14-дневная серия',
            '30-Day Streak': '30-дневная серия',
            '1-Week Streak': '1-недельная серия',
            "2-Week's Streak": '2-недельная серия',
            "4-Week's Streak": '4-недельная серия',
            '1-Month Streak': '1-месячная серия',
            "2-Month's Streak": '2-месячная серия',
            "4-Month's Streak": '4-месячная серия',
            'Break The Habit': 'Прерывание привычки',
        }
        return titles.get(obj.title, obj.title)

    get_title_display.short_description = 'Название'


# ==============================================
# АДМИНКА ДЛЯ ШАБЛОНОВ ПРИВЫЧЕК
# ==============================================
@admin.register(PredefinedHabit)
class PredefinedHabitAdmin(admin.ModelAdmin):
    """Управление шаблонами привычек"""
    list_display = ['name', 'get_period_display', 'frequency', 'goal', 'is_active']
    list_filter = ['period', 'is_active', 'category']
    search_fields = ['name', 'category']

    def get_period_display(self, obj):
        periods = {
            'daily': 'Ежедневная',
            'weekly': 'Еженедельная',
            'monthly': 'Ежемесячная',
            'annual': 'Ежегодная'
        }
        return periods.get(obj.period, obj.period)

    get_period_display.short_description = 'Период'