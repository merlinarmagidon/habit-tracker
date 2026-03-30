from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.test import TestCase
from freezegun import freeze_time
from habit.models import Habit, TaskTracker, Streak, Achievement
from habit.analytics import extract_first_failed_task


# ==============================================
# ТЕСТЫ ДЛЯ МОДЕЛИ ПРИВЫЧКИ
# Проверяем, правильно ли создаются и сохраняются привычки
# ==============================================
class HabitTestCase(TestCase):
    """Проверяем, правильно ли работает создание привычек."""

    @classmethod
    def setUpTestData(cls):
        """Создаем тестовые привычки перед запуском тестов."""
        cls.user_1 = User.objects.create_user(username='test_user_1', password='123456')
        cls.user_2 = User.objects.create_user(username='test_user', password='12345')

        # Привычка 1: еженедельная, спорт
        cls.habit_1 = Habit.objects.create(
            name='Упражнения',
            frequency=2,
            period='weekly',
            goal=35,
            num_of_tasks=0,  # Пусть посчитается автоматически
            notes='Регулярные упражнения для здоровья',
            start_date=timezone.now(),
            user=cls.user_1
        )

        # Привычка 2: еженедельная, гигиена
        cls.habit_2 = Habit.objects.create(
            name='Чистка зубов',
            frequency=2,
            period='weekly',
            goal=30,
            num_of_tasks=0,
            notes='Напоминание о гигиене полости рта',
            start_date=timezone.now(),
            user=cls.user_2
        )

    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.start_date = timezone.now()

    def test_habit_creation(self):
        """Проверяем, что привычка создается с правильными параметрами."""
        # Проверяем habit_1
        assert self.habit_1.name == 'Упражнения'
        assert self.habit_1.frequency == 2
        assert self.habit_1.period == 'weekly'
        assert self.habit_1.goal == 35
        assert self.habit_1.notes == 'Регулярные упражнения для здоровья'
        assert self.habit_1.user == self.user_1
        assert self.habit_1.num_of_tasks == 10  # Должно посчитаться как (35//7)*2

        # Проверяем habit_2
        assert self.habit_2.name == 'Чистка зубов'
        assert self.habit_2.frequency == 2
        assert self.habit_2.period == 'weekly'
        assert self.habit_2.goal == 30
        assert self.habit_2.notes == 'Напоминание о гигиене полости рта'
        assert self.habit_2.user == self.user_2
        assert self.habit_2.num_of_tasks == 8  # (30//7)*2

        # Проверяем правильность расчета количества задач
        expected_num_of_tasks_1 = (self.habit_1.goal // 7) * self.habit_1.frequency
        expected_num_of_tasks_2 = (self.habit_2.goal // 7) * self.habit_2.frequency
        assert self.habit_1.num_of_tasks == expected_num_of_tasks_1
        assert self.habit_2.num_of_tasks == expected_num_of_tasks_2

        # Проверяем даты
        assert self.habit_1.start_date is not None
        assert self.habit_1.completion_date is not None
        assert self.habit_1.completion_date == self.habit_1.start_date + timedelta(days=self.habit_1.goal)

        assert self.habit_2.start_date is not None
        assert self.habit_2.completion_date is not None
        assert self.habit_2.completion_date == self.habit_2.start_date + timedelta(days=self.habit_2.goal)


# ==============================================
# ТЕСТЫ ДЛЯ МОДЕЛИ ЗАДАЧ
# Проверяем создание задач и обновление статусов
# ==============================================
class TaskTrackerTestCase(TestCase):
    """Проверяем, правильно ли создаются и обновляются задачи."""

    @classmethod
    def setUpTestData(cls):
        """Создаем привычку для тестов."""
        cls.user_1 = User.objects.create_user(username='test_user_1', password='123456')
        cls.habit = Habit.objects.create(name='Упражнения', frequency=1, period='daily', goal=3,
                                         num_of_tasks=0, notes='Регулярные упражнения',
                                         start_date=timezone.now(), user=cls.user_1)

    def test_task_creation(self):
        """Проверяем, что задачи создаются в нужном количестве."""
        TaskTracker.create_tasks(self.habit)
        tasks = TaskTracker.objects.filter(habit=self.habit)

        # Задачи должны существовать
        assert tasks.exists()

        # Количество задач должно совпадать с habit.num_of_tasks
        assert tasks.count() == self.habit.num_of_tasks

        # Номера задач должны идти по порядку
        for index, task in enumerate(tasks, start=1):
            assert task.task_number == index

    def test_task_due_dates(self):
        """Проверяем, что даты выполнения рассчитываются правильно."""
        TaskTracker.create_tasks(self.habit)

        # Считаем промежуток между задачами
        time_jump = self.habit.goal / self.habit.num_of_tasks
        time_skip = timedelta(hours=time_jump * 24)

        # Проверяем каждую задачу
        tasks = TaskTracker.objects.filter(habit=self.habit)
        current_due_date = self.habit.start_date
        for task in tasks:
            assert task.due_date == (current_due_date + time_skip)
            current_due_date += time_skip

    def test_default_task_status(self):
        """Проверяем, что новые задачи получают статус 'В процессе'."""
        TaskTracker.create_tasks(self.habit)

        tasks = TaskTracker.objects.filter(habit=self.habit)
        for task in tasks:
            assert task.task_status == 'In progress'

    def test_update_failed_tasks(self):
        """Проверяем, что просроченные задачи становятся 'Провалено'."""
        TaskTracker.create_tasks(self.habit)
        tasks = TaskTracker.objects.filter(habit=self.habit)

        # Замораживаем время на 2 дня вперед (первые две задачи просрочены)
        frozen_time = timezone.now() + timedelta(days=2)
        with freeze_time(frozen_time):
            updated_habit_ids, updated_task_ids = TaskTracker.update_failed_tasks(self.user_1.id)

            for task in tasks:
                task.refresh_from_db()
                if task.task_number == 3:
                    assert task.task_status == 'In progress'  # Третья еще не просрочена
                else:
                    assert task.task_status == 'Failed'
                    assert task.task_completion_date == task.due_date

                    # Проверяем, что ID обновились правильно
                    assert task.habit_id in updated_habit_ids
                    assert task.id in updated_task_ids


# ==============================================
# ТЕСТЫ ДЛЯ МОДЕЛИ СЕРИИ
# Проверяем работу серий
# ==============================================
class StreakTestCase(TestCase):
    """Проверяем, правильно ли работают серии."""

    @classmethod
    def setUpTestData(cls):
        """Создаем привычку."""
        cls.user_1 = User.objects.create_user(username='test_user_1', password='123456')
        cls.habit = Habit.objects.create(name='Упражнения', frequency=1, period='daily',
                                goal=12, num_of_tasks=0, notes='Регулярные упражнения',
                                start_date=timezone.now(), user=cls.user_1)

    def test_streak_creation_on_habit_creation(self):
        """При создании привычки должна создаваться серия."""
        streak = Streak.objects.filter(habit=self.habit).first()
        assert streak is not None
        assert streak.current_streak == 0
        assert streak.longest_streak == 0

    def test_longest_streak_update(self):
        """Если текущая серия больше рекорда, рекорд должен обновиться."""
        streak = Streak.objects.create(
            habit=self.habit,
            longest_streak=10,
            current_streak=11,
        )
        streak.save()
        assert streak.longest_streak == 11

    def test_update_streak_information(self):
        """Проверяем всю логику обновления серии."""
        TaskTracker.create_tasks(self.habit)
        streak = Streak.objects.get(habit=self.habit)
        tasks = TaskTracker.objects.filter(habit=self.habit)

        # Отмечаем первые 7 задач и задачу 10 как выполненные
        for task in tasks:
            if task.task_number <= 7:
                task.task_status = 'Completed'
                streak.current_streak += 1
                task.save()
                streak.save()

        # Замораживаем время, чтобы задачи 8 и 9 просрочились
        frozen_time = timezone.now() + timedelta(days=9)
        with freeze_time(frozen_time):
            updated_habit_ids, updated_task_ids = TaskTracker.update_failed_tasks(self.user_1.id)
        streak.update_streak(updated_habit_ids)
        streak.num_completed_tasks(habit=self.habit)
        streak.refresh_from_db()

        # Отмечаем задачи 10-12 как выполненные
        for task in tasks:
            if 10 <= task.task_number <= 12:
                task.task_status = 'Completed'
                streak.current_streak += 1
                task.save()
                streak.save()

        streak.num_completed_tasks(habit=self.habit)
        streak.refresh_from_db()

        # Проверяем итоговые значения
        assert streak.num_of_completed_tasks == 10
        assert streak.num_of_failed_tasks == 2
        assert streak.longest_streak == 7
        assert streak.current_streak == 3


# ==============================================
# ТЕСТЫ ДЛЯ МОДЕЛИ ДОСТИЖЕНИЙ
# Проверяем выдачу достижений
# ==============================================
class AchievementTestCase(TestCase):
    """Проверяем, правильно ли выдаются достижения."""

    @classmethod
    def setUpTestData(cls):
        """Создаем привычки для тестов."""
        cls.user_1 = User.objects.create_user(username='test_user_1', password='123456')
        # Ежедневная привычка
        cls.habit_1 = Habit.objects.create(name='Упражнения', frequency=1, period='daily',
                                goal=30, num_of_tasks=0, notes='Регулярные упражнения',
                                start_date=timezone.now(), user=cls.user_1)
        # Еженедельная привычка
        cls.habit_2 = Habit.objects.create(name='Чтение книг', frequency=2, period='weekly',
                                goal=30, num_of_tasks=0, notes='',
                                start_date=timezone.now(), user=cls.user_1)

    def test_update_daily_achievement_information(self):
        """Проверяем, что ежедневные привычки получают правильные достижения."""
        TaskTracker.create_tasks(self.habit_1)
        streak = Streak.objects.get(habit=self.habit_1)
        tasks = TaskTracker.objects.filter(habit=self.habit_1)

        # Выполняем первые 8 задач (серия 7 дней, потом еще одна)
        for task in tasks:
            if task.task_number <= 8:
                task.task_status = 'Completed'
                streak.current_streak += 1
                task.save()
                streak.save()
                Achievement.rewards_streaks(task.habit_id, streak)

        # Проваливаем задачи 9-10
        frozen_time_1 = timezone.now() + timedelta(days=10)
        with freeze_time(frozen_time_1):
            updated_habit_ids, updated_task_ids = TaskTracker.update_failed_tasks(self.user_1.id)
            first_failed_tasks = extract_first_failed_task(updated_task_ids)
            Achievement.update_achievements(first_failed_tasks)
            streak.update_streak(updated_habit_ids)
            streak.refresh_from_db()

        # Проваливаем задачи 11-12 (проверяем, что не создается лишних "Прерывание привычки")
        frozen_time_2 = timezone.now() + timedelta(days=12)
        with freeze_time(frozen_time_2):
            updated_habit_ids, updated_task_ids = TaskTracker.update_failed_tasks(self.user_1.id)
            first_failed_tasks = extract_first_failed_task(updated_task_ids)
            Achievement.update_achievements(first_failed_tasks)
            streak.update_streak(updated_habit_ids)
            streak.refresh_from_db()

        # Выполняем задачи с 13 по 27 (серия 14 дней)
        for task in tasks:
            if 12 < task.task_number < 28:
                task.task_status = 'Completed'
                streak.current_streak += 1
                task.save()
                streak.save()
                Achievement.rewards_streaks(task.habit_id, streak)

        achievements = Achievement.objects.filter(habit=self.habit_1)
        streak.refresh_from_db()

        # Должно быть 4 достижения
        assert Achievement.objects.count() == 4
        assert achievements[0].title == '7-дневная серия'
        assert achievements[0].streak_length == 7
        assert achievements[1].title == 'Прерывание привычки'
        assert achievements[1].streak_length == 8
        assert achievements[2].title == '7-дневная серия'
        assert achievements[2].streak_length == 7
        assert achievements[3].title == '14-дневная серия'
        assert achievements[3].streak_length == 14

    def test_update_weekly_achievement(self):
        """Проверяем достижения для еженедельных привычек."""
        TaskTracker.create_tasks(self.habit_2)
        streak = Streak.objects.get(habit=self.habit_2)
        tasks = TaskTracker.objects.filter(habit=self.habit_2)

        # Выполняем первые 8 задач
        for task in tasks:
            if task.task_number <= 8:
                task.task_status = 'Completed'
                streak.current_streak += 1
                task.save()
                streak.save()
                Achievement.rewards_streaks(task.habit_id, streak)

        streak.refresh_from_db()
        achievements = Achievement.objects.filter(habit=self.habit_2)

        # Должно быть 3 достижения
        assert Achievement.objects.count() == 3
        assert achievements[0].title == '1-недельная серия'
        assert achievements[0].streak_length == 2
        assert achievements[1].streak_length == 4
        assert achievements[1].title == '2-недельная серия'
        assert achievements[2].title == '4-недельная серия'
        assert achievements[2].streak_length == 8