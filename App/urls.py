
from django.urls import path, include
from django.shortcuts import redirect
from . import views
from .views import ussd_callback
from .views_ml import predict_tree_survival, get_species_recommendations, get_climate_data

from django.contrib.auth import views as auth_views
from .views import UseRegisterView #CustomLoginView
from .views import CustomPasswordResetView
from .views import request_verification  
# from .forms import CustomLoginForm
from django.contrib.auth.views import LoginView

# from .forms import LoginFormWithCaptcha


from .views import(HomeView,   UserLogoutView, ResourceListView, ResourceCreateView,
                   ResourceUpdateView, ResourceDeleteView, ProfileDetailView, 
                   ResourceDetailView, AlertListView, AlertCreateView, AlertDetailView,
                   LatestAlertsView, ResourceRequestCreateView, ResourceRequestListView,
                   ForumPostListView, ForumPostCreateView, ForumPostDetailView,  AddCommentView, UserEditView, ApprovedAlertListView,
                   ApprovedContributeListView, TemplateView, OrganizationDashboardView, update_report_status,
                   TreeInitiativeView, TreePlantingFormView, TreePlantingsListView, MyReportsView, RewardsView, redeem_reward)
#,UserRegisterView
                   
urlpatterns = [
    path('', HomeView.as_view(), name='home'),  
    # path('', include('django.contrib.auth.urls')), 
    path('register/', UseRegisterView.as_view(), name='register'),
    path('register/organization/', UseRegisterView.as_view(), {'organization_only': True}, name='organization_register'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('resources/', ResourceListView.as_view(), name='resource_list'),
    path('resources/new/', ResourceCreateView.as_view(), name='resource_create'),
    path('resource/edit/<int:pk>/', ResourceUpdateView.as_view(), name='resource_update'),
    path('resource/delete/<int:pk>/', ResourceDeleteView.as_view(), name='resource_delete'),
    path('resources/<int:pk>/', ResourceDetailView.as_view(), name='resource_detail'),

    path('profile/', ProfileDetailView.as_view(), name='profile_detail'),
    path('request-verification/', request_verification, name='request_verification'),
    # path('profile/remove_picture/', remove_profile_picture, name='remove_profile_picture'),
    path('reports/', AlertListView.as_view(), name='alert_list'),
    path('reports/new/', AlertCreateView.as_view(), name='alert_create'),  # Use alert_create
    path('my-reports/', MyReportsView.as_view(), name='my_reports'),


    path('environmental-reports/', LatestAlertsView.as_view(), name='latest_alerts'),
    path('reports/<int:pk>/', AlertDetailView.as_view(), name='alert_detail'),
    path('approved-alerts/', ApprovedAlertListView.as_view(), name='approved_alerts'),
    path('approved-contributes/', ApprovedContributeListView.as_view(), name='approved_contributes'),
    path('organization-dashboard/', OrganizationDashboardView.as_view(), name='organization_dashboard'),
    path('update-report-status/<int:report_id>/', update_report_status, name='update_report_status'),
    path('update-tree-status/<int:tree_id>/', views.update_tree_status, name='update_tree_status'),
    
    # Tree Planting Initiative URLs
    path('tree-initiative/', TreeInitiativeView.as_view(), name='tree_initiative'),
    path('plant-trees/', TreePlantingFormView.as_view(), name='tree_planting_form'),
    path('tree-plantings/', TreePlantingsListView.as_view(), name='tree_plantings_list'),
    path('plant-trees-public/', views.PublicTreeFormView.as_view(), name='public_tree_form'),
    path('public-tree-planting/', views.public_tree_planting, name='public_tree_planting'),
    path('verify-tree-account/<uidb64>/<token>/', views.verify_tree_planting_account, name='verify_tree_planting_account'),
    path('request-resource/', ResourceRequestCreateView.as_view(), name='request_resource'),
    path('resource-requests/', ResourceRequestListView.as_view(), name='resource_requests'),
    path('request/success/', TemplateView.as_view(template_name='App/request_success.html'), name='request_success'),
    # path('resources/', ApprovedResourceListView.as_view(), name='resources-list'),
    path('forums/', ForumPostListView.as_view(), name='forum_post_list'),
    path('forums/create/', ForumPostCreateView.as_view(), name='forum_post_create'),
    path('forums/<int:pk>/', ForumPostDetailView.as_view(), name='forum_post_detail'),
    # path('comment/create/<int:post_id>/', CommentCreateView.as_view(), name='comment_create'),
    path('forums/<int:pk>/comment/', AddCommentView.as_view(), name='add_comment'),
    path('edit_profile/', UserEditView.as_view(), name='edit_profile'),
    # path('password/', auth_vie
    # ws.PasswordChangeView.as_view(template_name='registration/change-password.html')),
    path('change_password/', views.PasswordChangeView.as_view(template_name = "registration/password_change.html"), name="change-password"),
    path('password_change/', views.PasswordChangeView.as_view(template_name = "registration/password_change.html"), name="password_change"),
    path('password_success/', views.password_success, name="password_success"),
    path('ussd_callback/', ussd_callback, name='ussd_callback'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password_reset/', CustomPasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        success_url='/password_reset_done/',
        email_template_name='registration/password_reset_email.txt',  
        html_email_template_name='registration/password_reset_email.html'  
    ), name='password_reset'),

    path('accounts/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    
    # Redirect old contacts URL to home page footer
    path('contacts/', lambda request: redirect('/#footer-contact')),
    
    # Rewards system URLs
    path('rewards/', RewardsView.as_view(), name='rewards'),
    path('redeem-reward/<int:reward_id>/', redeem_reward, name='redeem_reward'),
    path('carbon-transaction/', views.carbon_transaction, name='carbon_transaction'),
    
    # Fire Risk Prediction URLs
    path('fire-risk/', views.FireRiskView.as_view(), name='fire_risk'),
    path('report-fire/', views.report_fire_observation, name='report_fire_observation'),
    path('report-fire-public/', TemplateView.as_view(template_name='App/public_fire_report.html'), name='public_fire_report'),
    path('field-assessment/', views.FieldAssessmentView.as_view(), name='field_assessment'),
    
    # Export URLs
    path('export/reports/', views.export_reports, name='export_reports'),
    path('export/tree-data/', views.export_tree_data, name='export_tree_data'),
    path('export/fire-data/', views.export_fire_data, name='export_fire_data'),
    path('export/fire-reports/', views.export_fire_reports, name='export_fire_reports'),
    
    # ML Prediction APIs
    path('api/predict-tree-survival/', predict_tree_survival, name='predict_tree_survival'),
    path('predict-tree-survival/', predict_tree_survival, name='predict_tree_survival_public'),
    path('api/species-recommendations/', get_species_recommendations, name='species_recommendations'),
    path('api/climate-data/', get_climate_data, name='get_climate_data'),
    path('api/detect-soil/', views.detect_soil_api, name='detect_soil_api'),
    path('tree-prediction/', views.TreePredictionView.as_view(), name='tree_prediction'),
    path('welcome/', TemplateView.as_view(template_name='App/welcome.html'), name='welcome'),
    
    # Platform Revenue Dashboard (Admin only)
    path('platform-revenue/', views.PlatformRevenueView.as_view(), name='platform_revenue'),





    # path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    # path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),

    # path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
   
    # path('login/', CustomLoginView.as_view(), name='login'),

# from django.urls import path
# from django.contrib.auth import views as auth_views

   
   
]



