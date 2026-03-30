from django.db import models
from django.contrib.auth.models import User
from habit.models import Habit


# ==============================================
# МОДЕЛЬ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ
# ==============================================
class Profile(models.Model):
    """
    Тут хранятся дополнительные данные о пользователе, которых нет в стандартной модели User.
    Связано с User через OneToOneField - у одного юзера может быть только один профиль.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    full_name = models.CharField(
        'Полное имя',
        max_length=255,
        blank=True,
        help_text='Автоматически заполняется из имени и фамилии'
    )
    active_habit = models.IntegerField(
        'Активных привычек',
        default=0,
        help_text='Количество активных привычек пользователя'
    )
    email = models.EmailField(
        'Электронная почта',
        default="unknown@example.com",
        help_text='Дублируется из модели User для удобства'
    )
    date_joined = models.DateTimeField(
        'Дата регистрации',
        null=True,
        blank=True,
        help_text='Дублируется из модели User для удобства'
    )

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f"Профиль {self.user.username}"

    def save(self, *args, **kwargs):
        """
        Когда сохраняем профиль, автоматически заполняем поля на основе данных пользователя.
        Чтобы не делать это вручную каждый раз.
        """
        # Собираем полное имя из имени и фамилии
        self.full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        # Считаем сколько у пользователя привычек
        self.active_habit = Habit.objects.filter(user=self.user).count()
        # Копируем email из модели User
        self.email = self.user.email
        # Копируем дату регистрации
        self.date_joined = self.user.date_joined
        # Вызываем оригинальный метод сохранения
        super().save(*args, **kwargs)