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

    Сначала я пытался хранить все в модели User, но потом решил расширить.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)  # Полное имя (first_name + last_name)
    active_habit = models.IntegerField(default=0)  # Сколько активных привычек у пользователя
    email = models.EmailField(default="unknown@example.com")  # Email (дублируем из User для удобства)
    date_joined = models.DateTimeField(null=True, blank=True)  # Дата регистрации (тоже дублируем)

    def save(self, *args, **kwargs):
        """
        Когда сохраняем профиль, автоматически заполняем поля на основе данных пользователя.
        Чтобы не делать это вручную каждый раз.

        Проблема: если пользователь меняет имя в админке, в профиле оно должно обновиться.
        """
        # Собираем полное имя из имени и фамилии
        self.full_name = f"{self.user.first_name} {self.user.last_name}"
        # Считаем сколько у пользователя привычек
        self.active_habit = Habit.objects.filter(user=self.user).count()
        # Копируем email из модели User
        self.email = self.user.email
        # Копируем дату регистрации
        self.date_joined = self.user.date_joined
        # Вызываем оригинальный метод сохранения
        super().save(*args, **kwargs)