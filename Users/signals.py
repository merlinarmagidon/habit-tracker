from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


# ==============================================
# СИГНАЛЫ ДЛЯ АВТОМАТИЧЕСКОГО СОЗДАНИЯ ПРОФИЛЯ
# ==============================================
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Когда создается новый пользователь (created = True),
    автоматически создаем для него профиль.
    Чтобы не делать это руками в админке или в коде.

    Сначала я забыл про сигналы, и у пользователей не было профилей.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """
    Когда обновляем данные пользователя, автоматически обновляем и профиль.
    Например, если поменяли имя - в профиле оно тоже обновится.
    """
    instance.profile.save()