from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import PasswordChangeForm as BasePasswordChangeForm
from .models import FAQ, Policy
from users.models import Company, CompanyAdmin

class FAQForm(forms.ModelForm):
    """Form for creating and updating FAQs."""
    
    class Meta:
        model = FAQ
        fields = ['category', 'question', 'answer']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        }

class PolicyForm(forms.ModelForm):
    """Form for creating and updating policies."""
    
    class Meta:
        model = Policy
        fields = ['category', 'title', 'content', 'is_active']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class CompanyForm(forms.ModelForm):
    """Form for updating company settings."""
    
    class Meta:
        model = Company
        fields = [
            'name',
            'description',
            'address',
            'phone',
            'email',
            'website',
            'language',
            'timezone',
            'monday_hours',
            'tuesday_hours',
            'wednesday_hours',
            'thursday_hours',
            'friday_hours',
            'saturday_hours',
            'sunday_hours',
            'welcome_message',
            'fallback_message',
            'handoff_message',
            'off_hours_message',
            'thanks_message',
            'response_delay',
            'typing_duration',
            'max_retries',
            'enable_analytics',
            'collect_feedback',
            'available_languages',
            'allowed_topics',
            'restricted_topics',
            'admin_id',
            'notifications_enabled',
            'notification_hours',
            'email_notifications',
            'admin_email'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all form fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

        # Add Switch widget for notification settings
        if field_name in ['notifications_enabled', 'email_notifications']:
            field.widget = forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'switch'
            })

        # Add special classes for specific fields
        if field_name in ['allowed_topics', 'restricted_topics', 'available_languages']:
            field.widget.attrs['class'] += ' tags-input'
            field.widget.attrs['rows'] = 3
            field.widget.attrs['class'] += ' policy-textarea'

        # Add placeholders
        self.fields['name'].widget.attrs['placeholder'] = _('Company name')
        self.fields['description'].widget.attrs['placeholder'] = _('Company description')
        self.fields['address'].widget.attrs['placeholder'] = _('Company address')
        self.fields['phone'].widget.attrs['placeholder'] = _('Phone number')
        self.fields['email'].widget.attrs['placeholder'] = _('Email address')
        self.fields['website'].widget.attrs['placeholder'] = _('Website URL')
        self.fields['welcome_message'].widget.attrs['placeholder'] = _('Welcome message')
        self.fields['fallback_message'].widget.attrs['placeholder'] = _('Fallback message')
        self.fields['handoff_message'].widget.attrs['placeholder'] = _('Handoff message')
        self.fields['off_hours_message'].widget.attrs['placeholder'] = _('Off hours message')
        self.fields['thanks_message'].widget.attrs['placeholder'] = _('Thanks message')
        self.fields['allowed_topics'].widget.attrs['placeholder'] = _('Allowed topics')
        self.fields['restricted_topics'].widget.attrs['placeholder'] = _('Restricted topics')
        self.fields['handoff_trigger'].widget.attrs['placeholder'] = _('Handoff triggers')
        self.fields['admin_email'].widget.attrs['placeholder'] = _('Admin email')
        self.fields['notification_hours'].widget.attrs['placeholder'] = _('Notification hours')
        self.fields['available_languages'].widget.attrs['placeholder'] = _('Available languages')

        # Add data attributes for time inputs
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            field_name = f'{day}_hours'
            self.fields[field_name].widget.attrs['data-day'] = day
            self.fields[field_name].widget.attrs['placeholder'] = _('HH:MM-HH:MM')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not phone.isdigit():
            raise forms.ValidationError(_('Phone number should contain only digits.'))
        return phone

    def save(self, commit=True):
        # Save the company first
        company = super().save(commit=False)
        
        # Create policy JSON
        policy = {
            'company_info': {
                'name': self.cleaned_data['company_name'],

            },
            'messages': {
                'welcome': self.cleaned_data['welcome_message'],
            },
            'support': {
                'email': self.cleaned_data['support_email'],
                'phone': self.cleaned_data['support_phone'],
            },
            'data_retention_days': self.cleaned_data['data_retention_days']
        }
        
        # Update company fields
        company.policy = policy
        company.name = self.cleaned_data['company_name']
        
        if commit:
            company.save()
        return company


        # Make email required
        self.fields['email'].required = True
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CompanyAdmin.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('This email is already in use.'))
        return email

class CustomPasswordChangeForm(BasePasswordChangeForm):
    """
    Form for changing a user's password with custom styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
            
        # Add your custom password validation here if needed
        # Example: Check for minimum length, complexity, etc.
        
        return password2


class AdminUserForm(forms.ModelForm):
    """Form for creating and updating admin users."""
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False  # Not required for updates
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False  # Not required for updates
    )
    
    class Meta:
        model = CompanyAdmin
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'position', 'department', 'is_active', 'is_staff'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 or password2:  # Only validate if passwords are being changed
            if password1 != password2:
                raise forms.ValidationError('Passwords do not match')
            if len(password1) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long')

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:  # If updating an existing user
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].widget = forms.HiddenInput()
            self.fields['password2'].widget = forms.HiddenInput()
            self.fields['email'].disabled = True  # Email can't be changed after creation
