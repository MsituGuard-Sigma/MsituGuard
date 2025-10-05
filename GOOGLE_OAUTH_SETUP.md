# Google OAuth Setup for MsituGuard

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install django-allauth==0.57.0
```

### 2. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set Application type to "Web application"
6. Add Authorized redirect URIs:
   - `http://localhost:8000/accounts/google/login/callback/`
   - `https://yourdomain.com/accounts/google/login/callback/` (for production)

### 3. Set Environment Variables

Create a `.env` file or set environment variables:
```bash
GOOGLE_OAUTH2_CLIENT_ID=your_client_id_here
GOOGLE_OAUTH2_CLIENT_SECRET=your_client_secret_here
```

### 4. Run Setup
```bash
python setup_google_oauth.py
```

Or manually:
```bash
python manage.py migrate
python manage.py setup_google_oauth
```

### 5. Start Server
```bash
python manage.py runserver
```

## ✅ Features Implemented

- ✅ Google OAuth2 login/signup
- ✅ Automatic user profile creation
- ✅ Email-based authentication
- ✅ Social account integration
- ✅ Custom adapters for user handling
- ✅ Updated login/register templates

## 🔧 Configuration Details

### Settings Added:
- `django-allauth` apps
- Social account providers
- Custom adapters
- Authentication backends

### URLs Added:
- `/accounts/google/login/` - Google OAuth login
- `/accounts/google/login/callback/` - OAuth callback

### Templates Updated:
- `login.html` - Added Google login button
- `register.html` - Added Google signup button

## 🎯 How It Works

1. User clicks "Continue with Google"
2. Redirected to Google OAuth consent screen
3. After approval, redirected back to your app
4. User account created automatically with profile
5. User logged in and redirected to home page

## 🛠️ Troubleshooting

### Common Issues:

1. **"redirect_uri_mismatch"**
   - Check your Google Console redirect URIs match exactly
   - Include both http://localhost:8000 and your production domain

2. **"Client ID not found"**
   - Verify environment variables are set correctly
   - Run `python manage.py setup_google_oauth` again

3. **"Site matching query does not exist"**
   - Run migrations: `python manage.py migrate`
   - The setup script creates the site automatically

### Debug Mode:
Set `DEBUG=True` in settings to see detailed error messages.

## 🌐 Production Deployment

1. Update `ALLOWED_HOSTS` in settings
2. Set production domain in Google Console
3. Update environment variables on your hosting platform
4. Run migrations on production server
5. Run setup command on production

## 📝 Notes

- Users can still register/login with email/password
- Google OAuth creates users with email as username
- Profile is automatically created for OAuth users
- No email verification required for OAuth users