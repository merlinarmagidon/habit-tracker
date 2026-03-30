from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# ==============================================
# НАСТРОЙКИ ПРИЛОЖЕНИЯ USERS
# ==============================================
class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Users'
    verbose_name = 'Пользователи'  # Русское название в админке

    def ready(self) -> None:
        """
        Импортируем сигналы для автоматического создания профилей.
        Если этого не сделать, профили не будут создаваться при регистрации.
        """
        import Users.signals