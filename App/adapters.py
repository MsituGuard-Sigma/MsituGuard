from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
import logging

logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Link Google OAuth to existing user by email"""
        if sociallogin.account.provider == 'google':
            email = sociallogin.account.extra_data.get('email')
            if email:
                try:
                    #Find existing user with this email
                    existing_user = User.objects.get(email=email)
                    #Connect the social account to existing user
                    sociallogin.connect(request, existing_user)
                    logger.info(f"Connected Google account to existing user: {existing_user.username}")
                except User.DoesNotExist:
                    #Mark as new user for welcome message
                    request.session['is_new_oauth_user'] = True
                except User.MultipleObjectsReturned:
                    #Multiple users with same email - use the first one
                    existing_user = User.objects.filter(email=email).first()
                    if existing_user:
                        sociallogin.connect(request, existing_user)
                        logger.warning(f"Multiple users found with email {email}, connected to {existing_user.username}")
                    else:
                        request.session['is_new_oauth_user'] = True
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        try:
            #Only create profile if user doesn't have one
            if not hasattr(user, 'profile'):
                Profile.objects.create(
                    user=user,
                    account_type='community',
                    phoneNumber='',
                    location='',
                    bio='Bio information not provided',
                    email=user.email or 'example@example.com',
                    first_name=user.first_name or '',
                    last_name=user.last_name or '',
                    is_verified=False
                )
                logger.info(f"Created profile for new user {user.username}")
        except Exception as e:
            logger.error(f"Error creating profile for user {user.username}: {e}")
        
        return user
    
    def get_login_redirect_url(self, request):
        """Redirect new users to welcome page, existing users to home"""
        if request.session.get('is_new_oauth_user'):
            # Clear the flag and redirect to welcome
            del request.session['is_new_oauth_user']
            return '/welcome/'
        return '/'  # Home for existing users
    
    def add_message(self, request, level, message_tag, message, extra_tags=''):
        """Suppress login success messages for professional UX"""
        # Don't show 'Successfully signed in as...' messages
        if 'signed in as' in message.lower():
            return
        super().add_message(request, level, message_tag, message, extra_tags)

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit)
        
        if commit:
            try:
                profile, created = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'account_type': 'community',
                        'phoneNumber': '',
                        'location': '',
                        'bio': 'Bio information not provided',
                        'email': user.email or 'example@example.com',
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'is_verified': False
                    }
                )
                if created:
                    logger.info(f"Created profile for user {user.username}")
            except Exception as e:
                logger.error(f"Error creating profile for user {user.username}: {e}")
        
        return user