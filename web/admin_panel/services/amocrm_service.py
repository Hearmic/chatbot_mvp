import requests
from django.conf import settings
from ..models import Integration
from users.models import Client

class AmoCRMService:
    def __init__(self, company_id):
        self.company_id = company_id
        self.integration = self._get_integration()
        self.base_url = self.integration.config.get('base_url')
        self.access_token = self.integration.config.get('access_token')
        
    def _get_integration(self):
        try:
            return Integration.objects.get(company_id=self.company_id, service='amocrm')
        except Integration.DoesNotExist:
            raise Exception('AmoCRM integration not found for this company')
    
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}/api/v4{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_users(self):
        """Fetch all users from AmoCRM"""
        result = self._make_request('GET', '/users')
        return result.get('_embedded', {}).get('users', [])
    
    def sync_users_to_local(self):
        """Synchronize AmoCRM users to local Client model"""
        amocrm_users = self.get_users()
        local_clients = []
        
        for user_data in amocrm_users:
            email = user_data.get('email')
            if not email:
                continue
                
            client, created = Client.objects.update_or_create(
                email=email,
                company_id=self.company_id,
                defaults={
                    'name': user_data.get('name', '').strip() or email.split('@')[0],
                    'is_permanent_client': True,
                    'settings': {
                        'amocrm_id': user_data.get('id'),
                        'phone': user_data.get('phone'),
                        'position': user_data.get('position'),
                        'language': user_data.get('language')
                    }
                }
            )
            local_clients.append(client)
            
        return local_clients
