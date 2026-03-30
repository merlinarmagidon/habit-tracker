"""
Этот файл содержит функции для анализа привычек.
Тут мы считаем прогресс, ищем просроченные задачи,
ранжируем привычки по сложности и обновляем активность пользователя.
Честно говоря, некоторые функции я писал несколько раз, пока не заработало как надо.
"""

from datetime import timedelta
from functools import partial
import numpy as np
from django.utils import timezone
from django.db.models import Min, Prefetch
from habit.models import TaskTracker, Habit, Streak, Achievement


# ==============================================
# ПОЛУЧЕНИЕ АКТИВНЫХ ПРИВЫЧЕК
# ==============================================
def all_tracked_habits(user_id):
    """
    Ищем все привычки пользователя, которые еще не завершены.
    Заодно подгружаем информацию о сериях (чтобы потом не делать лишние запросы к базе).
    Без prefetch_related было очень много запросов, сайт тормозил.
    """
    return Habit.objects.filter(user_id=user_id,
                                completion_date__gte=timezone.now()
                                ).prefetch_related('streak')


# ==============================================
# ФИЛЬТРАЦИЯ ПО ПЕРИОДУ
# ==============================================
def habits_by_period(period):
    """
    Возвращает функцию, которая будет фильтровать привычки по заданному периоду.
    Использую partial, чтобы не писать каждый раз одно и то же.
    Сначала я просто копипастил код, потом понял что так удобнее.
    """
    return partial(filter_habits_by_period, period)


def filter_habits_by_period(period, habits):
    """
    Просто отфильтровываем привычки, у которых period совпадает с нужным.
    """
    return habits.filter(period=period)


# ==============================================
# ПОИСК САМЫХ ДЛИННЫХ СЕРИЙ
# ==============================================
def longest_current_streak_over_all_habits():
    """
    Смотрим в таблице Streak, у какой привычки current_streak самая большая.
    Возвращаем саму привычку (с предзагрузкой серий).
    Если серий нет - возвращаем пустой список, чтобы не было ошибки.
    """
    first_streak = Streak.objects.order_by('-current_streak').first()
    if first_streak is None:
        return Habit.objects.none()
    return Habit.objects.filter(id=first_streak.habit_id).prefetch_related('streak')


def longest_streak_over_all_habits():
    """
    То же самое, но смотрим на longest_streak (рекордную серию).
    """
    first_streak = Streak.objects.order_by('-longest_streak').first()
    if first_streak is None:
        return Habit.objects.none()
    return Habit.objects.filter(id=first_streak.habit_id).prefetch_related('streak')


def longest_streak_for_habit(id):
    """
    Просто берем привычку по id и подгружаем ее серии.
    """
    return Habit.objects.prefetch_related('streak').get(id=id)


# ==============================================
# ЗАДАЧИ (СРОКИ, АКТИВНЫЕ, ПРЕДСТОЯЩИЕ)
# ==============================================
def due_today_tasks(user_id):
    """
    Ищем задачи, у которых due_date в промежутке от сейчас до +25 часов.
    Немного с запасом, чтобы точно все попало.
    Потому что у меня были проблемы с часовыми поясами.
    """
    now = timezone.now()
    twenty_four_hours = now + timedelta(hours=25, minutes=2)
    due_today = TaskTracker.objects.filter(
        habit__user_id=user_id,
        due_date__range=(now, twenty_four_hours),
        task_status='In progress'
    )
    return due_today


def active_tasks(user_id):
    """
    Ищем задачи со статусом 'In progress', у которых start_date уже наступил,
    а due_date еще не наступил. Плюс небольшой запас в 1 час.
    """
    now = timezone.now()+timedelta(hours=1)
    tasks = TaskTracker.objects.filter(
        habit__user_id=user_id,
        task_status='In progress',
        start_date__lte=now,
        due_date__gt=now
    )
    return tasks


def upcoming_tasks(user_id):
    """
    Берем задачи с номером 1 (первые в цепочке), у которых start_date в будущем.
    Думал сделать все задачи, но тогда слишком много всего.
    """
    tasks = TaskTracker.objects.filter(habit__user_id=user_id,
                                       start_date__gte=timezone.now()+timedelta(hours=1),
                                       task_number=1)
    return tasks


# ==============================================
# ПРОГРЕСС
# ==============================================
def calculate_progress(habits):
    """
    Для каждой привычки считаем процент выполнения:
    (сколько задач выполнено / сколько всего задач) * 100
    """
    for habit in habits:
        if habit.num_of_tasks > 0:
            streak = habit.streak.first()
            habit.progress_percentage = round(
                (streak.num_of_completed_tasks / habit.num_of_tasks) * 100, 2)
        else:
            habit.progress_percentage = 0.0


def num_inprogress_tasks(habit):
    """
    Просто считаем количество задач со статусом 'In progress' для данной привычки.
    """
    in_progress_num = TaskTracker.objects.filter(habit=habit, task_status='In progress').count()
    habit.in_progress = in_progress_num


