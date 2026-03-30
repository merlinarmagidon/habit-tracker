import json
from datetime import timedelta
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.core import serializers
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import HabitForm
from .models import TaskTracker, Habit, Streak, Achievement
from .analytics import (
    due_today_tasks, active_tasks, upcoming_tasks,
    calculate_progress, longest_current_streak_over_all_habits,
    all_tracked_habits, habits_by_period,
    longest_streak_over_all_habits, num_inprogress_tasks,
    update_user_activity, rank_habits, all_completed_habits
)


# ==============================================
# ГЛАВНАЯ СТРАНИЦА
# Тут показываются задачи, которые нужно сделать сегодня
# ==============================================
class HabitView(View):

    def dispatch(self, request, *args, **kwargs):
        # Сначала проверяем, зашел ли пользователь в аккаунт
        # Если нет - кидаем на гостевую страницу с кнопкой "Попробовать"
        if not request.user.is_authenticated:
            return render(request, 'home_guest.html')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Тут все для главной страницы, когда пользователь уже залогинен

        # Берем айдишник пользователя
        user_id = request.user.id

        # Эта функция проверяет, не просрочены ли какие-то задачи
        # Если просрочены - помечает их как "провалено"
        update_user_activity(user_id)

        # Задачи, которые надо сделать в ближайшие 24 часа
        today_tasks = due_today_tasks(user_id=user_id)

        # Задачи, которые можно выполнить прямо сейчас
        active_task = active_tasks(user_id=user_id)

        # Задачи, которые только планируются (еще не начались)
        upcoming_task = upcoming_tasks(user_id=user_id)

        # Нужно для приветствия типа "Привет, Алексей"
        user = User.objects.get(id=user_id)
        full_name = user.get_full_name()

        if full_name.strip():
            user_full_name = full_name.split()[0].capitalize()
        else:
            user_full_name = user.username.capitalize()

        # Собираем все в кучу и передаем в шаблон
        context = {
            'upcoming_tasks': upcoming_task,
            'due_today_tasks': today_tasks,
            'available_tasks': active_task,
            'user_full_name': user_full_name
        }

        return render(request, 'home.html', context)

    def post(self, request, *args, **kwargs):
        # Тут обрабатываем, когда пользователь нажимает "Отметить выполненным"

        if not request.user.is_authenticated:
            return redirect('login')

        # Достаем из формы айди задачи и айди привычки
        task_id = request.POST.get('task_id')
        habit_id = request.POST.get('habit_id')

        # Ищем эти объекты в базе данных
        task = get_object_or_404(TaskTracker, id=task_id)
        habit = get_object_or_404(Habit, id=habit_id)
        streak = get_object_or_404(Streak, habit_id=habit_id)

        try:
            # Меняем статус задачи на "выполнено"
            task.task_status = 'Completed'
            task.task_completion_date = timezone.now()
            task.save()

            # Если все ок, увеличиваем счетчик серии
            if task.task_status == 'Completed':
                streak.current_streak += 1
                streak.num_of_completed_tasks += 1
                # Тут проверяем, не пора ли дать пользователю награду
                Achievement.rewards_streaks(habit_id, streak)

                habit.save()
                streak.save()

                return redirect('habit-home')

        except TaskTracker.DoesNotExist:
            # Если что-то пошло не так - просто игнорируем
            pass

        return redirect('habit-home')


