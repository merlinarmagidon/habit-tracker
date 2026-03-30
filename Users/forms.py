from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import re


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) > 30:
            raise ValidationError('Имя пользователя не может превышать 30 символов.')
        return username

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z]+$', first_name):
            raise ValidationError('Имя может содержать только буквы.')
        if len(first_name) > 30:
            raise ValidationError('Имя не может превышать 30 символов.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z]+$', last_name):
            raise ValidationError('Фамилия может содержать только буквы.')
        if len(last_name) > 30:
            raise ValidationError('Фамилия не может превышать 30 символов.')
        return last_name