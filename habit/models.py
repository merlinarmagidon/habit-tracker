from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import convert_period_to_days


# ==============================================
# МОДЕЛЬ ПРИВЫЧКИ
# ==============================================
class Habit(models.Model):
    """Модель привычки"""

    # Выбор периода для фильтра в админке
    PERIOD_CHOICES = [
        ('daily', 'Ежедневная'),
        ('weekly', 'Еженедельная'),
        ('monthly', 'Ежемесячная'),
        ('annual', 'Ежегодная'),
    ]

    name = models.CharField('Название', max_length=255)
    frequency = models.IntegerField('Частота', default=1)
    period = models.CharField('Период', max_length=255, choices=PERIOD_CHOICES)
    goal = models.IntegerField('Цель (дни)', default=90)
    num_of_tasks = models.IntegerField('Количество задач')
    notes = models.CharField('Заметки', max_length=255, default=None, blank=True)
    creation_time = models.DateTimeField('Время создания', auto_now_add=True)
    start_date = models.DateTimeField('Дата начала', null=True, blank=True)
    completion_date = models.DateTimeField('Дата завершения', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
        ordering = ['-creation_time']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        if not self.completion_date:
            self.completion_date = self.start_date + timedelta(days=self.goal)
        num_of_period = convert_period_to_days(self.period)
        if not self.num_of_tasks:
            self.num_of_tasks = (self.goal // num_of_period) * self.frequency
        super().save(*args, **kwargs)


# ==============================================
# МОДЕЛЬ ЗАДАЧ
# ==============================================
class TaskTracker(models.Model):
    """Модель задач"""

    # Выбор статуса для фильтра в админке
    STATUS_CHOICES = [
        ('In progress', 'В процессе'),
        ('Completed', 'Выполнено'),
        ('Failed', 'Провалено'),
    ]

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, verbose_name='Привычка', related_name='tasks')
    start_date = models.DateTimeField('Дата начала', null=True, blank=True)
    due_date = models.DateTimeField('Дедлайн', null=True, blank=True)
    task_number = models.IntegerField('Номер задачи')
    task_status = models.CharField('Статус', max_length=255, choices=STATUS_CHOICES)
    task_completion_date = models.DateTimeField('Дата выполнения', null=True, blank=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['task_number']

    def __str__(self):
        return f"Задача {self.task_number} - {self.habit.name}"

    @classmethod
    def create_tasks(cls, habit, n=0):
        time_jump = habit.goal / habit.num_of_tasks
        time_skip = timedelta(hours=time_jump * 24)
        due_date = start_date = habit.start_date
        default = 'In progress'
        for i in range(n + 1, habit.num_of_tasks + (n + 1)):
            due_date += time_skip
            if i == n + 1:
                current_start_date = start_date
            else:
                current_start_date += time_skip
            cls.objects.create(habit=habit, due_date=due_date, task_number=i,
                               task_status=default, start_date=current_start_date)

    @classmethod
    def update_failed_tasks(cls, user_id):
        updated_habit_ids = []
        updated_task_ids = []
        tasks_to_update = cls.objects.filter(habit__user_id=user_id,
                                             due_date__lt=timezone.now(),
                                             task_status='In progress')
        for task in tasks_to_update:
            task.task_status = 'Failed'
            task.task_completion_date = task.due_date
            task.save()
            updated_habit_ids.append(task.habit_id)
            updated_task_ids.append(task.id)
        return (updated_habit_ids, updated_task_ids)


# ==============================================
# МОДЕЛЬ СЕРИИ
# ==============================================
class Streak(models.Model):
    """Модель серий"""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, verbose_name='Привычка', related_name='streak')
    num_of_completed_tasks = models.IntegerField('Выполнено задач', default=0)
    num_of_failed_tasks = models.IntegerField('Провалено задач', default=0)
    longest_streak = models.IntegerField('Самая длинная серия', default=0)
    current_streak = models.IntegerField('Текущая серия', default=0)

    class Meta:
        verbose_name = 'Серия'
        verbose_name_plural = 'Серии'

    def __str__(self):
        return f"Серия {self.habit.name} - {self.current_streak} дней"

    def save(self, *args, **kwargs):
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        super().save(*args, **kwargs)

    @classmethod
    def num_completed_tasks(cls, habit):
        completed_num = TaskTracker.objects.filter(habit=habit, task_status='Completed').count()
        streak = habit.streak.first()
        streak.num_of_completed_tasks = completed_num
        streak.save()

    @classmethod
    def update_streak(cls, habit_ids):
        for habit_id in habit_ids:
            habit_streak = cls.objects.get(habit_id=habit_id)
            habit_streak.num_of_failed_tasks += 1
            habit_streak.current_streak = 0
            habit_streak.save()


# ==============================================
# МОДЕЛЬ ДОСТИЖЕНИЙ
# ==============================================
class Achievement(models.Model):
    """Модель достижений"""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, verbose_name='Привычка', related_name='achievement')
    streak_length = models.IntegerField('Длина серии', default=0)
    title = models.CharField('Название', max_length=255)
    date = models.DateTimeField('Дата получения', null=True, blank=True)

    class Meta:
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижения'
        ordering = ['-date']

    def __str__(self):
        # Переводим названия достижений для отображения в админке
        titles = {
            '7-Day Streak': '7-дневная серия',
            '14-Day Streak': '14-дневная серия',
            '30-Day Streak': '30-дневная серия',
            '1-Week Streak': '1-недельная серия',
            "2-Week's Streak": '2-недельная серия',
            "4-Week's Streak": '4-недельная серия',
            '1-Month Streak': '1-месячная серия',
            "2-Month's Streak": '2-месячная серия',
            "4-Month's Streak": '4-месячная серия',
            'Break The Habit': 'Прерывание привычки',
        }
        return titles.get(self.title, self.title)

    @classmethod
    def update_achievements(cls, tasks):
        for task in tasks:
            if task.task_number > 1:
                try:
                    prev_task = TaskTracker.objects.get(
                        habit=task.habit,
                        task_number=task.task_number - 1
                    )
                    if prev_task.task_status == 'Failed':
                        continue
                except TaskTracker.DoesNotExist:
                    pass
            streak = task.habit.streak.get()
            if streak and streak.current_streak != 0:
                title = 'Прерывание привычки'
                streak_length = streak.current_streak if streak else 0
                cls.objects.create(habit=task.habit, date=task.due_date,
                                   title=title, streak_length=streak_length)

    @classmethod
    def rewards_streaks(cls, habit_id, streak):
        habit = Habit.objects.get(pk=habit_id)

        if streak.current_streak / habit.frequency == 7 and habit.period == 'daily':
            title = '7-дневная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak / habit.frequency == 14 and habit.period == 'daily':
            title = '14-дневная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak / habit.frequency == 30 and habit.period == 'daily':
            title = '30-дневная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)

        if habit.period == 'weekly' and (streak.current_streak / habit.frequency) == 1:
            title = '1-недельная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if (streak.current_streak / habit.frequency) == 2 and habit.period == 'weekly':
            title = '2-недельная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if (streak.current_streak / habit.frequency) == 4 and habit.period == 'weekly':
            title = '4-недельная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)

        if streak.current_streak // habit.frequency == 1 and habit.period == 'monthly':
            title = '1-месячная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak // habit.frequency == 2 and habit.period == 'monthly':
            title = '2-месячная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak // habit.frequency == 4 and habit.period == 'monthly':
            title = '4-месячная серия'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)


