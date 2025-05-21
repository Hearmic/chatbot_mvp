from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CompanyAdmin, Company, Client

@admin.register(CompanyAdmin)
class CompanyAdminAdmin(BaseUserAdmin):
    """Admin configuration for CompanyAdmin model."""
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'position', 'department')}),
        (_('Profile'), {'fields': ('profile_picture', 'bio', 'linkedin', 'twitter')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin configuration for Company model."""
    list_display = (
        'name', 'email', 'phone', 'website', 'language', 'timezone'
    )
    list_filter = ('language', 'timezone')
    search_fields = ('name', 'email', 'phone', 'website')
    fieldsets = (
        (_('Basic Info'), {
            'fields': ('name', 'description', 'address', 'phone', 'email', 'website')
        }),
        (_('Bot Configuration'), {
            'fields': (
                'language', 'timezone',
                'response_delay', 'typing_duration', 'max_retries',
                'enable_analytics', 'collect_feedback',
                'available_languages',
                'allowed_topics', 'restricted_topics'
            )
        }),
        (_('Working Hours'), {
            'fields': (
                'monday_hours', 'tuesday_hours', 'wednesday_hours',
                'thursday_hours', 'friday_hours', 'saturday_hours',
                'sunday_hours'
            )
        }),
        (_('Messages'), {
            'fields': (
                'welcome_message', 'fallback_message',
                'handoff_message', 'off_hours_message',
                'thanks_message'
            )
        }),
        (_('Admin Settings'), {
            'fields': (
                'admin_id', 'notifications_enabled',
                'notification_hours', 'email_notifications',
                'admin_email'
            )
        }),
    )

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin configuration for Client model."""
    list_display = ('name', 'email', 'phone', 'company', 'created_at', 'updated_at')
    list_filter = ('company',)
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('company', 'name', 'email', 'phone')
        }),
        # Removed date fields as they don't exist in the model,
    )
