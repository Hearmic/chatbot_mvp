from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from functools import wraps

def admin_required(view_func=None, login_url='users:login'):
    """
    Decorator for views that checks that the user is logged in and is a staff member.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please log in to access this page.')
                return redirect(login_url + f'?next={request.path}')
            if not request.user.is_staff:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('admin_panel:admin_dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator

def unauthenticated_user(view_func=None, redirect_url='admin_panel:admin_dashboard'):
    """
    Decorator for views that checks that the user is not logged in.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator
