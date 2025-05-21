from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm as BasePasswordChangeForm,
    UserCreationForm as BaseUserCreationForm
)
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from .models import CompanyAdmin as User, Company

class UserCreationForm(BaseUserCreationForm):
    """Form for creating new users. Only accessible by superusers."""
    is_superuser = forms.BooleanField(
        required=False,
        label=_('Superuser status'),
        help_text=_('Designates that this user has all permissions without explicitly assigning them.')
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_superuser')
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # If the current user is a company admin, hide the is_superuser field
        if self.request and hasattr(self.request.user, 'company'):
            if 'is_superuser' in self.fields:
                del self.fields['is_superuser']
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if the current user has permission to create users
        if not self.request or not (self.request.user.is_superuser or hasattr(self.request.user, 'company')):
            raise PermissionDenied(_('You do not have permission to create users.'))
            
        # If this is a company admin, remove the is_superuser field
        if hasattr(self.request.user, 'company'):
            if 'is_superuser' in self.data:
                # If they tried to set is_superuser, remove it
                data = self.data.copy()
                data['is_superuser'] = False
                self.data = data
            cleaned_data['is_superuser'] = False
            
        return cleaned_data
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set the company for new users created by company admins
        if hasattr(self.request.user, 'company') and not user.is_superuser:
            user.company = self.request.user.company
            
        if commit:
            user.save()
            
        return user

class UserUpdateForm(forms.ModelForm):
    """Form for updating user information."""
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First name')
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last name')
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        exclude = ['email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email field read-only and not required
        self.fields['email'] = forms.EmailField(
            required=False,
            widget=forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': _('Email address')
            })
        )
        self.fields['email'].widget.attrs['disabled'] = True
        self.fields['email'].widget.attrs['class'] += ' text-muted'

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information."""
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Phone number')
        })
    )
    
    position = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Position')
        })
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Department')
        })
    )
    
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('About me')
        })
    )
    
    linkedin = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': _('LinkedIn profile URL')
        })
    )
    
    twitter = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': _('Twitter profile URL')
        })
    )
    
    class Meta:
        model = User
        fields = [
            'phone', 'position', 'department', 'bio', 
            'profile_picture', 'linkedin', 'twitter'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Phone number')
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your position')
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your department')
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Tell us about yourself...')
            }),
            'linkedin': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/username'
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/username'
            }),
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.isdigit():
            raise forms.ValidationError(_('Phone number should contain only digits.'))
        return phone

class CompanyForm(forms.ModelForm):
    """Form for updating company settings."""
    
    class Meta:
        model = Company
        exclude = ['admin']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class PasswordChangeForm(BasePasswordChangeForm):
    """Form for changing user's password."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
