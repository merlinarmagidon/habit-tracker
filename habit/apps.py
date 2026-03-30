from django.apps import AppConfig


# ==============================================
# НАСТРОЙКИ ПРИЛОЖЕНИЯ HABIT
# ==============================================
class HabitConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'habit'
    # verbose_name = 'Привычки' - закомментировал, потому что пока не нужен перевод в админке

    def ready(self) -> None:
        """
        Когда приложение готово, импортируем сигналы.
        Без этого сигналы не работают, и серии не создаются автоматически.
        Долго мучился, пока не понял в чем дело.
        """
        import habit.signals