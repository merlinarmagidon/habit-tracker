import pytest
from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from habit.views import HabitManagerView, HabitView
from habit.models import Habit, TaskTracker, Streak
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase


# ==============================================
# ТЕСТЫ ДЛЯ ПРЕДСТАВЛЕНИЙ (VIEWS)
# Проверяем, как работают страницы с привычками
# ==============================================
class ViewTestCase(TestCase):
    """Проверяем, как работают основные страницы приложения."""

    @classmethod
    def setUpTestData(cls):
        """Создаем пользователя и привычку для тестов."""
        cls.user = User.objects.create_user(username='test_user_1', password='123456')
        cls.factory = RequestFactory()
        cls.habit = Habit.objects.create(user=cls.user, name='Тестовая привычка', frequency=1,
                                         period='daily', goal=7, notes='', start_date=timezone.now())

    # Тест добавления привычки авторизованным пользователем
    def test_add_habit_authenticated_user(self):
        """Авторизованный пользователь должен видеть страницу добавления."""
        request = self.factory.post('/add-habit')
        request.user = self.user
        response = HabitManagerView.add_habit(request)
        assert response.status_code == 200

    # Тест добавления привычки неавторизованным пользователем
    def test_add_habit_not_authenticated(self):
        """Неавторизованный должен быть перенаправлен на страницу входа."""
        request = self.factory.post('/add-habit')
        request.user = AnonymousUser()
        response = HabitManagerView.add_habit(request)
        assert response.status_code == 302
        assert response.url == '/Login'

    # Тест удаления привычки авторизованным пользователем
    def test_delete_habit_authenticated_user(self):
        """Авторизованный пользователь может удалить свою привычку."""
        request = self.factory.post(reverse('habit_deletion', args=[self.habit.pk]))
        request.user = self.user
        response = HabitManagerView.delete_habit(request, self.habit.pk)
        assert response.status_code == 302
        assert not Habit.objects.filter(pk=self.habit.pk).exists()  # Привычка должна удалиться
        assert response.url == '/Habit-Manager/'

    # Тест удаления привычки неавторизованным пользователем
    def test_delete_habit_not_authenticated(self):
        """Неавторизованный не может удалить привычку."""
        request = self.factory.post(reverse('habit_deletion', args=[self.habit.pk]))
        request.user = AnonymousUser()
        response = HabitManagerView.delete_habit(request, self.habit.pk)
        assert response.status_code == 302
        assert Habit.objects.filter(pk=self.habit.pk).exists()  # Привычка должна остаться
        assert response.url == '/Login'

    # Тест отметки задачи как выполненной
    def test_mark_task_completed(self):
        """Проверяем, что при отметке задачи обновляется серия."""
        task = TaskTracker.objects.create(habit=self.habit, task_number=1)
        streak = Streak.objects.filter(habit=self.habit).first()
        request = self.factory.post('/habit-home', {'task_id': task.id, 'habit_id': self.habit.id})
        request.user = self.user
        response = HabitView.as_view()(request)

        # Статус должен стать 'Выполнено'
        assert TaskTracker.objects.get(id=task.id).task_status == 'Completed'

        # Серия должна обновиться
        streak.refresh_from_db()
        assert streak is not None
        assert streak.current_streak == 1
        assert streak.num_of_completed_tasks == 1
        assert streak.longest_streak == 1

        # Должен быть редирект на главную
        assert response.status_code == 302
        assert response.url == '/'