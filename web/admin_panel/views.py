from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.models import Company, Client
from .decorators import admin_required
from .models import FAQ, Policy, Integration
from .forms import FAQForm, PolicyForm
from .services.bitrix_service import BitrixService
from .services.amocrm_service import AmoCRMService
import json

@login_required
def dashboard(request):
    """Admin dashboard view"""
    return render(request, 'admin_panel/dashboard.html')

@login_required
def bot_settings(request):
    """Bot settings view"""
    return render(request, 'admin_panel/bot_settings.html')

@login_required
@admin_required
def select_service(request):
    """Service selection view"""
    company = Company.objects.filter(admin=request.user).first()
    if not company:
        messages.error(request, 'Please create a company profile first')
        return redirect('users:company_profile')
    request.session['company_id'] = company.id
    return render(request, 'admin_panel/select_service.html')

@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def input_connection_data(request):
    if request.method == 'POST':
        service = request.POST.get('service')
        company_id = request.session.get('company_id')
        
        if not company_id:
            messages.error(request, 'Company not selected')
            return redirect('select_service')
            
        if service == 'bitrix':
            # Save Bitrix integration data
            try:
                webhook_url = request.POST.get('webhook_url')
                if not webhook_url:
                    messages.error(request, 'Webhook URL is required')
                    return render(request, 'admin_panel/input_connection_data_bitrix.html')
                    
                # Save or update integration
                Integration.objects.update_or_create(
                    company_id=company_id,
                    service='bitrix',
                    defaults={
                        'config': {
                            'webhook_url': webhook_url,
                            'api_key': request.POST.get('api_key', ''),
                            'api_secret': request.POST.get('api_secret', '')
                        }
                    }
                )
                return redirect('data_transfer_options')
                
            except Exception as e:
                messages.error(request, f'Error saving integration: {str(e)}')
                return render(request, 'admin_panel/input_connection_data_bitrix.html')
                
        elif service == 'amocrm':
            # Handle AmoCRM connection
            try:
                base_url = request.POST.get('base_url')
                client_id = request.POST.get('client_id')
                client_secret = request.POST.get('client_secret')
                auth_code = request.POST.get('auth_code')
                
                if not all([base_url, client_id, client_secret, auth_code]):
                    messages.error(request, 'All fields are required')
                    return render(request, 'admin_panel/input_connection_data_amocrm.html')
                
                # In a real implementation, you would exchange the auth code for tokens here
                # This is a simplified example
                access_token = f"{client_id}:{client_secret}:{auth_code}"  # Simplified
                
                # Save or update integration
                Integration.objects.update_or_create(
                    company_id=company_id,
                    service='amocrm',
                    defaults={
                        'config': {
                            'base_url': base_url,
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'access_token': access_token
                        }
                    }
                )
                return redirect('data_transfer_options', service='amocrm')
                
            except Exception as e:
                messages.error(request, f'Error saving AmoCRM integration: {str(e)}')
                return render(request, 'admin_panel/input_connection_data_amocrm.html')
            
    # GET request - show the appropriate form
    service = request.GET.get('service')
    if service == 'bitrix':
        return render(request, 'admin_panel/input_connection_data_bitrix.html')
    elif service == 'amocrm':
        return render(request, 'admin_panel/input_connection_data_amocrm.html')
        
    return redirect('select_service')


@login_required
@admin_required
def add_policy(request, company_id):
    """View for adding a new policy."""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = PolicyForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.company = company
            policy.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PolicyForm()
        
    return render(request, 'admin_panel/policy_form.html', {
        'form': form,
        'company': company
    })

@login_required
@admin_required
def edit_policy(request, company_id, policy_id):
    """View for editing an existing policy."""
    company = get_object_or_404(Company, id=company_id)
    policy = get_object_or_404(Policy, id=policy_id, company=company)
    
    if request.method == 'POST':
        form = PolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PolicyForm(instance=policy)
        
    return render(request, 'admin_panel/policy_form.html', {
        'form': form,
        'company': company,
        'policy': policy
    })

