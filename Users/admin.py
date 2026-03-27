from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ['full_name', 'active_habit', 'email', 'date_joined']


class CustomUserAdmin(UserAdmin):
    """Управление пользователями"""
    inlines = [ProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} пользователей активировано.')

    make_active.short_description = 'Активировать выбранных пользователей'

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} пользователей деактивировано.')

    make_inactive.short_description = 'Деактивировать выбранных пользователей'


# Регистрируем пользователей
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# Группы
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)

# УБИРАЕМ регистрацию Profile - удалите или закомментируйте эти строки:
# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     """Управление профилями"""
#     list_display = ['user', 'full_name', 'active_habit', 'email', 'date_joined']
#     search_fields = ['user__username', 'full_name', 'email']
#     readonly_fields = ['full_name', 'active_habit', 'email', 'date_joined']


# Настройка внешнего вида админки
admin.site.site_header = "Панель управления oFp"
admin.site.site_title = "oFp - Ocean of possibilities"
admin.site.index_title = "Добро пожаловать в панель управления"