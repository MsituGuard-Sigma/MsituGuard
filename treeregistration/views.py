from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
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


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('home')


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
            return redirect("tree_upload")
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
    individual_users = User.objects.filter(treeregistration_profile__user_type='individual')
    individual_count = individual_users.count()
    individual_trees = Tree.objects.filter(user__treeregistration_profile__user_type='individual').count()
    
    # Organization users stats
    org_users = User.objects.filter(treeregistration_profile__user_type='organisation')
    org_count = org_users.count()
    org_trees = Tree.objects.filter(user__treeregistration_profile__user_type='organisation').count()
    
    # Recent trees
    recent_trees = Tree.objects.select_related('user').order_by('-uploaded_at')[:10]
    
    # Top users
    top_users = User.objects.filter(treeregistration_profile__isnull=False).order_by('-treeregistration_profile__tree_count')[:10]
    
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
        users = User.objects.filter(treeregistration_profile__user_type='individual').order_by('-treeregistration_profile__tree_count')
    elif user_type == 'organisation':
        users = User.objects.filter(treeregistration_profile__user_type='organisation').order_by('-treeregistration_profile__tree_count')
    else:
        users = User.objects.filter(treeregistration_profile__isnull=False).order_by('-treeregistration_profile__tree_count')
    
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
            # Generate hash for uploaded photo to check for duplicates
            from .models import generate_photo_hash
            photo_hash = generate_photo_hash(request.FILES['photo'])
            
            # Check if this photo has already been uploaded
            if Tree.objects.filter(photo_hash=photo_hash).exists():
                form.add_error('photo', 'This tree photo has already been uploaded!')
                return render(request, "treeregistration/upload.html", {"form": form})
            
            tree = form.save(commit=False)
            tree.user = request.user
            tree.photo_hash = photo_hash  # Set hash to avoid regenerating
            
            # Get location data if provided
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            location_name = request.POST.get('location_name')
            
            if latitude and longitude:
                tree.latitude = float(latitude)
                tree.longitude = float(longitude)
                
                # Use location service to detect county and region
                try:
                    from Tree_Prediction.integration.location_service import get_accurate_location
                    location_data = get_accurate_location(float(latitude), float(longitude))
                    if location_data.get('success', False):
                        tree.detected_county = location_data.get('county', '')
                        if not location_name:
                            tree.location_name = location_data.get('county', 'Unknown Location')
                    else:
                        tree.detected_county = ''
                        tree.location_name = location_name or 'Unknown Location'
                except Exception as e:
                    print(f"Location detection error: {e}")
                    tree.detected_county = ''
                    tree.location_name = location_name or 'Unknown Location'
            else:
                tree.location_name = location_name or 'Unknown Location'
                tree.detected_county = ''
            
            tree.save()
            return redirect("profile_detail")
    else:
        form = TreeUploadForm()

    return render(request, "treeregistration/upload.html", {"form": form})
