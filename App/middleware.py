from django.contrib import messages

class SuppressOAuthMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Remove OAuth success messages after processing
        if hasattr(request, '_messages'):
            storage = messages.get_messages(request)
            filtered_messages = []
            for message in storage:
                # Filter out OAuth success messages
                if not ('signed in as' in str(message).lower() or 
                       'successfully signed in' in str(message).lower()):
                    filtered_messages.append(message)
            
            # Clear all messages and re-add only non-OAuth ones
            storage.used = False
            storage._queued_messages = filtered_messages
        
        return response