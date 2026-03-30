from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import convert_period_to_days


# ==============================================
# МОДЕЛЬ ПРИВЫЧКИ
# Самая главная модель, тут хранятся все привычки пользователей
# ==============================================
class Habit(models.Model):
    """
    Тут лежат привычки. Название, частота, период и т.д.
    Когда создаешь привычку, некоторые поля заполняются сами (например, количество задач).
    """

    name = models.CharField(max_length=255)  # Название привычки, типа "Чистка зубов"
    frequency = models.IntegerField(default=1)  # Сколько раз в период делать (например, 2 раза в неделю)
    period = models.CharField(max_length=255)  # Период: daily, weekly, monthly, annual
    goal = models.IntegerField(default=90)  # На сколько дней рассчитана привычка
    num_of_tasks = models.IntegerField()  # Всего задач (высчитывается автоматом)
    notes = models.CharField(max_length=255, default=None)  # Заметки пользователя
    creation_time = models.DateTimeField(auto_now_add=True)  # Когда создали
    start_date = models.DateTimeField(null=True, blank=True)  # С какого числа начинаем
    completion_date = models.DateTimeField(null=True, blank=True)  # Когда закончится (высчитывается)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Кто создал, связь с пользователем

    def save(self, *args, **kwargs):
        """
        Переопределил метод сохранения, чтобы некоторые поля заполнялись сами.
        Раньше я их вручную в коде заполнял, но так удобнее.
        """

        # Приводим название к нижнему регистру, чтобы не было дублей типа "Чтение" и "чтение"
        self.name = self.name.lower()

        # Если дата завершения не указана - вычисляем её из даты начала и цели
        if not self.completion_date:
            self.completion_date = self.start_date + timedelta(days=self.goal)

        # Считаем количество задач
        # Сначала узнаем, сколько дней в одном периоде
        num_of_period = convert_period_to_days(self.period)
        if not self.num_of_tasks:
            # Формула: (цель / длину периода) * частоту
            self.num_of_tasks = (self.goal // num_of_period) * self.frequency

        # Вызываем родительский метод сохранения
        super().save(*args, **kwargs)


# ==============================================
# МОДЕЛЬ ЗАДАЧ
# Каждая задача - это одно выполнение привычки
# Например, если привычка "Чистка зубов" на 30 дней, то будет 30 задач
# ==============================================
class TaskTracker(models.Model):
    """
    Тут хранятся все задачи, которые нужно выполнить.
    Для каждой привычки создается куча задач (по количеству num_of_tasks).
    """

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE)  # К какой привычке относится
    start_date = models.DateTimeField(null=True, blank=True)  # Когда можно начинать
    due_date = models.DateTimeField(null=True, blank=True)  # Дедлайн
    task_number = models.IntegerField()  # Номер задачи (1, 2, 3...)
    task_status = models.CharField(max_length=255)  # Статус: In progress, Completed, Failed
    task_completion_date = models.DateTimeField(null=True, blank=True)  # Когда реально выполнили

    @classmethod
    def create_tasks(cls, habit, n=0):
        """
        Создает все задачи для привычки.
        Раньше я это вручную делал, потом вынес в отдельную функцию.

        Алгоритм:
        1. Вычисляем промежуток между задачами (goal / num_of_tasks)
        2. Для каждой задачи считаем start_date и due_date
        3. Создаем запись в базе
        """

        # Считаем, через сколько дней/часов должна появляться следующая задача
        time_jump = habit.goal / habit.num_of_tasks  # В днях
        time_skip = timedelta(hours=time_jump * 24)  # Переводим в timedelta

        # Стартуем от даты начала привычки
        due_date = start_date = habit.start_date
        default = 'In progress'  # Статус по умолчанию

        # Создаем задачи по одной
        for i in range(n + 1, habit.num_of_tasks + (n + 1)):
            due_date += time_skip  # Увеличиваем дедлайн
            if i == n + 1:
                current_start_date = start_date  # Для первой задачи дата начала = start_date привычки
            else:
                current_start_date += time_skip  # Для остальных - сдвигаем

            cls.objects.create(habit=habit, due_date=due_date, task_number=i,
                               task_status=default, start_date=current_start_date)

    @classmethod
    def update_failed_tasks(cls, user_id):
        """
        Ищет все задачи пользователя со статусом 'In progress',
        у которых due_date уже прошел.
        Меняет статус на 'Failed' и сохраняет дату завершения = due_date.
        Возвращает списки id обновленных привычек и задач.
        """
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
# МОДЕЛЬ СЕРИИ (СТРИК)
# Считает, сколько дней/недель подряд пользователь выполняет привычку
# ==============================================
class Streak(models.Model):
    """
    Серия - это сколько раз подряд пользователь выполнил задачу.
    Если пропустил - серия сбрасывается.
    """

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='streak')
    num_of_completed_tasks = models.IntegerField(default=0)  # Сколько всего задач выполнено
    num_of_failed_tasks = models.IntegerField(default=0)  # Сколько всего задач провалено
    longest_streak = models.IntegerField(default=0)  # Самая длинная серия
    current_streak = models.IntegerField(default=0)  # Текущая серия

    def save(self, *args, **kwargs):
        """
        Когда сохраняем серию, проверяем: если текущая серия стала длиннее,
        чем была самая длинная - обновляем рекорд.
        """
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        super().save(*args, **kwargs)

    @classmethod
    def num_completed_tasks(cls, habit):
        """
        Считает, сколько задач выполнено, и обновляет это поле в серии.
        """
        completed_num = TaskTracker.objects.filter(habit=habit, task_status='Completed').count()
        streak = habit.streak.first()
        streak.num_of_completed_tasks = completed_num
        streak.save()

    @classmethod
    def update_streak(cls, habit_ids):
        """
        Когда задача провалена:
        1. Увеличиваем счетчик проваленных задач
        2. Сбрасываем текущую серию в 0
        """
        for habit_id in habit_ids:
            habit_streak = cls.objects.get(habit_id=habit_id)
            habit_streak.num_of_failed_tasks += 1
            habit_streak.current_streak = 0
            habit_streak.save()


