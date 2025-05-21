from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
            
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def get_queryset(self):
        """
        Filter users based on the current user's permissions:
        - Superusers see all users
        - Company admins see users from their company
        - Regular users see only themselves
        """
        request = getattr(self, '_request', None)
        if not request:
            return super().get_queryset().none()
            
        user = request.user
        if user.is_superuser:
            return super().get_queryset()
            
        # For company admins, get their company and return its users
        if hasattr(user, 'company'):
            return super().get_queryset().filter(company=user.company)
            
        # Regular users can only see themselves
        return super().get_queryset().filter(pk=user.pk)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CompanyAdmin(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='admins', null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

class CompanyManager(models.Manager):
    def get_queryset(self):
        """
        Filter companies based on the current user's permissions:
        - Superusers see all companies
        - Company admins see only their company
        - Regular users see no companies
        """
        request = getattr(self, '_request', None)
        if not request:
            return super().get_queryset().none()
            
        user = request.user
        if user.is_superuser:
            return super().get_queryset()
            
        # Company admins can see only their company
        if hasattr(user, 'company'):
            return super().get_queryset().filter(pk=user.company.pk)
            
        # Regular users can't see any companies
        return super().get_queryset().none()

class Company(models.Model):
    objects = CompanyManager()
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Bot Configuration
    language = models.CharField(max_length=2, choices=[
        ('ru', 'Russian'),
        ('kz', 'Kazakh'),
        ('en', 'English')
    ], default='ru')
    timezone = models.CharField(max_length=50, choices=[
        ('UTC', 'UTC'),
        ('Asia/Almaty', 'Asia/Almaty'),
        ('Europe/Moscow', 'Europe/Moscow'),
        ('Asia/Tokyo', 'Asia/Tokyo'),
        ('America/New_York', 'America/New_York'),
        ('America/Los_Angeles', 'America/Los_Angeles'),
    ], default='Asia/Almaty')
    
    # Working Hours
    monday_hours = models.CharField(max_length=20, default='9:00-21:00')
    tuesday_hours = models.CharField(max_length=20, default='9:00-21:00')
    wednesday_hours = models.CharField(max_length=20, default='9:00-21:00')
    thursday_hours = models.CharField(max_length=20, default='9:00-21:00')
    friday_hours = models.CharField(max_length=20, default='9:00-21:00')
    saturday_hours = models.CharField(max_length=20, default='9:00-21:00')
    sunday_hours = models.CharField(max_length=20, default='9:00-21:00')
    
    # Bot Messages
    welcome_message = models.TextField(blank=True, null=True)
    fallback_message = models.TextField(blank=True, null=True)
    handoff_message = models.TextField(blank=True, null=True)
    off_hours_message = models.TextField(blank=True, null=True)
    thanks_message = models.TextField(blank=True, null=True)
    
    # Bot Settings
    response_delay = models.PositiveIntegerField(default=2)
    typing_duration = models.PositiveIntegerField(default=3)
    max_retries = models.PositiveIntegerField(default=3)
    enable_analytics = models.BooleanField(default=True)
    collect_feedback = models.BooleanField(default=True)
    available_languages = models.JSONField(default=list)
    
    # Topics
    allowed_topics = models.JSONField(default=list)
    restricted_topics = models.JSONField(default=list)
    
    # Admin Settings
    admin_id = models.CharField(max_length=50, blank=True, null=True)
    notifications_enabled = models.BooleanField(default=True)
    notification_hours = models.JSONField(default=list)
    email_notifications = models.BooleanField(default=True)
    admin_email = models.EmailField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('company')
        verbose_name_plural = _('companies')

    def __str__(self):
        return self.name

class Client(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('client')
        verbose_name_plural = _('clients')
        unique_together = ['company', 'email']

    def __str__(self):
        return f"{self.name} ({self.email})"
