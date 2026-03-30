from django.contrib import admin
from .models import Habit, TaskTracker, Streak, Achievement, PredefinedHabit


# ==============================================
# АДМИНКА ДЛЯ ПРИВЫЧЕК
# Тут я зарегистрировал модели, чтобы ими можно было управлять через /admin
# Сначала забыл про register, и модели не отображались в админке
# ==============================================

# Регистрируем привычки
admin.site.register(Habit)

# Регистрируем задачи
admin.site.register(TaskTracker)

# Регистрируем серии
admin.site.register(Streak)

# Регистрируем достижения
admin.site.register(Achievement)

# Регистрируем готовые шаблоны привычек
admin.site.register(PredefinedHabit)

# Остальные модели (Theme, DeviceSettings, LayoutTemplate, ImageAsset) пока не нужны в админке
# Они есть в проекте, но закомментировал, чтобы не захламлять интерфейс
# Потом, если понадобятся, можно раскомментировать