class RequestMiddleware:
    """Middleware to make the request object available to the UserManager."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the request object in the UserManager
        from .models import UserManager
        UserManager._request = request
        
        response = self.get_response(request)
        return response
