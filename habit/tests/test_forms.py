from datetime import datetime
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from django.test import TestCase
from habit.models import Habit
from habit.forms import HabitForm


# ==============================================
# ТЕСТЫ ДЛЯ ФОРМЫ СОЗДАНИЯ ПРИВЫЧКИ
# Проверяем, правильно ли работает форма HabitForm
# ==============================================
class ViewTestCase(TestCase):
    """Проверяем, правильно ли работает форма добавления привычки."""

    @classmethod
    def setUpTestData(cls):
        """Создаем тестового пользователя."""
        cls.user = User.objects.create_user(username='test_user_1', password='123456')


    # Тест на уникальность названия привычки
    @pytest.mark.django_db
    def test_valid_habit_name(cls):
        """Проверяем, что новое уникальное название проходит валидацию."""
        start_date = timezone.make_aware(datetime(2024, 4, 19, 12, 0))
        data = {'name': 'Новая привычка', 'frequency': -1, 'period': 'daily',
                'goal': -7, 'notes': '', 'start_date': start_date}
        form = HabitForm(data=data)
        form.is_valid()
        # Должно вернуть True, потому что такой привычки еще нет
        assert form.is_valid_habit_name(cls.user) == True


    # Тест на повторяющееся название
    @pytest.mark.django_db
    def test_invalid_habit_name(cls):
        """Проверяем, что нельзя создать вторую привычку с таким же названием."""
        start_date = timezone.make_aware(datetime(2024, 4, 19, 12, 0))
        # Сначала создаем привычку
        existing_habit = Habit.objects.create(user=cls.user, name='Существующая привычка', frequency=1,
                                              period='daily', goal=7, notes='', start_date=start_date)
        # Пытаемся создать еще одну с таким же именем
        data = {'name': 'Существующая привычка', 'frequency': 1, 'period': 'daily',
                'goal': 7, 'notes': '', 'start_date': start_date}
        form = HabitForm(data=data)
        form.is_valid()
        # Должно вернуть False
        assert form.is_valid_habit_name(cls.user) == False


    # Тест на невалидные данные (отрицательная частота и цель)
    @pytest.mark.django_db
    def test_invalid_data(cls):
        """Проверяем, что форма не пропускает отрицательные значения."""
        start_date = timezone.make_aware(datetime(2024, 4, 19, 12, 0))
        data = {'name': 'Новая привычка', 'frequency': -1, 'period': 'daily',
                'goal': -7, 'notes': '', 'start_date': start_date}
        form = HabitForm(data=data)

        # Форма должна быть невалидной
        assert form.is_valid() == False

        # Должны появиться ошибки для полей frequency и goal
        assert 'frequency' in form.errors
        assert 'goal' in form.errors
        assert "Убедитесь, что это значение больше либо равно 1." in form.errors['frequency']
        assert "Выберите корректный вариант. -7 нет среди допустимых значений." in form.errors['goal']