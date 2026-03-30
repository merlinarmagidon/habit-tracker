from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from Users import views as user_views
from habit import views as habit_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# ==============================================
# ГЛАВНЫЕ МАРШРУТЫ ВСЕГО САЙТА
# Тут я прописал все URL, по которым можно перейти
# Сначала была каша, потом разложил по полочкам
# ==============================================

urlpatterns = [
    # Админка
    path('admin/', admin.site.urls),

    # Пользователи (регистрация, вход, профиль, выход)
    path('Login', user_views.user_login, name='login'),  # Страница входа (кастомная)
    path('Register/', user_views.register, name='register'),  # Регистрация
    path('Profile/', user_views.profile, name='profile'),  # Профиль пользователя
    path('Logout', auth_views.LogoutView.as_view(template_name='Users/logout.html'), name='logout'),  # Выход

    # Главная страница
    path('', habit_views.HabitView.as_view(), name='habit-home'),

    # Управление привычками
    path('Add-Habit/', habit_views.HabitManagerView.add_habit, name='habit_creation'),  # Добавить привычку
    path('delete-habit/<int:habit_id>/', habit_views.HabitManagerView.delete_habit, name='habit_deletion'),  # Удалить
    path('Habit-Manager/', habit_views.HabitManagerView.active_habits, name='active_habits'),  # Список привычек
    path('Habit-Infos/<int:habit_id>/', habit_views.HabitManagerView.habit_detail, name='habit_detail'),  # Детали

    # Аналитика
    path('Habits-Analysis/', habit_views.HabitAnalysis.as_view(), name='HabitsAnalysis'),

    # Информационные страницы
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),  # О нас
    path('contacts/', TemplateView.as_view(template_name='contacts.html'), name='contacts'),  # Контакты

    # Восстановление пароля
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='Users/password_reset.html',
             email_template_name='Users/password_reset_email.html',
             subject_template_name='Users/password_reset_subject.txt'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='Users/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='Users/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='Users/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

# В режиме разработки добавляем маршруты для медиа-файлов (картинки пользователей)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)