# ==============================================
# СЛОЖНЫЕ РАСЧЕТЫ ДЛЯ РАНЖИРОВАНИЯ
# Тут я использовал numpy, хотя сначала пытался без него, но не получилось
# ==============================================
def calculate_score(completed_tasks, failed_tasks, longest_streak, current_streak,
                    num_of_tasks, duration, weights):
    """
    Формула оценки:
    (вес_выполненных * выполненные + вес_проваленных * проваленные +
     вес_макс_серии * макс_серия + вес_тек_серии * тек_серия) / (всего_задач * длительность)
    Чем больше проваленных задач - тем выше оценка (привычка сложнее).
    Веса подбирал экспериментально, методом тыка.
    """
    score = (weights['completed_tasks'] * completed_tasks +
             weights['failed_tasks'] * failed_tasks +
             weights['longest_streak'] * longest_streak +
             weights['current_streak'] *current_streak
             ) / (num_of_tasks * duration)
    return score


def normalize_scores(scores):
    """
    Используем Z-нормализацию: (x - среднее) / стандартное_отклонение.
    Чтобы оценки разных привычек можно было сравнивать.
    Без этого одна привычка с большим количеством задач всегда была бы в топе.
    """
    mu = np.mean(scores)
    sigma = np.std(scores)
    z_scores = []
    for x in scores:
        if sigma != 0:
            z_scores.append((x - mu) / sigma)
        else:
            z_scores.append(np.nan)  # Если стандартное отклонение = 0, оценка не определена
    return z_scores


def rank_habits(weights, period):
    """
    Для всех привычек заданного периода считаем оценки, нормализуем и сортируем.
    Возвращаем список кортежей (привычка, нормализованная_оценка) в порядке убывания.
    Сначала я пытался сделать это в лоб, но было слишком много запросов к базе.
    """
    scores = []
    now = timezone.now()
    last_month = now - timedelta(days=30)

    # Заранее подгружаем серии, чтобы не делать много запросов в цикле
    prefetch_streaks = Prefetch('streak', queryset=Streak.objects.all())
    habits = Habit.objects.prefetch_related(prefetch_streaks).filter(period=period,
                                                creation_time__range=(last_month, now))

    for habit in habits:
        streak = habit.streak.latest('id')
        if streak is not None:
            num_of_tasks = habit.num_of_tasks
            completed_tasks = streak.num_of_completed_tasks
            failed_tasks = streak.num_of_failed_tasks
            longest_streak = streak.longest_streak
            current_streak = streak.current_streak
            # Вычитаем один день, чтобы не было деления на ноль
            duration = (now - (habit.creation_time - timedelta(days=1))).days

            score = calculate_score(completed_tasks, failed_tasks, longest_streak,
                                    current_streak, num_of_tasks, duration, weights)

            scores.append(score)
        else:
            pass

    normalized_scores = normalize_scores(scores)
    ranked_habits = sorted(zip(habits, normalized_scores), key=lambda x: x[1], reverse=True)

    return ranked_habits


# ==============================================
# ЗАВЕРШЕННЫЕ ПРИВЫЧКИ
# ==============================================
def all_completed_habits(user_id):
    """
    Ищем привычки, у которых completion_date уже прошел.
    Подгружаем серии, чтобы потом не делать лишние запросы.
    """
    prefetch_streaks = Prefetch('streak', queryset=Streak.objects.all())
    return Habit.objects.prefetch_related(prefetch_streaks).filter(user_id=user_id, completion_date__lt=timezone.now())


# ==============================================
# ПЕРВАЯ ПРОВАЛЕННАЯ ЗАДАЧА
# Нужно для достижения "Break The Habit"
# ==============================================
def extract_first_failed_task(updated_task_ids):
    """
    Когда пользователь проваливает несколько задач подряд,
    нам нужно найти самую первую проваленную для каждой привычки.
    Это важно для достижения "Break The Habit".
    """
    # Для каждой привычки находим минимальный номер задачи среди проваленных
    min_task_numbers = TaskTracker.objects.filter(
        id__in=updated_task_ids
        ).values('habit_id').annotate(min_task_number=Min('task_number'))

    # Берем задачи с этими минимальными номерами
    first_failed_tasks = TaskTracker.objects.filter(
        id__in=updated_task_ids,
        task_number__in=min_task_numbers.values('min_task_number')
        ).order_by('habit_id')

    return first_failed_tasks


# ==============================================
# ОБНОВЛЕНИЕ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЯ
# Самая важная функция, которую я вызываю при каждом заходе на главную
# ==============================================
def update_user_activity(user_id):
    """
    Главная функция, которую вызываем периодически.
    1. Обновляем статусы просроченных задач на 'Failed'
    2. Находим первые проваленные задачи
    3. Обновляем достижения (если провалена задача)
    4. Обновляем серии (сбрасываем текущую серию)
    """

    # Обновляем статусы задач с 'In progress' на 'Failed' и получаем их id
    updated_habit_tasks_ids = TaskTracker.update_failed_tasks(user_id=user_id)
    updated_habit_ids, updated_task_ids = updated_habit_tasks_ids

    # Находим первые проваленные задачи (для достижений)
    first_failed_tasks = extract_first_failed_task(updated_task_ids)

    # Обновляем достижения
    Achievement.update_achievements(first_failed_tasks)
    # Обновляем серии (сбрасываем текущую)
    Streak.update_streak(updated_habit_ids)