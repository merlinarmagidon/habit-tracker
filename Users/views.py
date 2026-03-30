from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from .models import Profile


# ==============================================
# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
# ==============================================
def register(request):
    """
    Тут происходит регистрация нового пользователя.
    Если форма отправлена и валидна - создаем пользователя и кидаем на страницу входа.
    Если нет - показываем форму с ошибками.

    Сначала я забыл про проверку на is_valid(), и пользователи могли регистрироваться с пустыми полями.
    """
    # Если пользователь отправил форму (метод POST)
    if request.method == 'POST':
        # Создаем форму с данными из запроса
        form = UserRegisterForm(request.POST)
        # Проверяем, все ли поля заполнены правильно
        if form.is_valid():
            # Сохраняем нового пользователя в базу данных
            form.save()
            # Достаем имя пользователя из формы
            username = form.cleaned_data.get('username')
            # Показываем сообщение об успехе
            messages.success(request, f'Аккаунт создан для {username}')
            # Отправляем пользователя на страницу входа
            return redirect('login')
    else:
        # Если пользователь просто открыл страницу - показываем пустую форму
        form = UserRegisterForm()
    # Отображаем шаблон с формой
    return render(request, 'Users/register.html', {'form': form})


# ==============================================
# ВХОД ПОЛЬЗОВАТЕЛЯ (КАСТОМНЫЙ)
# ==============================================
def user_login(request):
    """
    Тут пользователь входит в систему.
    Я переписал стандартную Django-шную функцию, потому что хотел кастомную обработку ошибок.

    Проблема была в том, что стандартная форма сама показывала ошибки,
    а мне хотелось свои сообщения.
    """
    # Переменная для хранения ошибки (если будет)
    error_message = None

    # Если пользователь отправил форму входа
    if request.method == 'POST':
        # Получаем логин и пароль из формы
        username = request.POST.get('username')
        password = request.POST.get('password')
        # Проверяем, есть ли такой пользователь в базе
        user = authenticate(request, username=username, password=password)

        # Если пользователь найден и пароль правильный
        if user is not None:
            # Выполняем вход (создаем сессию)
            login(request, user)
            # Отправляем на главную
            return redirect('habit-home')
        else:
            # Если данные неверные - показываем ошибку
            error_message = 'Неверный пароль или имя пользователя'

    # Отображаем страницу входа (передаем ошибку, если есть)
    return render(request, 'Users/login.html', {'error': error_message})


# ==============================================
# ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ==============================================
@login_required
def profile(request):
    """
    Страница профиля пользователя.
    Тут показывается информация о пользователе.

    @login_required - декоратор, который не пускает на страницу неавторизованных.
    Сначала я забыл его поставить, и кто попало мог смотреть чужие профили.
    """
    # Если пользователь открыл страницу (метод GET)
    if request.method == 'GET':
        # Пытаемся найти профиль пользователя, если нет - создаем новый
        profile_instance, create = Profile.objects.get_or_create(user=request.user)
    # Отображаем страницу профиля с данными
    return render(request, 'Users/profile.html', {'profile': profile_instance})