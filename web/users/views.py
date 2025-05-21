from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponseForbidden
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import permission_required
from django.utils.translation import gettext_lazy as _
import os

from .models import CompanyAdmin as User, Company
from .forms import (
    UserUpdateForm, ProfileUpdateForm, 
    PasswordChangeForm, CompanyForm, UserCreationForm
)

@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """View for user profile management."""
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'users/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """View for changing user's password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {
        'form': form
    })

@require_http_methods(["GET", "POST"])
def login_view(request):
    """View for user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('users:profile')
    else:
        form = AuthenticationForm()
    
    return render(request, 'users/login.html', {
        'form': form
    })

def logout_view(request):
    """View for user logout."""
    logout(request)
    return redirect('users:login')

@login_required
def user_list(request):
    """
    List users based on the current user's permissions:
    - Superusers see all users
    - Company admins see users from their company
    - Regular users are redirected to their profile
    """
    if not request.user.is_authenticated:
        return redirect('users:login')
        
    if not (request.user.is_superuser or hasattr(request.user, 'company')):
        return redirect('users:profile')
    
    users = User.objects.all()
    
    # If it's a company admin, filter users by their company
    if hasattr(request.user, 'company') and not request.user.is_superuser:
        users = users.filter(company=request.user.company)
    
    return render(request, 'users/user_list.html', {
        'users': users,
        'has_permission': request.user.is_superuser or hasattr(request.user, 'company')
    })

@login_required
def user_create(request):
    """
    Create a new user:
    - Superusers can create any user
    - Company admins can create users for their company
    - Regular users cannot create users
    """
    if not (request.user.is_superuser or hasattr(request.user, 'company')):
        return HttpResponseForbidden(_("You don't have permission to create users."))
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST, request=request)
        if form.is_valid():
            user = form.save(commit=False)
            # If the current user is a company admin, assign the new user to their company
            if hasattr(request.user, 'company') and not user.is_superuser:
                user.company = request.user.company
            user.save()
            messages.success(request, _('User created successfully.'))
            return redirect('users:user_list')
    else:
        initial = {}
        # If the current user is a company admin, pre-fill the company
        if hasattr(request.user, 'company'):
            initial['company'] = request.user.company
        form = UserCreationForm(initial=initial, request=request)
    
    return render(request, 'users/user_form.html', {
        'form': form,
        'title': _('Create User'),
        'is_superuser': request.user.is_superuser
    })

@login_required
def company_create(request):
    """
    Create a new company (superuser only).
    Company admins cannot create new companies.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden(_("You don't have permission to create companies."))
    
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.admin = request.user
            company.save()
            messages.success(request, _('Company created successfully.'))
            return redirect('users:company_profile')
    else:
        form = CompanyForm()
    
    return render(request, 'users/company_form.html', {
        'form': form,
        'title': _('Create Company')
    })

@login_required
@require_http_methods(["GET", "POST"])
def company_profile(request):
    """View for company profile management."""
    try:
        company = Company.objects.get(admin=request.user)
    except Company.DoesNotExist:
        company = None
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            company = form.save(commit=False)
            company.admin = request.user
            company.save()
            messages.success(request, 'Company profile updated successfully')
            return redirect('users:company_profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'users/company_profile.html', {
        'form': form,
        'company': company
    })
