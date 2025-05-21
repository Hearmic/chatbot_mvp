from django.urls import path, include
from django.views.generic import RedirectView
from .views import (
    select_service, input_connection_data, data_transfer_options, sync_users,
    dashboard, bot_settings
)

app_name = 'admin_panel'

urlpatterns = [
    # Main pages
    path('', dashboard, name='admin_dashboard'),
    path('dashboard/', dashboard, name='dashboard'),
    path('bot-settings/', bot_settings, name='bot_settings'),
    
    # Service-related URLs
    path('select-service/', select_service, name='select_service'),
    path('input-connection-data/<str:service>/', input_connection_data, name='input_connection_data'),
    path('data-transfer-options/<str:service>/', data_transfer_options, name='data_transfer_options'),
    path('data-transfer-options/', data_transfer_options, name='data_transfer_options_default'),
    path('sync-users/<str:service>/', sync_users, name='sync_users'),
    path('sync-users/', sync_users, name='sync_users_default'),
]