from django.contrib import admin
from .models import (
    Habit, TaskTracker, Streak, Achievement,
    PredefinedHabit, Theme, DeviceSettings,
    LayoutTemplate, ImageAsset
)

admin.site.register(Habit)
admin.site.register(TaskTracker)
admin.site.register(Streak)
admin.site.register(Achievement)
admin.site.register(PredefinedHabit)
admin.site.register(Theme)
admin.site.register(DeviceSettings)
admin.site.register(LayoutTemplate)
admin.site.register(ImageAsset)