from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from decouple import config

class Command(BaseCommand):
    help = 'Setup Google OAuth application'

    def handle(self, *args, **options):
        # Get or create site
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': 'localhost:8000',
                'name': 'MsituGuard Local'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created site: {site.name}')
            )
        
        # Get Google OAuth credentials from environment
        client_id = config('GOOGLE_OAUTH2_CLIENT_ID', default=None)
        client_secret = config('GOOGLE_OAUTH2_CLIENT_SECRET', default=None)
        
        if not client_id or not client_secret:
            self.stdout.write(
                self.style.ERROR(
                    'Google OAuth credentials not found in environment variables.\n'
                    'Please set GOOGLE_OAUTH2_CLIENT_ID and GOOGLE_OAUTH2_CLIENT_SECRET'
                )
            )
            return
        
        # Create or update Google OAuth app
        google_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google OAuth2',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        
        if not created:
            google_app.client_id = client_id
            google_app.secret = client_secret
            google_app.save()
            self.stdout.write(
                self.style.SUCCESS('Updated Google OAuth app')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Created Google OAuth app')
            )
        
        # Add site to the app
        google_app.sites.add(site)
        
        self.stdout.write(
            self.style.SUCCESS(
                'Google OAuth setup complete!\n'
                f'Client ID: {client_id[:10]}...\n'
                f'Site: {site.domain}'
            )
        )