# ==============================================
# ТУТ ВСЕ ДЛЯ УПРАВЛЕНИЯ ПРИВЫЧКАМИ
# Добавление, удаление, просмотр списка
# ==============================================
class HabitManagerView(View):

    @staticmethod
    def add_habit(request):
        # Проверка на всякий случай, вдруг кто-то без аккаунта полезет
        if not request.user.is_authenticated:
            return redirect('login')

        # Список готовых привычек, чтобы пользователь не вбивал все вручную
        # Взял самые популярные, на мой взгляд
        pre_defined_habits = {
            'Упражнения': {
                'frequency': '2',
                'period': 'weekly',
                'goal': '1 month',
                'notes': 'Регулярные упражнения для поддержания физической формы.'
            },
            'Чтение': {
                'frequency': '1',
                'period': 'daily',
                'goal': '1 month',
                'notes': 'Чтение для личностного роста и обучения.'
            },
            'Чистка зубов': {
                'frequency': '2',
                'period': 'daily',
                'goal': '1 month',
                'notes': 'Напоминание о гигиене полости рта дважды в день.'
            },
            'Бюджет': {
                'frequency': '1',
                'period': 'weekly',
                'goal': '1 month',
                'notes': 'Планирование бюджета для финансовой стабильности.'
            },
            'Медитация': {
                'frequency': '1',
                'period': 'daily',
                'goal': '1 month',
                'notes': 'Ежедневная медитация для душевного равновесия.'
            },
            'Ежемесячный обзор': {
                'frequency': '1',
                'period': 'monthly',
                'goal': '1 year',
                'notes': 'Анализ достижений и планирование целей на месяц.'
            }
        }

        # Если пользователь отправил форму
        if request.method == 'POST':
            form = HabitForm(request.POST)
            if form.is_valid():
                # Проверяем, вообще реально ли достичь такой цели?
                if not form.is_goal_achievable():
                    messages.error(request,
                                   'Частота приводит к цели, которая не достижима. Выберите более длительную цель.')
                    return render(request, 'add_habit.html', {'form': form, 'pre_defined_habits': pre_defined_habits})

                # Проверяем, нет ли уже привычки с таким названием
                if not form.is_valid_habit_name(request.user):
                    messages.error(request, "Вы уже использовали это название для другой привычки")
                    return render(request, 'add_habit.html', {'form': form, 'pre_defined_habits': pre_defined_habits})

                # Берем дату начала из формы
                start_date = form.cleaned_data['start_date']
                # Создаем привычку, но пока не сохраняем в базу
                habit = form.save(commit=False)
                habit.user = request.user
                habit.start_date = start_date
                habit.save()

                # Генерируем задачи для этой привычки
                TaskTracker.create_tasks(habit)

                habit_name = form.cleaned_data.get('name')
                messages.success(request, f'Привычка "{habit_name}" создана')
                return redirect('habit-home')
        else:
            # Если просто открыли страницу - показываем пустую форму
            form = HabitForm()

        context = {
            'form': form,
            'pre_defined_habits': pre_defined_habits
        }

        return render(request, 'add_habit.html', context)

    @staticmethod
    def delete_habit(request, habit_id):
        # Удаление привычки со всеми ее задачами и сериями
        if not request.user.is_authenticated:
            return redirect('login')

        habit = get_object_or_404(Habit, pk=habit_id)

        if request.method == 'POST':
            try:
                habit.delete()
                messages.success(request, 'Привычка успешно удалена')
                return redirect('active_habits')
            except Habit.DoesNotExist:
                messages.error(request, 'Привычка не найдена')
                return redirect('active_habits')

        return render(request, 'habit_confirm_delete.html', {'habit': habit})

    @staticmethod
    def active_habits(request):
        # Показываем все активные привычки пользователя
        if not request.user.is_authenticated:
            return redirect('login')

        user_id = request.user.id

        # Берем все привычки, которые еще не завершены
        all_active_habits = all_tracked_habits(user_id=user_id)

        # Группируем по периоду (ежедневные, еженедельные, ежемесячные)
        daily_habits = habits_by_period('daily')(all_active_habits)
        weekly_habits = habits_by_period('weekly')(all_active_habits)
        monthly_habits = habits_by_period('monthly')(all_active_habits)

        # Считаем прогресс для каждой группы
        calculate_progress(all_active_habits)
        calculate_progress(daily_habits)
        calculate_progress(weekly_habits)
        calculate_progress(monthly_habits)

        context = {
            'active_habits': all_active_habits,
            'daily_habits': daily_habits,
            'weekly_habits': weekly_habits,
            'monthly_habits': monthly_habits,
        }
        return render(request, 'habit_manager.html', context)

    @staticmethod
    def habit_detail(request, habit_id):
        # Детальная страница конкретной привычки
        # Тут видно все задачи, серии, достижения
        if not request.user.is_authenticated:
            return redirect('login')

        habit = get_object_or_404(Habit, pk=habit_id)
        tasks = TaskTracker.objects.filter(habit_id=habit_id)
        streak = Streak.objects.get(habit_id=habit_id)
        achievement = Achievement.objects.filter(habit_id=habit_id)
        num_inprogress_tasks(habit)

        context = {
            'habit': habit,
            'tasks': tasks,
            'streak': streak,
            'achievement': achievement
        }

        return render(request, 'habit_details.html', context)


# ==============================================
# СТРАНИЦА АНАЛИТИКИ
# Тут всякая статистика, серии, графики (хотя с графиками были проблемы, но ладно)
# ==============================================
class HabitAnalysis(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        user_id = request.user.id

        # Получаем все привычки и сортируем по периодам
        all_habits = all_tracked_habits(user_id=user_id)
        daily_habits = habits_by_period('daily')(all_habits)
        weekly_habits = habits_by_period('weekly')(all_habits)
        monthly_habits = habits_by_period('monthly')(all_habits)

        # Завершенные привычки (те, у которых срок прошел)
        completed_habits = all_completed_habits(user_id)

        # Ищем самые длинные серии
        longest_current_all_streak = longest_current_streak_over_all_habits()
        longest_all_streak = longest_streak_over_all_habits()

        # Веса для расчета "сложных" привычек (методом тыка подобрал)
        weights = {
            'completed_tasks': -0.2,
            'failed_tasks': 0.8,
            'longest_streak': -0.2,
            'current_streak': -0.1
        }

        # Сортируем привычки по сложности
        daily_struggled_most = rank_habits(weights, 'daily')
        weekly_struggled_most = rank_habits(weights, 'weekly')

        # Считаем прогресс для всех групп
        calculate_progress(all_habits)
        calculate_progress(daily_habits)
        calculate_progress(weekly_habits)
        calculate_progress(monthly_habits)
        calculate_progress(longest_all_streak)
        calculate_progress(longest_current_all_streak)

        context = {
            'all_habits': all_habits,
            'daily_habits': daily_habits,
            'weekly_habits': weekly_habits,
            'monthly_habits': monthly_habits,
            'daily_struggled_most': daily_struggled_most,
            'weekly_struggled_most': weekly_struggled_most,
            'longest_all_streak': longest_all_streak,
            'longest_current_all_streak': longest_current_all_streak,
            'completed_habits': completed_habits,
        }

        return render(request, 'analysis.html', context)

    def post(self, request, *args, **kwargs):
        # AJAX запрос с фронтенда, когда выбирают конкретную привычку для детального анализа
        selected_value = request.POST.get('selectedValue')

        habit = Habit.objects.prefetch_related('streak').get(id=selected_value)

        habit_data = serializers.serialize('json', [habit])

        habit_dict = json.loads(habit_data)[0]['fields']

        habit_dict['streak'] = list(habit.streak.values())

        return JsonResponse(habit_dict, safe=False)