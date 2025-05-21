from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.contrib.messages import get_messages

from django.contrib.auth import get_user_model
from users.models import Company
from users.forms import UserCreationForm, UserUpdateForm

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='testpass123'
        )
        self.company_admin = User.objects.create_user(
            email='admin@company.com',
            password='testpass123',
            company=self.company
        )
        self.regular_user = User.objects.create_user(
            email='user@company.com',
            password='testpass123',
            company=self.company
        )
        self.factory = RequestFactory()
        self.client = Client()

    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            email='newuser@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123'
        )
        self.assertEqual(admin.email, 'super@example.com')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)

    def test_user_manager_queryset_superuser(self):
        """Test that superusers see all users"""
        request = self.factory.get('/')
        request.user = self.superuser
        
        # Set the request on the manager
        User.objects._request = request
        
        users = User.objects.all()
        self.assertEqual(users.count(), 3)  # superuser, company_admin, regular_user

    def test_user_manager_queryset_company_admin(self):
        """Test that company admins see only their company's users"""
        # Create another company and user
        company2 = Company.objects.create(name="Another Company")
        user2 = User.objects.create_user(
            email='user2@another.com',
            password='testpass123',
            company=company2
        )
        
        request = self.factory.get('/')
        request.user = self.company_admin
        User.objects._request = request
        
        users = User.objects.all()
        self.assertEqual(users.count(), 2)  # company_admin and regular_user from same company
        self.assertNotIn(user2, users)

class UserFormTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='testpass123'
        )
        self.company_admin = User.objects.create_user(
            email='admin@company.com',
            password='testpass123',
            company=self.company
        )
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_user_creation_form_superuser(self):
        """Test user creation form for superuser"""
        self.request.user = self.superuser
        form_data = {
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'is_superuser': True
        }
        form = UserCreationForm(data=form_data, request=self.request)
        self.assertTrue(form.is_valid())

    def test_user_creation_form_company_admin(self):
        """Test user creation form for company admin"""
        self.request.user = self.company_admin
        form_data = {
            'email': 'new@company.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        }
        form = UserCreationForm(data=form_data, request=self.request)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.company, self.company)
        self.assertFalse(user.is_superuser)

    def test_user_creation_form_company_admin_superuser_attempt(self):
        """Test that company admins can't create superusers"""
        self.request.user = self.company_admin
        form_data = {
            'email': 'new@company.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'is_superuser': True
        }
        form = UserCreationForm(data=form_data, request=self.request)
        self.assertTrue(form.is_valid())  # Form is valid but is_superuser is ignored
        user = form.save()
        self.assertFalse(user.is_superuser)  # Should not be a superuser

class UserViewTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='testpass123'
        )
        self.company_admin = User.objects.create_user(
            email='admin@company.com',
            password='testpass123',
            company=self.company
        )
        self.regular_user = User.objects.create_user(
            email='user@company.com',
            password='testpass123',
            company=self.company
        )
        self.client = Client()

    def test_user_list_view_superuser(self):
        """Test user list view for superuser"""
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'admin@company.com')
        self.assertContains(response, 'user@company.com')

    def test_user_list_view_company_admin(self):
        """Test user list view for company admin"""
        self.client.login(email='admin@company.com', password='testpass123')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Members')
        self.assertContains(response, 'admin@company.com')
        self.assertContains(response, 'user@company.com')
        self.assertNotContains(response, 'admin@example.com')

    def test_user_create_view_company_admin(self):
        """Test user creation by company admin"""
        self.client.login(email='admin@company.com', password='testpass123')
        
        # Test GET request
        response = self.client.get(reverse('users:user_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_form.html')
        
        # Test POST request
        response = self.client.post(reverse('users:user_create'), {
            'email': 'newuser@company.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'New',
            'last_name': 'User'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to user list
        self.assertTrue(User.objects.filter(email='newuser@company.com').exists())
        
        # Verify the user was created with the correct company
        user = User.objects.get(email='newuser@company.com')
        self.assertEqual(user.company, self.company)
        new_user = User.objects.get(email='newuser@company.com')
        self.assertEqual(new_user.company, self.company)
        self.assertFalse(new_user.is_superuser)

    def test_regular_user_access_denied(self):
        """Test that regular users can't access admin views"""
        self.client.login(email='user@company.com', password='testpass123')
        
        # Test user list - should redirect to profile
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 302)  # Should redirect to profile
        
        # Test user create - should be denied
        response = self.client.get(reverse('users:user_create'))
        self.assertIn(response.status_code, [302, 403])  # Either redirect or forbidden is acceptable

    def test_company_admin_cant_create_superuser(self):
        """Test that company admins can't create superusers"""
        self.client.login(email='admin@company.com', password='testpass123')
        
        response = self.client.post(reverse('users:user_create'), {
            'email': 'newadmin@company.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'New',
            'last_name': 'Admin',
            'is_superuser': True  # This should be ignored
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to user list on success
        
        # The user should be created but not as a superuser
        user = User.objects.get(email='newadmin@company.com')
        self.assertFalse(user.is_superuser)
