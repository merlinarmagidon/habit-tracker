from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Habit, Streak


# ==============================================
# СИГНАЛЫ ДЛЯ АВТОМАТИЧЕСКОГО СОЗДАНИЯ СЕРИИ
# ==============================================
@receiver(post_save, sender=Habit)
def create_streak(sender, instance, created, **kwargs):
    """
    Когда пользователь создает новую привычку, Django автоматически вызывает эту функцию.
    Мы создаем объект Streak, связанный с этой привычкой.
    Чтобы не делать это руками в коде.

    Сначала я забыл про сигналы и создавал серии вручную, потом нашел этот способ.
    """
    if created:
        Streak.objects.create(habit=instance)


@receiver(post_save, sender=Habit)
def save_streak(sender, instance, **kwargs):
    """
    Когда привычка сохраняется (например, обновилось название),
    проверяем, есть ли у нее серия, и сохраняем ее тоже.
    Нужно, чтобы все было согласованно.
    """
    # Проверяем, есть ли у привычки связанная серия
    if hasattr(instance, 'streak'):
        streak_instance = instance.streak.first()
        if streak_instance:
            streak_instance.save()