@login_required
@admin_required
def delete_policy(request, company_id, policy_id):
    """View for deleting a policy."""
    company = get_object_or_404(Company, id=company_id)
    policy = get_object_or_404(Policy, id=policy_id, company=company)
    
    if request.method == 'POST':
        policy.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
@admin_required
def company_profile(request):
    """View for company profile and bot settings."""
    company = request.user.company
    
    if request.method == 'POST':
        form = BotSettingsForm(request.POST, instance=company)
        if form.is_valid():
            company = form.save(commit=False)
            company.save()
            messages.success(request, 'Bot settings updated successfully')
            return redirect('admin_panel:company_profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = BotSettingsForm(instance=company)
    
    # Get FAQs for the company
    faqs = FAQ.objects.filter(company=company)
    
    context = {
        'form': form,
        'company': company,
        'faqs': faqs
    }

    return render(request, 'admin_panel/company_profile.html', context)

@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def data_transfer_options(request, service=None):
    
    company_id = request.session.get('company_id')
    if not company_id:
        messages.error(request, 'Company not selected')
        return redirect('select_service')
    
    if request.method == 'POST':
        transfer_choice = request.POST.get('transfer_choice')
        platforms = request.POST.getlist('platforms', [])
        
        try:
            if transfer_choice == 'transfer':
                if service == 'bitrix':
                    bitrix = BitrixService(company_id)
                    synced_users = bitrix.sync_users_to_local()
                    messages.success(request, f'Successfully synced {len(synced_users)} users from Bitrix24')
                elif service == 'amocrm':
                    amocrm = AmoCRMService(company_id)
                    synced_users = amocrm.sync_users_to_local()
                    messages.success(request, f'Successfully synced {len(synced_users)} users from AmoCRM')
                else:
                    messages.error(request, 'Unsupported service')
                    return redirect('select_service')
                
                # Process platforms if needed
                for platform in platforms:
                    # Add platform-specific processing here
                    pass
                    
            else:
                messages.info(request, f'Connected to {service} without data transfer')
                
            return redirect('select_service')
                
        except Exception as e:
            messages.error(request, f'Error during synchronization: {str(e)}')
    
    # GET request - show the form
    return render(request, 'admin_panel/data_transfer_options.html', {'service': service})

@login_required
@admin_required
@require_http_methods(["POST"])
@csrf_exempt
def sync_users(request):
    """
    AJAX endpoint for user synchronization
    Supports both Bitrix24 and AmoCRM
    """
    try:
        data = json.loads(request.body)
        company_id = request.session.get('company_id')
        service = data.get('service')
        transfer_choice = data.get('transfer_choice')
        platforms = data.get('platforms', [])
        
        if not all([company_id, service, transfer_choice is not None]):
            return JsonResponse(
                {'error': 'Missing required parameters'}, 
                status=400
            )
        
        if transfer_choice == 'transfer':
            try:
                if service == 'bitrix':
                    bitrix = BitrixService(company_id)
                    synced_users = bitrix.sync_users_to_local()
                    service_name = 'Bitrix24'
                elif service == 'amocrm':
                    amocrm = AmoCRMService(company_id)
                    synced_users = amocrm.sync_users_to_local()
                    service_name = 'AmoCRM'
                else:
                    return JsonResponse(
                        {'error': 'Unsupported service'}, 
                        status=400
                    )
                
                # Process platforms if needed
                platform_messages = []
                for platform in platforms:
                    # Add platform-specific processing here
                    platform_messages.append(f"{len(synced_users)} users synchronized with {platform}")
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully synchronized {len(synced_users)} users from {service_name}',
                    'platform_messages': platform_messages
                })
                
            except Exception as e:
                return JsonResponse(
                    {'error': f'Error during {service} synchronization: {str(e)}'}, 
                    status=500
                )
        else:
            # Just connect without data transfer
            return JsonResponse({
                'success': True,
                'message': f'Connected to {service} without data transfer',
                'platform_messages': [f'Connected to {platform} without data transfer' for platform in platforms]
            })
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON data'}, 
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Unexpected error: {str(e)}'}, 
            status=500
        )
