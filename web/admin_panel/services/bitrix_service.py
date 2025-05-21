import requests
from django.conf import settings
from ..models import Integration
from users.models import Client

class BitrixService:
    def __init__(self, company_id):
        self.company_id = company_id
        self.integration = self._get_integration()
        self.base_url = self.integration.config.get('webhook_url')
        
    def _get_integration(self):
        try:
            return Integration.objects.get(company_id=self.company_id, service='bitrix')
        except Integration.DoesNotExist:
            raise Exception('Bitrix integration not found for this company')
    
    def _make_request(self, method, params=None):
        url = f"{self.base_url}/{method}"
        response = requests.get(url, params=params or {})
        response.raise_for_status()
        return response.json()
    
    def get_users(self):
        """Fetch all users from Bitrix24"""
        result = self._make_request('user.get', {
            'filter[ACTIVE]': True
        })
        return result.get('result', [])
    
    def sync_users_to_local(self):
        """Synchronize Bitrix24 users to local Client model"""
        bitrix_users = self.get_users()
        local_clients = []
        
        for bitrix_user in bitrix_users:
            client, created = Client.objects.update_or_create(
                telegram_id=bitrix_user.get('ID'),
                company_id=self.company_id,
                defaults={
                    'name': bitrix_user.get('NAME'),
                    'email': bitrix_user.get('EMAIL'),
                    'is_permanent_client': True,
                    'settings': {
                        'bitrix_id': bitrix_user.get('ID'),
                        'phone': bitrix_user.get('PERSONAL_PHONE'),
                        'position': bitrix_user.get('WORK_POSITION'),
                    }
                }
            )
            local_clients.append(client)
            
        return local_clients
