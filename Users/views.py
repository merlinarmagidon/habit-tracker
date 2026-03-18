from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from .models import Profile


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'Users/register.html', {'form': form})


def user_login(request):
    error_message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('habit-home')
        else:
            # Просто передаем ошибку через контекст
            error_message = 'Неверный пароль или имя пользователя'

    return render(request, 'Users/login.html', {'error': error_message})


@login_required
def profile(request):
    if request.method == 'GET':
        profile_instance, create = Profile.objects.get_or_create(user=request.user)
    return render(request, 'Users/profile.html', {'profile': profile_instance})