# ==============================================
# МОДЕЛЬ ДОСТИЖЕНИЙ
# Пользователь получает их за определенные успехи (серия 7 дней, 14 дней и т.д.)
# ==============================================
class Achievement(models.Model):
    """
    Достижения бывают двух типов:
    1. За выполнение определенного количества дней подряд (7, 14, 30 дней)
    2. За прерывание серии ("Break The Habit") - когда пользователь срывается
    """

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='achievement')
    streak_length = models.IntegerField(default=0)  # Длина серии, за которую дали достижение
    title = models.CharField(max_length=255)  # Название достижения
    date = models.DateTimeField(null=True, blank=True)  # Когда получили

    @classmethod
    def update_achievements(cls, tasks):
        """
        Когда пользователь проваливает задачу, проверяем:
        1. Не было ли уже достижения "Break The Habit" для предыдущей задачи
        2. Если была текущая серия > 0 - создаем достижение
        """
        for task in tasks:
            # Проверяем, не было ли уже провалено предыдущее задание (чтобы не дублировать)
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
            # Если была серия (current_streak != 0) - создаем достижение
            if streak and streak.current_streak != 0:
                title = 'Break The Habit'
                streak_length = streak.current_streak if streak else 0
                cls.objects.create(habit=task.habit, date=task.due_date,
                                   title=title, streak_length=streak_length)

    @classmethod
    def rewards_streaks(cls, habit_id, streak):
        """
        Проверяем, не достигла ли текущая серия одного из порогов:
        - для ежедневных: 7, 14, 30 дней
        - для еженедельных: 1, 2, 4 недели
        - для ежемесячных: 1, 2, 4 месяца
        Если достигла - создаем соответствующее достижение.
        """
        habit = Habit.objects.get(pk=habit_id)

        # Ежедневные достижения
        if streak.current_streak / habit.frequency == 7 and habit.period == 'daily':
            title = '7-Day Streak'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak / habit.frequency == 14 and habit.period == 'daily':
            title = '14-Day Streak'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak / habit.frequency == 30 and habit.period == 'daily':
            title = '30-Day Streak'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)

        # Еженедельные достижения
        if habit.period == 'weekly' and (streak.current_streak / habit.frequency) == 1:
            title = '1-Week Streak'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if (streak.current_streak / habit.frequency) == 2 and habit.period == 'weekly':
            title = "2-Week's Streak"
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if (streak.current_streak / habit.frequency) == 4 and habit.period == 'weekly':
            title = "4-Week's Streak"
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)

        # Ежемесячные достижения
        if streak.current_streak // habit.frequency == 1 and habit.period == 'monthly':
            title = '1-Month Streak'
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak // habit.frequency == 2 and habit.period == 'monthly':
            title = "2-Month's Streak"
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)
        if streak.current_streak // habit.frequency == 4 and habit.period == 'monthly':
            title = "4-Month's Streak"
            cls.objects.create(habit=habit, date=timezone.now(), title=title,
                               streak_length=streak.current_streak)


# ==============================================
# МОДЕЛЬ ШАБЛОНОВ ПРИВЫЧЕК
# Готовые привычки, которые пользователь может выбрать
# ==============================================
class PredefinedHabit(models.Model):
    """
    Тут хранятся готовые привычки (Упражнения, Чтение, Медитация и т.д.)
    Не привязаны к конкретному пользователю - общие для всех.
    """

    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    frequency = models.IntegerField('Частота', default=1)
    period = models.CharField('Период', max_length=20, default='daily')
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
# Для кастомизации внешнего вида (пока не используется активно)
# ==============================================
class Theme(models.Model):
    """
    Позволяет пользователю настраивать цвета интерфейса.
    Пока не доделал, но основа есть.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='themes')
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
# Хранит информацию о том, с какого устройства зашел пользователь
# ==============================================
class DeviceSettings(models.Model):
    """
    Тут лежат настройки для разных устройств (компьютер, планшет, телефон).
    Чтобы сайт хорошо выглядел везде.
    """

    DEVICE_TYPES = [
        ('desktop', 'Компьютер'),
        ('tablet', 'Планшет'),
        ('mobile', 'Телефон'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_settings')
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
# Для разных вариантов расположения элементов на странице
# ==============================================
class LayoutTemplate(models.Model):
    """
    Заготовки для разных вариантов расположения элементов.
    Пока не используется, но может пригодиться для развития.
    """

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
# Все картинки, которые используются в приложении
# ==============================================
class ImageAsset(models.Model):
    """
    Тут хранятся все изображения: иконки, фоны, логотипы.
    Разделены по категориям для удобства.
    """

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