# ==============================================
# МОДЕЛЬ ШАБЛОНОВ ПРИВЫЧЕК
# ==============================================
class PredefinedHabit(models.Model):
    """Шаблоны привычек"""

    PERIOD_CHOICES = [
        ('daily', 'Ежедневная'),
        ('weekly', 'Еженедельная'),
        ('monthly', 'Ежемесячная'),
        ('annual', 'Ежегодная'),
    ]

    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    frequency = models.IntegerField('Частота', default=1)
    period = models.CharField('Период', max_length=20, choices=PERIOD_CHOICES, default='daily')
    goal = models.IntegerField('Цель (дни)', default=30)
    notes = models.TextField('Заметки', blank=True)
    category = models.CharField('Категория', max_length=100, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Шаблон привычки'
        verbose_name_plural = 'Шаблоны привычек'

    def __str__(self):
        return self.name


# ==============================================
# МОДЕЛЬ ТЕМЫ ОФОРМЛЕНИЯ
# ==============================================
class Theme(models.Model):
    """Темы оформления"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='themes')
    name = models.CharField('Название темы', max_length=100)
    primary_color = models.CharField('Основной цвет', max_length=7, default='#262C3C')
    secondary_color = models.CharField('Вторичный цвет', max_length=7, default='#D6BDA8')
    background_color = models.CharField('Цвет фона', max_length=7, default='#F3F4F5')
    font_family = models.CharField('Шрифт', max_length=100, default='Arial')
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


# ==============================================
# НАСТРОЙКИ УСТРОЙСТВ
# ==============================================
class DeviceSettings(models.Model):
    """Настройки устройств"""

    DEVICE_TYPES = [
        ('desktop', 'Компьютер'),
        ('tablet', 'Планшет'),
        ('mobile', 'Телефон'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь',
                             related_name='device_settings')
    device_type = models.CharField('Тип устройства', max_length=50, choices=DEVICE_TYPES)
    browser = models.CharField('Браузер', max_length=100)
    screen_width = models.IntegerField('Ширина экрана')
    screen_height = models.IntegerField('Высота экрана')
    font_size = models.IntegerField('Размер шрифта', default=16)
    last_updated = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Настройка устройства'
        verbose_name_plural = 'Настройки устройств'

    def __str__(self):
        return f"{self.device_type} - {self.user.username}"


# ==============================================
# ШАБЛОНЫ МАКЕТОВ
# ==============================================
class LayoutTemplate(models.Model):
    """Шаблоны макетов"""

    name = models.CharField('Название шаблона', max_length=100)
    description = models.TextField('Описание', blank=True)
    html_structure = models.TextField('HTML структура')
    css_styles = models.TextField('CSS стили')
    is_default = models.BooleanField('По умолчанию', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Шаблон макета'
        verbose_name_plural = 'Шаблоны макетов'

    def __str__(self):
        return self.name


# ==============================================
# ИЗОБРАЖЕНИЯ
# ==============================================
class ImageAsset(models.Model):
    """Изображения"""

    CATEGORIES = [
        ('icon', 'Иконка'),
        ('background', 'Фон'),
        ('logo', 'Логотип'),
    ]

    name = models.CharField('Название', max_length=100)
    file = models.ImageField('Файл', upload_to='assets/')
    category = models.CharField('Категория', max_length=50, choices=CATEGORIES)
    alt_text = models.CharField('Описание', max_length=255, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Ресурс'
        verbose_name_plural = 'Ресурсы'

    def __str__(self):
        return self.name