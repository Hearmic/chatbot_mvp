from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Message, Integration, FAQ, Policy

# Get the custom user model
User = get_user_model()

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('company', 'category', 'title', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'company')
    search_fields = ('title', 'content', 'company__name')
    ordering = ('category', 'title')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('company')
    
    fieldsets = (
        (None, {'fields': ('category', 'title', 'content', 'is_active')}),
        ('Company', {'fields': ('company',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('category', 'title', 'content', 'is_active', 'company')}
        ),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('truncated_content', 'user', 'company', 'timestamp')
    list_filter = ('timestamp', 'company')
    search_fields = ('content', 'user__email', 'user__username')
    date_hierarchy = 'timestamp'
    list_select_related = ('user', 'company')
    
    def truncated_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    truncated_content.short_description = 'Content'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('service', 'company', 'created_at', 'updated_at')
    list_filter = ('service', 'created_at', 'company')
    search_fields = ('company__name', 'service')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('company',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)
    
    def created_at(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else 'N/A'
    created_at.short_description = 'Created At'
    
    def updated_at(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else 'N/A'
    updated_at.short_description = 'Updated At'