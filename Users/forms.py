from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re


# ==============================================
# ФОРМА РЕГИСТРАЦИИ ПОЛЬЗОВАТЕЛЯ
# ==============================================
class UserRegisterForm(UserCreationForm):
    """
    Эта форма расширяет стандартную форму регистрации Django.
    Добавляем поле для email, потому что в стандартной его нет.
    А еще добавил свои проверки для имени и фамилии (только буквы и не длиннее 30 символов).
    """

    # Добавляем поле email (обязательное)
    email = forms.EmailField()

    class Meta:
        """
        Настройки формы - говорим, с какой моделью работаем и какие поля показываем.
        """
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_username(self):
        """
        Проверка имени пользователя: не длиннее 30 символов.
        Пользователи пытались вводить очень длинные имена.
        """
        username = self.cleaned_data.get('username')
        if len(username) > 30:
            raise ValidationError('Имя пользователя не может превышать 30 символов.')
        return username

    def clean_first_name(self):
        """
        Проверка имени: только буквы (русские или английские) и не длиннее 30 символов.
        Сначала пропускал цифры и символы, потом понял что это некрасиво.
        """
        first_name = self.cleaned_data.get('first_name')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z]+$', first_name):
            raise ValidationError('Имя может содержать только буквы.')
        if len(first_name) > 30:
            raise ValidationError('Имя не может превышать 30 символов.')
        return first_name

    def clean_last_name(self):
        """
        Проверка фамилии: только буквы и не длиннее 30 символов.
        Аналогично с именем.
        """
        last_name = self.cleaned_data.get('last_name')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z]+$', last_name):
            raise ValidationError('Фамилия может содержать только буквы.')
        if len(last_name) > 30:
            raise ValidationError('Фамилия не может превышать 30 символов.')
        return last_name