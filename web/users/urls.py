from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User management (superuser only)
    path('users/', login_required(views.user_list), name='user_list'),
    path('users/create/', login_required(views.user_create), name='user_create'),
    
    # Profile management
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Company management
    path('company/create/', login_required(views.company_create), name='company_create'),
    path('company-profile/', views.company_profile, name='company_profile'),
]
