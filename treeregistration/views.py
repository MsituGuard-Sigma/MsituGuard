from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.contrib import messages

from django.contrib.auth.models import User
from .models import Tree, UserProfile
from .forms import TreeUploadForm, UserRegisterForm, UserLoginForm


# ===============================
# LANDING PAGE
# ===============================

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('tree_home')
    return render(request, 'treeregistration/landing.html')


# ===============================
# AUTHENTICATION VIEWS
# ===============================

class UserLoginView(LoginView):
    template_name = "treeregistration/login.html"
    success_url = "/tree-registration/dashboard/"


class UserLogoutView(LogoutView):
    next_page = "/"


def register_view(request):
    user_type = request.GET.get('type', 'individual')
    
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()
            
            # Create UserProfile with user_type
            profile_user_type = request.POST.get('user_type', 'individual')
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'user_type': profile_user_type}
            )
            
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("tree_home")
        else:
            print("Form errors:", form.errors)  # Debug print
    else:
        form = UserRegisterForm()

    return render(request, "treeregistration/register.html", {
        "form": form,
        "user_type": user_type
    })


# ===============================
# USER DASHBOARD / PROFILE
# ===============================

@login_required
def home(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    context = {
        "tree_count": profile.tree_count,
        "badge": profile.badge
    }
    return render(request, "treeregistration/home.html", context)




# ===============================
# ADMIN VIEWS
# ===============================

@staff_member_required
def admin_dashboard(request):
    # Get statistics
    total_users = User.objects.count()
    total_trees = Tree.objects.count()
    
    # Individual users stats
    individual_users = User.objects.filter(user_type='individual')
    individual_count = individual_users.count()
    individual_trees = Tree.objects.filter(user__user_type='individual').count()
    
    # Organization users stats
    org_users = User.objects.filter(user_type='organisation')
    org_count = org_users.count()
    org_trees = Tree.objects.filter(user__user_type='organisation').count()
    
    # Recent trees
    recent_trees = Tree.objects.select_related('user').order_by('-uploaded_at')[:10]
    
    # Top users
    top_users = User.objects.order_by('-tree_count')[:10]
    
    context = {
        'total_users': total_users,
        'total_trees': total_trees,
        'individual_count': individual_count,
        'individual_trees': individual_trees,
        'org_count': org_count,
        'org_trees': org_trees,
        'recent_trees': recent_trees,
        'top_users': top_users,
    }
    return render(request, 'treeregistration/admin_dashboard.html', context)


@staff_member_required
def admin_users(request):
    user_type = request.GET.get('type', 'all')
    
    if user_type == 'individual':
        users = User.objects.filter(user_type='individual').order_by('-tree_count')
    elif user_type == 'organisation':
        users = User.objects.filter(user_type='organisation').order_by('-tree_count')
    else:
        users = User.objects.all().order_by('-tree_count')
    
    context = {
        'users': users,
        'current_type': user_type,
    }
    return render(request, 'treeregistration/admin_users.html', context)


@staff_member_required
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            if not user.is_staff:  # Prevent deleting admin users
                username = user.username
                user.delete()
                messages.success(request, f'User {username} has been deleted successfully.')
            else:
                messages.error(request, 'Cannot delete admin users.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    return redirect('admin_users')


# ===============================
# TREE UPLOAD VIEW
# ===============================



@login_required
def upload_tree(request):
    if request.method == "POST":
        form = TreeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            tree = form.save(commit=False)
            tree.user = request.user
            tree.save()
            return redirect("profile_detail")
    else:
        form = TreeUploadForm()

    return render(request, "treeregistration/upload.html", {"form": form})
