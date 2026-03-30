"""
Формы для создания привычек.
Тут описана форма, через которую пользователь добавляет новую привычку.
Долго мучился с валидацией, особенно с проверкой уникальности названия.
"""

from django import forms
from django.core.validators import MinValueValidator
from .models import Habit
from .utils import convert_goal_to_days


# ==============================================
# ФОРМА ДЛЯ ДОБАВЛЕНИЯ ПРИВЫЧКИ
# ==============================================
class HabitForm(forms.ModelForm):
    """
    Эта форма отображается на странице /Add-Habit/.
    Пользователь вводит:
    - название привычки
    - частоту (сколько раз в период)
    - период (ежедневно, еженедельно, ежемесячно)
    - цель (на сколько дней)
    - заметки
    - дату начала
    """

    # Варианты для выпадающего списка "Период"
    # Сначала были на английском, потом перевел
    PERIOD_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно')
        # annual убрал, потому что никто не пользуется
    ]

    # Варианты для выпадающего списка "Цель"
    GOAL_CHOICES = [
        ('3 days', '3 дня'),
        ('1 week', '1 неделя'),
        ('1 month', '1 месяц'),
        ('2 months', '2 месяца'),
        ('3 months', '3 месяца'),
        ('6 months', '6 месяцев'),
        ('1 year', '1 год')
    ]

    # Явно описываем поля формы (некоторые берем из модели, некоторые добавляем сами)
    period = forms.ChoiceField(choices=PERIOD_CHOICES, widget=forms.Select, required=True)
    frequency = forms.IntegerField(initial=1, required=False, validators=[MinValueValidator(1)])
    notes = forms.CharField(required=False)
    goal = forms.ChoiceField(choices=GOAL_CHOICES, widget=forms.Select, required=True)
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'start-date-field'}),
        required=True
    )

    def clean_goal(self):
        """
        Пользователь выбирает из списка "1 месяц", а мы должны сохранить в базу число 30.
        Эта функция преобразует текст в число.
        Сначала я пытался хранить как текст, но потом понял что так неудобно считать.
        """
        selected_goal = self.cleaned_data.get('goal')
        return convert_goal_to_days(selected_goal)

    def is_valid_habit_name(self, user):
        """
        Нельзя создать две привычки с одинаковым названием у одного пользователя.
        Проверяем, нет ли уже такой в базе (без учета регистра).
        Пользователи жаловались, что "Чтение" и "чтение" - это одно и то же.
        """
        habit_name = self.cleaned_data['name']

        # Ищем в базе (без учета регистра)
        if Habit.objects.filter(user=user, name__iexact=habit_name).exists():
            return False
        return True

    def is_goal_achievable(self):
        """
        Проверяем, достижима ли цель.
        Если пользователь выбрал период "ежедневно" и цель "3 дня" - все ок.
        Но если период "ежемесячно" и цель "3 дня" - цель меньше периода, так нельзя.
        Об этом меня попросили на защите курсовой.
        """
        goal = self.cleaned_data.get('goal')
        period = self.cleaned_data.get('period')

        # Сколько дней в одном периоде
        num = 1
        if period == 'daily':
            num = 1
        elif period == 'weekly':
            num = 7
        elif period == 'monthly':
            num = 30
        elif period == 'annual':
            num = 365

        return num < goal

    class Meta:
        """
        Настройки формы: с какой моделью работаем и какие поля показываем.
        """
        model = Habit
        fields = ['name', 'frequency', 'period', 'goal', 'notes', 'start_date']