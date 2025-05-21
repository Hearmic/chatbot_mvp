from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Manager

class FAQ(models.Model):
    """Frequently Asked Questions for a company."""
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, related_name='faqs')
    category = models.CharField(max_length=50, choices=[
        ('general', 'General'),
        ('cancellation', 'Cancellation'),
        ('privacy', 'Privacy'),
        ('refund', 'Refund'),
        ('late_arrival', 'Late Arrival'),
        ('no_show', 'No Show'),
        ('custom', 'Custom')
    ], default='general')
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
        ordering = ['category', '-created_at']

    def __str__(self):
        return f"{self.company.name}: {self.category} - {self.question[:50]}..."

class Policy(models.Model):
    """Company policies that can be customized."""
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, related_name='policies')
    category = models.CharField(max_length=50, choices=[
        ('cancellation', 'Cancellation Policy'),
        ('privacy', 'Privacy Policy'),
        ('refund', 'Refund Policy'),
        ('late_arrival', 'Late Arrival Policy'),
        ('no_show', 'No Show Policy'),
        ('custom', 'Custom Policy')
    ])
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Policy'
        verbose_name_plural = 'Policies'
        ordering = ['category', 'title']
        unique_together = ['company', 'category', 'title']

    def __str__(self):
        return f"{self.company.name}: {self.get_category_display()} - {self.title}"

# Company and CompanyAdmin models have been moved to users/models.py

class Message(models.Model):
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey('users.Client', on_delete=models.CASCADE, related_name='messages')
    response_time = models.DurationField(null=True, blank=True)
    is_bot_response = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'admin_panel'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Message from {self.user.username} at {self.timestamp}"

    def calculate_response_time(self, previous_message):
        """Calculate response time based on the previous message."""
        if previous_message and previous_message.user != self.user:
            self.response_time = self.timestamp - previous_message.timestamp
            self.save()

    @classmethod
    def create_with_response_time(cls, content, company, user, is_bot_response=False):
        """Create a new message and calculate response time."""
        previous_message = cls.objects.filter(
            company=company,
            user=user
        ).order_by('-timestamp').first()
        
        message = cls.objects.create(
            content=content,
            company=company,
            user=user,
            is_bot_response=is_bot_response
        )
        
        message.calculate_response_time(previous_message)
        return message

class Analytics(models.Model):
    """Model to store daily analytics for each company."""
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    
    # User metrics
    total_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    
    # Message metrics
    total_messages = models.IntegerField(default=0)
    bot_messages = models.IntegerField(default=0)
    user_messages = models.IntegerField(default=0)
    
    # Response time metrics
    average_response_time = models.DurationField(null=True, blank=True)
    max_response_time = models.DurationField(null=True, blank=True)
    min_response_time = models.DurationField(null=True, blank=True)
    
    # Engagement metrics
    engagement_rate = models.FloatField(default=0.0)
    response_rate = models.FloatField(default=0.0)
    
    class Meta:
        app_label = 'admin_panel'
        unique_together = ['company', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"Analytics for {self.company.name} on {self.date}"

    @classmethod
    def update_daily_analytics(cls, company):
        """Update analytics for today."""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get or create today's analytics
        analytics, created = cls.objects.get_or_create(
            company=company,
            date=today
        )
        
        # Calculate metrics
        analytics.total_users = Client.objects.filter(company=company).count()
        analytics.active_users = Client.objects.filter(
            company=company,
            messages__timestamp__gte=today
        ).distinct().count()
        
        # Calculate new users
        analytics.new_users = Client.objects.filter(
            company=company,
            date_joined__gte=yesterday
        ).count()
        
        # Calculate message metrics
        messages = Message.objects.filter(
            company=company,
            timestamp__date=today
        )
        
        analytics.total_messages = messages.count()
        analytics.bot_messages = messages.filter(is_bot_response=True).count()
        analytics.user_messages = messages.filter(is_bot_response=False).count()
        
        # Calculate response time metrics
        response_times = [msg.response_time for msg in messages if msg.response_time]
        if response_times:
            analytics.average_response_time = sum(response_times, timedelta()) / len(response_times)
            analytics.max_response_time = max(response_times)
            analytics.min_response_time = min(response_times)
        
        # Calculate engagement metrics
        if analytics.total_users > 0:
            analytics.engagement_rate = analytics.total_messages / analytics.total_users
            analytics.response_rate = analytics.bot_messages / analytics.user_messages if analytics.user_messages > 0 else 0
        
        analytics.save()
        return analytics

class Integration(models.Model):
    company = models.ForeignKey('users.Company', on_delete=models.CASCADE, related_name='integrations')
    service = models.CharField(max_length=255)
    config = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'admin_panel'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service} integration for {self.company.name}"