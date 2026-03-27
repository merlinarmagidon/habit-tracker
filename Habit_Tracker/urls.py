from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from Users import views as user_views
from habit import views as habit_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

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

    path('Login', user_views.user_login, name='login'),
    path('Register/', user_views.register, name='register'),
    path('Profile/', user_views.profile, name='profile'),
    path('Logout', auth_views.LogoutView.as_view(template_name='Users/logout.html'), name='logout'),
    path('', habit_views.HabitView.as_view(), name='habit-home'),
    path('Add-Habit/', habit_views.HabitManagerView.add_habit, name='habit_creation'),
    path('delete-habit/<int:habit_id>/', habit_views.HabitManagerView.delete_habit, name='habit_deletion'),
    path('Habit-Manager/', habit_views.HabitManagerView.active_habits, name='active_habits'),
    path('Habit-Infos/<int:habit_id>/', habit_views.HabitManagerView.habit_detail, name='habit_detail'),
    path('Habits-Analysis/', habit_views.HabitAnalysis.as_view(), name='HabitsAnalysis'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contacts/', TemplateView.as_view(template_name='contacts.html'), name='contacts'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)