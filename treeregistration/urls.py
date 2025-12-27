from django.urls import path
from .views import (
    UserLoginView,
    UserLogoutView,
    register_view,
    home,
    upload_tree,
    landing_page,
    admin_dashboard,
    admin_users,
    admin_delete_user,
)

urlpatterns = [
    # Landing page
    path('', landing_page, name='tree_landing'),
    
    # Authentication - Tree Registration Auth
    path('auth/register/', register_view, name='tree_register'),
    path('auth/login/', UserLoginView.as_view(), name='tree_login'),
    path('auth/logout/', UserLogoutView.as_view(), name='tree_logout'),
    
    # Home + user routes (requires login)
    path('dashboard/', home, name='tree_home'),
    path('upload/', upload_tree, name='tree_upload'),
    
    # Admin routes
    path('admin-dashboard/', admin_dashboard, name='tree_admin_dashboard'),
    path('admin-users/', admin_users, name='tree_admin_users'),
    path('admin-delete-user/<int:user_id>/', admin_delete_user, name='tree_admin_delete_user'),
]
