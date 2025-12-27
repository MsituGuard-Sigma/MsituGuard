from django import forms
from .models import Tree

class TreeUploadForm(forms.ModelForm):
    class Meta:
        model = Tree
        fields = ['photo']


from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

# Registration form
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

# Login form
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput)
