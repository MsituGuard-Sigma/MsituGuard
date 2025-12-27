from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView, DeleteView 
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.views import LogoutView, PasswordChangeView
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from .models import Profile, Resource, EmergencyContact, Report, ResourceRequest, ForumPost, Comment, TreePlanting, TreePrediction
# Keep Alert as alias for backward compatibility
Alert = Report
from .forms import UserRegistrationForm,  ResourceForm, ReportForm, ProfileForm,  ResourceRequestForm, ForumPostForm,  FormComment, EditProfileForm, PasswordChangingForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.edit import FormMixin
from django.views import generic
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.views import PasswordResetView
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from .forms import UserForm, ProfileForm
from django.utils import timezone
import os
from django.http import HttpResponse
import csv
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from django.contrib.auth.models import User
from .models import Profile  # Assuming Profile model is in the same app
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
# from django.core.mail import EmailMultiAlternatives
# from django.conf import settings
# from .models import Notification
# from django.core.mail import EmailMultiAlternatives
# from django.conf import settings
# from django.utils.http import urlsafe_base64_decode

# Create your views here.

class HomeView(TemplateView):
    # model = Profile
    template_name = 'App/home.html'

    def dispatch(self, request, *args, **kwargs):
        # Redirect organizations to their dashboard
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.account_type == 'organization':
            return redirect('organization_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['alerts'] = Report.objects.filter(status__in=['verified', 'resolved'])
        context['resources'] = Resource.objects.all()
        
        # Tree planting stats for homepage
        plantings = TreePlanting.objects.all()
        context['total_trees'] = sum(p.number_of_trees for p in plantings)
        context['total_planters'] = plantings.values('planter').distinct().count()
        
        if self.request.user.is_authenticated:
            try:
                context['profile'] = self.request.user.profile
            except Profile.DoesNotExist:
                context['profile'] = None
        
        return context
class UserLogoutView(LogoutView):
    next_page = reverse_lazy('home')

class ResourceListView(LoginRequiredMixin, ListView):
    model = Resource
    template_name = 'App/resource_list.html'
    context_object_name = 'resources'
    login_url = 'login'
    def get_queryset(self):
        return Resource.objects.filter(is_approved=True).order_by('-contributor_id')[:10]

class ResourceCreateView(LoginRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'App/resource_form.html'
    success_url = reverse_lazy('resource_list')

    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self.request.user, 'profile'):
            initial['phoneNumber'] = self.request.user.profile.phoneNumber
            initial['location'] = self.request.user.profile.location
        return initial

    def dispatch(self, request, *args, **kwargs):
        # First, ensure user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # LoginRequiredMixin handles redirect

        # Then check if user is verified
        if not request.user.profile.is_verified:
            if request.user.profile.verification_requested:
                messages.info(request, "Verification request submitted. Admin will review and verify your account.")
            else:
                messages.warning(request, "You must verify your account before contributing resources.")
            return redirect('profile_detail')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Validate phone number matches profile
        if form.cleaned_data['phoneNumber'] != self.request.user.profile.phoneNumber:
            form.add_error('phoneNumber', 'Use the phone number you used to register your account. If you lost access to this number, please update your profile first.')
            return self.form_invalid(form)
        
        form.instance.contributor = self.request.user
        form.instance.is_approved = False  # Admin will approve manually
        self.object = form.save()
        
        messages.success(self.request, 'Resource shared successfully! Thank you for contributing to the community.')
        
        return render(self.request, self.template_name, {
            'submitted': True  # Pass a flag to the template
        })
class ResourceUpdateView(LoginRequiredMixin, UpdateView):
    model = Resource
    form_class = ResourceForm
    template_name = 'App/resource_form.html'
    success_url = reverse_lazy('resource_list')


class ResourceDeleteView(LoginRequiredMixin, DeleteView):
    model = Resource
    template_name = 'App/resource_confirm_delete.html'
    success_url = reverse_lazy('resource_list')


class ResourceDetailView(DetailView):
    model = Resource
    template_name = 'App/resource_detail.html' 
    context_object_name = 'resource'


@login_required
@require_POST
def request_verification(request):
    profile = request.user.profile
    if profile.verification_requested:
        messages.info(request, "You've already requested verification. Please wait for approval.")
    else:
        profile.verification_requested = True
        profile.save()
        messages.success(request, "Verification request submitted. Admin will review and verify your account.")
    return redirect('profile_detail')


    
class ProfileDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Profile
    form_class = ProfileForm
    template_name = 'App/profile_detail.html'
    success_url = reverse_lazy('profile_detail')

    def get_object(self, queryset=None):
        return get_object_or_404(Profile, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        
        # Add tree registration data
        try:
            from treeregistration.models import Tree, UserProfile
            user_profile = UserProfile.objects.filter(user=self.request.user).first()
            if user_profile:
                context['tree_count'] = user_profile.tree_count
                context['badge'] = user_profile.badge
                context['trees'] = Tree.objects.filter(user=self.request.user).order_by('-uploaded_at')[:12]
            else:
                context['tree_count'] = 0
                context['badge'] = 'None'
                context['trees'] = []
        except Exception as e:
            # If tree registration app is not available, set defaults
            context['tree_count'] = 0
            context['badge'] = 'None'
            context['trees'] = []
        
        return context

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(instance=self.get_object())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            self.object.profile_picture = request.FILES['profile_picture']
            self.object.save()
            messages.success(request, "Profile picture updated successfully!")
            return redirect('profile_detail')
        
        # Handle quick edit for phone and location
        if 'phoneNumber' in request.POST and 'location' in request.POST:
            phone = request.POST.get('phoneNumber', '').strip()
            location = request.POST.get('location', '').strip()
            
            # Validate phone number
            import re
            if phone and not re.match(r'^\+?[0-9]{10,15}$', phone.replace(' ', '').replace('-', '')):
                messages.error(request, "Please enter a valid phone number (10-15 digits)")
                return redirect('profile_detail')
            
            # Validate location
            if location and len(location) < 3:
                messages.error(request, "Please provide a more specific location")
                return redirect('profile_detail')
            
            # Update fields
            if phone:
                self.object.phoneNumber = phone
            if location:
                self.object.location = location
                
            self.object.save()
            messages.success(request, "Contact information updated successfully!")
            return redirect('profile_detail')
        
        # Handle regular form submission
        form = self.get_form_class()(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)
        

class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = 'App/report_list.html'
    context_object_name = 'reports'
    login_url = 'login'

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user)


class ReportCreateView(CreateView):
    model = Report
    form_class = ReportForm
    template_name = 'App/report_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            initial['phoneNumber'] = self.request.user.profile.phoneNumber
        return initial

    def form_valid(self, form):
        try:
            # Save the report with files
            report = form.save(commit=False)
            # Handle anonymous users
            if self.request.user.is_authenticated:
                report.reporter = self.request.user
            report.status = 'new'
            report.save()
            print(f"Report saved successfully: {report.id}")
            
            # Handle file upload only if a valid file is provided
            if 'image' in self.request.FILES:
                uploaded_file = self.request.FILES['image']
                if uploaded_file and uploaded_file.size > 0:
                    try:
                        report.image = uploaded_file
                        report.save()
                        print(f"Image uploaded successfully: {uploaded_file.name}, size: {uploaded_file.size}")
                    except Exception as img_error:
                        print(f"Image upload failed: {img_error}")
                        # Continue without image
                else:
                    print(f"No valid file provided, continuing without image")
            else:
                print(f"No image file in request, continuing without image")
            
            # Send email notification only once
            try:
                self.send_submission_email(report)
                print(f"Email sent successfully")
            except Exception as e:
                print(f"Email sending failed: {e}")
                # Continue even if email fails
            
            self.object = report
            # Use redirect to prevent form resubmission
            messages.success(self.request, 'Environmental Report Successfully Created! Your report has been submitted and will be reviewed immediately.')
            print(f"About to redirect")
            return render(self.request, self.template_name, {'submitted': True})
            
        except Exception as e:
            print(f"Form validation error: {e}")
            import traceback
            traceback.print_exc()
            
            # If it's a Cloudinary error, still save the report without image
            if "Empty file" in str(e) or "cloudinary" in str(e).lower():
                messages.success(self.request, 'Environmental Report Successfully Created! Your report has been submitted and will be reviewed immediately.')
                return redirect('report_create')
            else:
                messages.error(self.request, f'Error submitting report: {str(e)}')
                return self.form_invalid(form)
    
    def send_submission_email(self, report):
        try:
            dashboard_url = self.request.build_absolute_uri(reverse('home'))
            
            # Use the styled HTML email template
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f0fdf4; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; }}
                    .header {{ background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
                    .btn {{ background-color: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }}
                    .details {{ background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #22c55e; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌱 MsituGuard</h1>
                        <h2>Report Submitted Successfully</h2>
                        <p>Thank you for protecting our environment!</p>
                    </div>
                    <div class="content">
                        <h3>Hello {report.reporter.first_name or report.reporter.username},</h3>
                        <p>Thank you for submitting your environmental report <strong>"{report.title}"</strong>.</p>
                        
                        <p>Our team will investigate and verify this issue. You will receive email updates when the status changes.</p>
                        
                        <div class="details">
                            <h4>📄 Report Details:</h4>
                            <p><strong>Type:</strong> {report.get_report_type_display()}</p>
                            <p><strong>Location:</strong> {report.location_name}</p>
                            <p><strong>Status:</strong> Under Review</p>
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="{dashboard_url}" class="btn">Track Your Report Progress</a>
                        </div>
                        
                        <p>Thank you for being an environmental guardian! 🌿</p>
                        
                        <p>Best regards,<br><strong>MsituGuard Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>© 2024 MsituGuard - Environmental Protection Platform</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg = EmailMultiAlternatives(
                subject='🌱 Report Submitted Successfully',
                body=f'Hello {report.reporter.username},\n\nThank you for submitting "{report.title}". Track progress: {dashboard_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[report.reporter.email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            
        except Exception as e:
            print(f"Email sending failed: {e}")
            raise e

class ReportUpdateView(UpdateView):
    model = Report
    form_class = ReportForm
    template_name = 'App/report_form.html'
    success_url = reverse_lazy('report_list')

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user)  

        
class LatestReportsView(ListView):
    model = Report
    template_name = 'App/latest_reports.html'  
    context_object_name = 'reports'

    def get_queryset(self):
        return Report.objects.filter(status__in=['verified', 'resolved']).order_by('-timestamp')[:10]

   
class ReportDetailView(DetailView):
    model = Report
    template_name = 'App/report_detail.html'
    context_object_name = 'report'

@login_required
def remove_profile_picture(request):
    profile = request.user.profile
    profile.profile_picture.delete()
    profile.save()
    return redirect('profile_detail')


class ResourceRequestCreateView(LoginRequiredMixin, CreateView):
    model = ResourceRequest
    form_class = ResourceRequestForm
    template_name = 'App/request_resource.html'
    success_url = reverse_lazy('request_success')
    login_url = 'login'

    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self.request.user, 'profile'):
            initial['phoneNumber'] = self.request.user.profile.phoneNumber
            initial['location'] = self.request.user.profile.location
        return initial

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user has phone number in profile
        if not hasattr(request.user, 'profile') or not request.user.profile.phoneNumber or request.user.profile.phoneNumber.strip() == '':
            messages.warning(request, "Please update your phone number in your profile before planting trees.")
            return redirect('profile_detail')
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Validate phone number matches profile
        if form.cleaned_data['phoneNumber'] != self.request.user.profile.phoneNumber:
            form.add_error('phoneNumber', 'Use the phone number you used to register your account. If you lost access to this number, please update your profile first.')
            return self.form_invalid(form)
        
        form.instance.user = self.request.user
        return super().form_valid(form)


class ResourceRequestListView(LoginRequiredMixin,ListView):
    model = ResourceRequest
    template_name = 'App/resource_requests.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return ResourceRequest.objects.filter(user=self.request.user).order_by('-date_requested')
        


class RequestSuccessView(TemplateView):
    template_name = 'App/request_success.html'


class UseRegisterView(generic.CreateView):
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if this is organization-only registration
        context['organization_only'] = self.kwargs.get('organization_only', False)
        return context

    def form_valid(self, form):
        # Check if this is organization registration and validate account type
        if self.kwargs.get('organization_only', False):
            if form.cleaned_data.get('account_type') != 'organization':
                form.add_error('account_type', 'This registration link is for organizations only.')
                return self.form_invalid(form)
        
        response = super().form_valid(form)
        
        # Link existing tree plantings if phone numbers match
        user = self.object
        if hasattr(user, 'profile') and user.profile.phoneNumber:
            linked_plantings = TreePlanting.objects.filter(
                planter__isnull=True,
                phoneNumber=user.profile.phoneNumber
            )
            linked_count = linked_plantings.count()
            if linked_count > 0:
                linked_plantings.update(planter=user)
                messages.success(self.request, f"Registration successful! We've linked {linked_count} of your previous tree plantings to your account.")
            else:
                messages.success(self.request, "Registration successful! Welcome to MsituGuard.")
        else:
            messages.success(self.request, "Registration successful! Welcome to MsituGuard.")
        
        return response


class ForumPostListView(LoginRequiredMixin, ListView):
    model = ForumPost
    template_name = 'App/forum_post_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    form_class = ForumPostForm


    def forum_post_list(request):
        query = request.GET.get('q')
        if query:
            posts = ForumPost.objects.filter(
                Q(title__icontains=query) | Q(user__username__icontains=query)
            ).order_by('-created_at')
        else:
            posts = ForumPost.objects.all().order_by('-created_at')
        
        return render(request, 'App/forum_post_list.html', {'posts': posts})

   
class ForumPostCreateView(LoginRequiredMixin, CreateView):
    model = ForumPost
    form_class = ForumPostForm
    template_name = 'App/forum_post_create.html'
    success_url = reverse_lazy('forum_post_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Forum post created successfully!')
        return response

class ForumPostDetailView(LoginRequiredMixin, DetailView):
    model = ForumPost
    template_name = 'App/forum_post_detail.html'
    context_object_name = 'post'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = FormComment()
        return context


class AddCommentView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = FormComment
    template_name = 'App/add_comment.html'
    login_url = 'login'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.post_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('forum_post_detail', kwargs={'pk': self.kwargs['pk']}) + '#comments'
class UserEditView(UpdateView):
    model = User
    form_class = UserForm
    template_name = 'registration/edit_profile.html'
    success_url = reverse_lazy('profile_detail')

    def get_object(self, queryset=None):
        # Return the logged-in user object
        return self.request.user

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            data['profile_form'] = ProfileForm(self.request.POST, instance=self.request.user.profile)
        else:
            data['profile_form'] = ProfileForm(instance=self.request.user.profile)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        if profile_form.is_valid():
            self.object = form.save()
            profile_form.instance = self.object.profile
            profile_form.save()
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class PasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = PasswordChangingForm
    login_url = 'login'
    success_url = reverse_lazy('password_success')


def password_success(request):
    return render(request, "registration/password_change_success.html")


class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    success_message = "We've emailed you instructions for setting your password."

    def form_valid(self, form):
        return super().form_valid(form)



class profile(LoginRequiredMixin, generic.View):
    model = User
    login_url = 'login'
    template_name = "App/profile.html"

    def get(self, request, user_name):
        user_related_data = User.objects.filter(author__username=user_name)[:6]
        user_profile_data = Profile.objects.get(user=request.user.id)
        context = {
            "user_related_data": user_related_data,
            'user_profile_data': user_profile_data
        }
        return render(request, self.template_name, context)


class ApprovedReportListView(ListView):
    model = Report
    template_name = 'App/approved_alerts.html'  # The template where reports will be rendered
    context_object_name = 'approved_alerts'

    def get_queryset(self):
        return Report.objects.filter(status__in=['verified', 'resolved'])

class ApprovedContributeListView(ListView):
    model = Resource
    template_name = 'App/approved_contributes.html'  # The template where alerts will be rendered
    context_object_name = 'approved_contributes'

    def get_queryset(self):
        approved_contributes = Resource.objects.filter(is_approved=True)
        # logger.debug(f'Approved resources retrieved: {approved_contributes}')  # Log the alerts
        return approved_contributes

class OrganizationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'App/organization_dashboard.html'
    login_url = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user is admin or organization
        if request.user.is_superuser:
            # Admin can access
            return super().dispatch(request, *args, **kwargs)
        elif hasattr(request.user, 'profile') and request.user.profile.account_type == 'organization':
            # Organization can access
            return super().dispatch(request, *args, **kwargs)
        else:
            # Regular users cannot access
            messages.error(request, "Access denied. Organization account or admin privileges required.")
            return redirect('home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = Report.objects.all().order_by('-timestamp')
        
        # Stats for dashboard
        context['new_count'] = reports.filter(status='new').count()
        context['verified_count'] = reports.filter(status='verified').count()
        context['resolved_count'] = reports.filter(status='resolved').count()
        context['total_count'] = reports.count()
        context['reports'] = reports
        
        # Tree planting data
        tree_plantings = TreePlanting.objects.all().order_by('-planted_date')
        context['tree_plantings'] = tree_plantings
        context['total_trees_planted'] = sum(p.number_of_trees for p in tree_plantings)
        context['total_tree_planters'] = tree_plantings.values('planter').distinct().count()
        context['verified_tree_plantings'] = tree_plantings.filter(status='verified').count()
        
        # Tree Registration data from treeregistration app
        try:
            from treeregistration.models import Tree, UserProfile
            
            # All registered trees
            registered_trees = Tree.objects.all().order_by('-uploaded_at')
            context['registered_trees'] = registered_trees
            context['total_registered_trees'] = registered_trees.count()
            
            # All user profiles with tree counts
            user_profiles = UserProfile.objects.all().order_by('-tree_count')
            context['user_profiles'] = user_profiles
            context['total_tree_users'] = user_profiles.count()
            
            # Organization-specific data
            org_profiles = user_profiles.filter(user_type='organisation')
            individual_profiles = user_profiles.filter(user_type='individual')
            
            context['org_tree_users'] = org_profiles.count()
            context['individual_tree_users'] = individual_profiles.count()
            
            # Organization-specific registered trees
            org_registered_trees = registered_trees.filter(user__treeregistration_profile__user_type='organisation')
            individual_registered_trees = registered_trees.filter(user__treeregistration_profile__user_type='individual')
            
            context['org_registered_trees'] = org_registered_trees
            context['individual_registered_trees'] = individual_registered_trees
            context['org_registered_trees_count'] = org_registered_trees.count()
            context['individual_registered_trees_count'] = individual_registered_trees.count()
            
            # Badge statistics for all users
            context['diamond_users'] = user_profiles.filter(badge='Diamond').count()
            context['gold_users'] = user_profiles.filter(badge='Gold').count()
            context['silver_users'] = user_profiles.filter(badge='Silver').count()
            context['bronze_users'] = user_profiles.filter(badge='Bronze').count()
            
            # Organization badge statistics
            context['org_diamond_users'] = org_profiles.filter(badge='Diamond').count()
            context['org_gold_users'] = org_profiles.filter(badge='Gold').count()
            context['org_silver_users'] = org_profiles.filter(badge='Silver').count()
            context['org_bronze_users'] = org_profiles.filter(badge='Bronze').count()
            
            # Recent organization registrations
            context['recent_org_trees'] = Tree.objects.filter(
                user__treeregistration_profile__user_type='organisation'
            ).order_by('-uploaded_at')[:6]
            
        except ImportError:
            # If treeregistration app is not available
            context['registered_trees'] = []
            context['total_registered_trees'] = 0
            context['user_profiles'] = []
            context['total_tree_users'] = 0
            context['org_tree_users'] = 0
            context['individual_tree_users'] = 0
            context['org_registered_trees'] = []
            context['individual_registered_trees'] = []
            context['org_registered_trees_count'] = 0
            context['individual_registered_trees_count'] = 0
            context['diamond_users'] = 0
            context['gold_users'] = 0
            context['silver_users'] = 0
            context['bronze_users'] = 0
            context['org_diamond_users'] = 0
            context['org_gold_users'] = 0
            context['org_silver_users'] = 0
            context['org_bronze_users'] = 0
            context['recent_org_trees'] = []
        
        return context

@csrf_exempt
def update_report_status(request, report_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            report = Report.objects.get(id=report_id)
            old_status = report.status
            report.status = data['status']
            report.save()
            
            # No notification needed for anonymous reporting
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def detect_soil_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not latitude or not longitude:
                return JsonResponse({'success': False, 'error': 'Latitude and longitude required'})
            
            # Use MISTRAL AI to detect soil type
            soil_type = detect_soil_with_mistral(latitude, longitude)
            
            # Detect region and county
            region, county = detect_region_county(latitude, longitude)
            
            return JsonResponse({
                'success': True,
                'soil_type': soil_type,
                'region': region,
                'county': county,
                'coordinates': f"{latitude}, {longitude}"
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POST method required'})

@csrf_exempt
def update_tree_status(request, tree_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tree_planting = TreePlanting.objects.get(id=tree_id)
            old_status = tree_planting.status
            tree_planting.status = data['status']
            tree_planting.save()
            
            print(f"Tree status updated: {tree_planting.title} from {old_status} to {data['status']}")
            
            # Award tokens and send notification if verified (only if status changed)
            if data['status'] == 'verified' and old_status != 'verified':
                print(f"Tree planting verified: {tree_planting.title}")
                
                if tree_planting.planter:
                    # Registered user - award tree points
                    points_awarded = tree_planting.award_tree_points()
                    send_tree_verification_notification(tree_planting)
                else:
                    # Unregistered user - send registration encouragement email
                    print(f"Unregistered user - sending registration encouragement email")
                    send_unregistered_reward_notification(tree_planting)
            
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error updating tree status: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})

def send_tree_verification_notification(tree_planting):
    try:
        print(f"Starting tree verification notification for: {tree_planting.title}")
        
        # Calculate tree points
        points_earned = tree_planting.number_of_trees
        
        # Determine badge based on tree count
        if tree_planting.number_of_trees >= 50:
            badge = "🌳 Forest Hero"
        elif tree_planting.number_of_trees >= 20:
            badge = "🌲 Tree Champion"
        elif tree_planting.number_of_trees >= 10:
            badge = "🌿 Green Warrior"
        elif tree_planting.number_of_trees >= 5:
            badge = "🌱 Eco Defender"
        else:
            badge = "🍃 Nature Friend"
        
        # Add badge to user profile
        tree_planting.planter.profile.add_badge(badge)
        
        # Add special 15 billion trees initiative badge for first-time planters
        user_tree_count = TreePlanting.objects.filter(planter=tree_planting.planter, status='verified').count()
        if user_tree_count == 1:  # First verified tree planting
            tree_planting.planter.profile.add_badge("🌍 15 Billion Trees Initiative Participant")
        
        print(f"Awarded {points_earned} tree points and badge to user")
        
        # Get profile (should already exist)
        profile = tree_planting.planter.profile
        print(f"Updated profile with tree points: {profile.tree_points}")
        
        # No notification creation for anonymous reporting
        print("Tree planting verified, no notification created")
        
        # Send HTML email with rewards
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f0fdf4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
                .btn {{ background-color: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }}
                .details {{ background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #22c55e; }}
                .rewards {{ background: linear-gradient(135deg, #fef3c7, #fbbf24); padding: 25px; border-radius: 15px; margin: 20px 0; text-align: center; }}
                .reward-item {{ background: white; padding: 15px; border-radius: 10px; margin: 10px; display: inline-block; min-width: 120px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌱 MsituGuard</h1>
                    <h2>🎉 Tree Planting Verified!</h2>
                    <p>Your environmental contribution has been officially verified</p>
                </div>
                <div class="content">
                    <h3>Hello {tree_planting.planter.first_name or tree_planting.planter.username},</h3>
                    <p>Great news! Your tree planting contribution has been verified by our local organization partners.</p>
                    
                    <div class="details">
                        <h4>🌳 {tree_planting.title}</h4>
                        <p><strong>Location:</strong> {tree_planting.location_name}</p>
                        <p><strong>Trees Planted:</strong> {tree_planting.number_of_trees}</p>
                        <p><strong>Tree Type:</strong> {tree_planting.get_tree_type_display()}</p>
                        <p style="color: #22c55e; font-weight: bold;">✅ VERIFIED</p>
                    </div>
                    
                    <div class="rewards">
                        <h3 style="color: #92400e; margin-top: 0;">🎉 Congratulations! You've Earned Rewards!</h3>
                        <div style="text-align: center;">
                            <div class="reward-item">
                                <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{points_earned}</div>
                                <div style="color: #6b7280; font-size: 14px;">Tree Points Earned</div>
                            </div>
                            <div class="reward-item">
                                <div style="font-size: 18px; font-weight: bold; color: #f59e0b;">{badge}</div>
                                <div style="color: #6b7280; font-size: 14px;">New Badge</div>
                            </div>
                        </div>
                        <p style="color: #92400e; margin: 10px 0; font-weight: 600;">Your Rank: {profile.conservation_rank}</p>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; border: 2px solid #0ea5e9;">
                        <h4 style="color: #0c4a6e; margin-top: 0;">🏆 Certificate Earned!</h4>
                        <p style="color: #0c4a6e; margin: 10px 0;">You've earned your official 15 Billion Trees Initiative Certificate! View it in your dashboard.</p>
                    </div>
                    
                    <p>Your contribution to Kenya's 15 billion trees initiative is now officially recognized. Thank you for being an environmental guardian!</p>
                    
                    <div style="text-align: center;">
                        <a href="http://127.0.0.1:8000/" class="btn">Visit MsituGuard</a>
                    </div>
                    
                    <p style="margin-top: 30px;">Keep up the great work protecting our forests and environment. 🌿</p>
                    
                    <p>Best regards,<br><strong>MsituGuard Team</strong><br><em>Protecting Kenya's Environment Together</em></p>
                </div>
                <div class="footer">
                    <p>© 2024 MsituGuard - Environmental Protection Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        print(f"Sending email to: {tree_planting.planter.email}")
        print(f"User tree count: {user_tree_count}")
        print(f"Is first time planter: {user_tree_count == 1}")
        
        msg = EmailMultiAlternatives(
            subject='Tree Planting Verified - Points & Badge Earned! - MsituGuard',
            body=f'Hello {tree_planting.planter.first_name},\n\nYour tree planting "{tree_planting.title}" has been verified! You earned {points_earned} tree points and the "{badge}" badge.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[tree_planting.planter.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)  # Show email errors for debugging
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"Tree verification notification failed: {e}")
        import traceback
        traceback.print_exc()


def send_unregistered_reward_notification(tree_planting):
    try:
        # Calculate rewards
        points_earned = tree_planting.number_of_trees
        
        if tree_planting.number_of_trees >= 50:
            badge = "🌳 Forest Hero"
        elif tree_planting.number_of_trees >= 20:
            badge = "🌲 Tree Champion"
        elif tree_planting.number_of_trees >= 10:
            badge = "🌿 Green Warrior"
        elif tree_planting.number_of_trees >= 5:
            badge = "🌱 Eco Defender"
        else:
            badge = "🍃 Nature Friend"
        
        # Tokens are awarded by the award_tokens method when status changes to verified
        
        # Get email from phone number (find user with this phone)
        from .models import Profile
        try:
            profile = Profile.objects.get(phoneNumber=tree_planting.phoneNumber)
            user = profile.user
            
            # Only send email if user has verified their email (is_active=True)
            if not user.is_active:
                print(f"User {user.email} has not verified email yet - no reward email sent")
                return
                
            email = user.email
            name = tree_planting.planter_name or user.first_name or "Environmental Guardian"
        except Profile.DoesNotExist:
            print(f"No profile found for phone: {tree_planting.phoneNumber}")
            return
        
        register_url = "http://127.0.0.1:8000/register/"
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f0fdf4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .footer {{ background-color: #f8fafc; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
                .btn {{ background-color: #22c55e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 15px 10px; font-weight: bold; }}
                .btn-secondary {{ background-color: #3b82f6; }}
                .details {{ background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #22c55e; }}
                .rewards {{ background: linear-gradient(135deg, #fef3c7, #fbbf24); padding: 25px; border-radius: 15px; margin: 20px 0; text-align: center; }}
                .reward-item {{ background: white; padding: 15px; border-radius: 10px; margin: 10px; display: inline-block; min-width: 120px; }}
                .cta-section {{ background: linear-gradient(135deg, #eff6ff, #dbeafe); padding: 25px; border-radius: 15px; margin: 20px 0; text-align: center; border: 2px solid #3b82f6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌱 MsituGuard</h1>
                    <h2>🎉 Tree Planting Verified!</h2>
                    <p>Your environmental contribution has been officially verified</p>
                </div>
                <div class="content">
                    <h3>Hello {name},</h3>
                    <p>Great news! Your tree planting contribution has been verified by our local organization partners.</p>
                    
                    <div class="details">
                        <h4>🌳 {tree_planting.title}</h4>
                        <p><strong>Location:</strong> {tree_planting.location_name}</p>
                        <p><strong>Trees Planted:</strong> {tree_planting.number_of_trees}</p>
                        <p><strong>Tree Type:</strong> {tree_planting.get_tree_type_display()}</p>
                        <p style="color: #22c55e; font-weight: bold;">✅ VERIFIED</p>
                    </div>
                    
                    <div class="rewards">
                        <h3 style="color: #92400e; margin-top: 0;">🎉 You've Earned Rewards!</h3>
                        <div style="text-align: center;">
                            <div class="reward-item">
                                <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{tokens_earned}</div>
                                <div style="color: #6b7280; font-size: 14px;">Tokens Earned</div>
                            </div>
                            <div class="reward-item">
                                <div style="font-size: 18px; font-weight: bold; color: #f59e0b;">{badge}</div>
                                <div style="color: #6b7280; font-size: 14px;">Badge Earned</div>
                            </div>
                        </div>
                        <p style="color: #92400e; margin: 10px 0; font-weight: 600;">Your rewards are waiting for you!</p>
                    </div>
                    
                    <div class="cta-section">
                        <h3 style="color: #1d4ed8; margin-top: 0;">🎆 Claim Your Complete Rewards!</h3>
                        <p style="color: #1e40af; margin-bottom: 20px;">Create your free MsituGuard account to:</p>
                        <ul style="text-align: left; color: #1e40af; max-width: 400px; margin: 0 auto;">
                            <li>✅ View your complete reward dashboard</li>
                            <li>🏆 Track your environmental impact</li>
                            <li>🌳 Join Kenya's tree planting leaderboard</li>
                            <li>📊 Submit more environmental reports</li>
                            <li>🌟 Earn more badges and recognition</li>
                        </ul>
                        <div style="margin-top: 25px;">
                            <a href="{register_url}" class="btn">Create Free Account & Claim Rewards</a>
                        </div>
                        <p style="color: #6b7280; font-size: 14px; margin-top: 15px;">Takes less than 2 minutes • No spam • Your rewards are waiting!</p>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; border: 2px solid #0ea5e9;">
                        <h4 style="color: #0c4a6e; margin-top: 0;">🏆 Certificate Available!</h4>
                        <p style="color: #0c4a6e; margin: 10px 0;">You've earned an official 15 Billion Trees Initiative Certificate! Register to claim and download it.</p>
                    </div>
                    
                    <p>Your contribution to Kenya's 15 billion trees initiative is now officially recognized. Thank you for being an environmental guardian!</p>
                    
                    <p style="margin-top: 30px;">Keep up the great work protecting our forests and environment. 🌿</p>
                    
                    <p>Best regards,<br><strong>MsituGuard Team</strong><br><em>Protecting Kenya's Environment Together</em></p>
                </div>
                <div class="footer">
                    <p>© 2024 MsituGuard - Environmental Protection Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = EmailMultiAlternatives(
            subject='Tree Planting Verified - Claim Your Rewards! - MsituGuard',
            body=f'Hello {name},\n\nYour tree planting "{tree_planting.title}" has been verified! You earned {points_earned} tree points and the "{badge}" badge. Create your free account to claim your complete rewards: {register_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        print(f"Unregistered reward email sent to: {email}")
        
    except Exception as e:
        print(f"Unregistered reward notification failed: {e}")

class TreeInitiativeView(TemplateView):
    template_name = 'App/tree_initiative.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plantings = TreePlanting.objects.all()
        
        context['total_trees'] = sum(p.number_of_trees for p in plantings)
        context['total_planters'] = plantings.values('planter').distinct().count()
        context['verified_plantings'] = plantings.filter(status='verified').count()
        context['recent_plantings'] = plantings.order_by('-planted_date')[:6]
        
        return context

class TreePlantingFormView(LoginRequiredMixin, CreateView):
    model = TreePlanting
    template_name = 'App/tree_planting_form.html'
    fields = ['location_name', 'latitude', 'longitude', 'tree_type', 'number_of_trees', 'description', 'after_image']
    login_url = 'login'
    
    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self.request.user, 'profile'):
            initial['phoneNumber'] = self.request.user.profile.phoneNumber
        return initial
    
    def form_valid(self, form):
        # Validate phone number matches profile
        if form.cleaned_data['phoneNumber'] != self.request.user.profile.phoneNumber:
            messages.error(self.request, 'Phone number must match your registered number. Please update your profile if you need to change it.')
            return redirect('profile_detail')
        
        form.instance.planter = self.request.user
        form.instance.status = 'planned' if not form.instance.after_image else 'planted'
        form.instance.title = f'Tree Planting by {self.request.user.first_name or self.request.user.username}'
        self.object = form.save()
        
        messages.success(self.request, f'Tree planting registered successfully! {self.object.number_of_trees} trees recorded.')
        return redirect('tree_planting_form')

class TreePlantingsListView(ListView):
    model = TreePlanting
    template_name = 'App/tree_plantings_list.html'
    context_object_name = 'plantings'
    paginate_by = 12
    
    def get_queryset(self):
        return TreePlanting.objects.all().order_by('-planted_date')



user_sessions = {}

logger = logging.getLogger(__name__)

def register_user(username, password, phone_number):
    if User.objects.filter(username=username).exists():
        return False  # Username already exists
    if Profile.objects.filter(phone_number=phone_number).exists():
        return False  # Phone number already registered
    
    # Create the user
    user = User.objects.create_user(username=username, password=password)
    
    # Create a new profile
    Profile.objects.create(user=user, phone_number=phone_number)
    return True  # Registration successful

def authenticate_user(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return True
    except User.DoesNotExist:
        return False
    return False

@csrf_exempt
def ussd_callback(request):
    logger.info("Request Headers: %s", request.headers)
    logger.info("Request Body: %s", request.body)
    logger.info("Request Method: %s", request.method)
    logger.info("Current session state: %s", user_sessions)

    # Check if the request method is POST
    if request.method != "POST":
        return HttpResponse("Bad Request: Expected POST method", status=400)

    # Initialize the response variable
    response = "END Invalid request. Please try again."

    # Get parameters from the request
    session_id = request.POST.get('sessionId')
    service_code = request.POST.get('serviceCode')
    phone_number = request.POST.get('phoneNumber')
    text = request.POST.get('text', '')  # Default to an empty string

    logger.info("Parameters: sessionId=%s, serviceCode=%s, phoneNumber=%s, text=%s", session_id, service_code, phone_number, text)

    input_steps = text.split('*')
    logger.info("Input steps: %s", input_steps)

    if text == '':
        # Initial welcome message for all users
        response = "CON Welcome to the Crisis Communication Platform\n"
        response += "1. Latest Alerts\n"
        response += "2. Request a Resource\n"
        response += "3. Share a Resource\n"
        response += "4. Volunteer Opportunities\n"
        response += "5. Emergency Contacts\n"
        response += "6. View Resources\n"
        response += "7. Your Profile\n"
        response += "8. About the Platform\n"
        response += "9. Register/Login\n"
        response += "0. Exit"

    elif input_steps[0] == '1':
        response = "END Here are the latest alerts:\n"  # Logic to fetch and display alerts

    elif input_steps[0] == '2':  # Request a Resource flow
        if len(input_steps) == 1:
            # Step 1: Ask for the type of resource
            response = "CON Request a Resource:\nPlease enter the type of resource you need:"
        elif len(input_steps) == 2:
            # Step 2: Ask for a description
            resource_type = input_steps[1]
            response = f"CON You entered: {resource_type}\nPlease provide a brief description of the resource:"
        elif len(input_steps) == 3:
            # Step 3: Ask for location
            resource_description = input_steps[2]
            response = f"CON Description: {resource_description}\nPlease provide your location:"
        elif len(input_steps) == 4:
            # Step 4: Confirm submission
            location = input_steps[3]
            resource_type = input_steps[1]
            resource_description = input_steps[2]
            response = f"END Resource Request Submitted Successfully!\nResource type: {resource_type}\nDescription: {resource_description}\nLocation: {location}\nWe will process your request soon."
        else:
            response = "END Invalid input. Please try again."

    elif input_steps[0] == '3':  # Share a Resource
        response = "CON Share a Resource:\nPlease enter the details of the resource you're sharing."
    elif input_steps[0] == '4':  # Volunteer Opportunities
        response = "CON Volunteer Opportunities:\nPlease enter your availability."
    elif input_steps[0] == '5':  # Emergency Contacts
        response = "CON Emergency Contacts:\n1. Local Disaster Response Team\n2. Police\n3. Ambulance"
    elif input_steps[0] == '6':  # View Resources
        response = "CON View Resources:\n1. Food\n2. Clothes"
    elif input_steps[0] == '7':  # Your Profile
        response = "CON Your Profile:\n1. View Details\n2. Edit Profile"
    elif input_steps[0] == '8':  # About the Platform
        response = "END About the Platform:\nThis platform helps communities during crises by sharing resources and sending alerts."
    elif input_steps[0] == '9':  # Register/Login
        if len(input_steps) == 1:
            # Step 1: Show login/registration options
            response = "CON Welcome to the Crisis Communication Platform\n"
            response += "1. Register\n"
            response += "2. Login\n"
        elif input_steps[1] == '1':  # Registration Flow
            if len(input_steps) == 2:
                response = "CON Register:\nPlease enter your username:"
            elif len(input_steps) == 3:
                response = "CON Enter your password:"
            elif len(input_steps) == 4:
                response = "CON Confirm your password:"
            elif len(input_steps) == 5:
                username = input_steps[2]
                password = input_steps[3]
                confirm_password = input_steps[4]

                if password != confirm_password:
                    response = "END Passwords do not match. Please try again."
                else:
                    registration_success = register_user(username=username, password=password, phone_number=phone_number)

                    if registration_success:
                        response = f"END Registration successful! Welcome, {username}."
                    else:
                        response = "END Username already taken. Please try a different username."
        elif input_steps[1] == '2':  # Login Flow
            if len(input_steps) == 2:
                response = "CON Login:\nPlease enter your username:"
            elif len(input_steps) == 3:
                response = "CON Enter your password:"
            elif len(input_steps) == 4:
                username = input_steps[2]
                password = input_steps[3]

                if authenticate_user(username=username, password=password):
                    response = "CON Welcome back, {}!\n".format(username)
                    response += "1. Latest Alerts\n"
                    response += "2. Request a Resource\n"
                    response += "3. Share a Resource\n"
                    response += "4. Volunteer Opportunities\n"
                    response += "5. Emergency Contacts\n"
                    response += "6. View Resources\n"
                    response += "7. Your Profile\n"
                    response += "8. About the Platform\n"
                    response += "0. Exit"
                else:
                    response = "END Invalid login. Please check your credentials."

    elif text == '0':
        response = "END Thank you for using the Crisis Communication Platform. Goodbye!"

    return HttpResponse(response, content_type='text/plain')

def public_tree_planting(request):
    if request.method == 'POST':
        try:
            # Extract form data
            full_name = request.POST.get('full_name')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('email')
            location = request.POST.get('location')
            number_of_trees = int(request.POST.get('number_of_trees', 1))
            tree_type = request.POST.get('tree_species', 'indigenous')
            planting_date = request.POST.get('planting_date')
            description = request.POST.get('description', '')
            before_image = request.FILES.get('before_image')
            after_image = request.FILES.get('after_image')
            
            # Generate temporary password
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # Check if user already exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': full_name.split()[0] if full_name else '',
                    'last_name': ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    'is_active': False  # Require email verification
                }
            )
            
            if created:
                user.set_password(temp_password)
                user.save()
            
            # Create or update profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'phoneNumber': phone_number,
                    'location': location,
                    'account_type': 'individual'
                }
            )
            
            if not profile_created:
                # Update existing profile
                profile.phoneNumber = phone_number
                profile.location = location
                profile.save()
            
            # Create tree planting record
            tree_planting = TreePlanting.objects.create(
                planter=user if user.is_active else None,
                planter_name=full_name,
                title=f'Tree Planting by {full_name}',
                location_name=location,
                tree_type=tree_type,
                number_of_trees=number_of_trees,
                description=description,
                phoneNumber=phone_number,
                status='planted' if after_image else 'planned',
                before_image=before_image,
                after_image=after_image
            )
            
            # Send verification email with password
            send_verification_email(user, request, temp_password if created else None)
            
            messages.success(request, f'🌱 Thank you {full_name}! Your tree planting has been registered successfully. We\'ve sent verification details to your email.')
            return redirect('http://localhost:8000/rewards/')
            
        except Exception as e:
            messages.error(request, f'Error submitting tree planting: {str(e)}')
            return redirect('public_tree_form')
    
    return redirect('home')

def send_verification_email(user, request, temp_password=None):
    try:
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_url = request.build_absolute_uri(
            reverse('verify_tree_planting_account', kwargs={'uidb64': uid, 'token': token})
        )
        
        html_message = render_to_string('App/emails/tree_planting_verification.html', {
            'user': user,
            'verification_url': verification_url,
            'temp_password': temp_password,
            'login_url': request.build_absolute_uri(reverse('login')),
            'is_logged_in': request.user.is_authenticated,
        })
        
        send_mail(
            subject='Verify Your Tree Planting Account - MsituGuard',
            message=f'Hello {user.first_name},\n\nThank you for contributing to Kenya\'s 15 billion trees initiative! Please verify your account: {verification_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Verification email failed: {e}")

def verify_tree_planting_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            
            return render(request, 'App/verification_success.html', {
                'user_name': user.first_name,
                'is_logged_in': request.user.is_authenticated
            })
        else:
            return render(request, 'App/verification_error.html', {
                'error_message': 'Invalid or expired verification link.'
            })
    except Exception as e:
        return render(request, 'App/verification_error.html', {
            'error_message': 'Verification failed. Please try again.'
        })

class PublicTreeFormView(TemplateView):
    template_name = 'App/public_tree_form.html'




@login_required
def export_reports(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="environmental_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Type', 'Location', 'Reporter', 'Status', 'Date', 'Description'])
    
    reports = Report.objects.all().order_by('-timestamp')
    for report in reports:
        writer.writerow([
            report.title,
            report.get_report_type_display(),
            report.location_name,
            report.reporter.username if report.reporter else 'N/A',
            report.status,
            report.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            report.description
        ])
    
    return response

@login_required
def export_tree_data(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tree_plantings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Location', 'Tree Type', 'Number of Trees', 'Planter', 'Status', 'Date', 'Phone Number'])
    
    plantings = TreePlanting.objects.all().order_by('-planted_date')
    for planting in plantings:
        writer.writerow([
            planting.title,
            planting.location_name,
            planting.get_tree_type_display(),
            planting.number_of_trees,
            planting.planter_display_name,
            planting.status,
            planting.planted_date.strftime('%Y-%m-%d'),
            planting.phoneNumber
        ])
    
    return response



class TreePredictionView(TemplateView):
    template_name = 'App/tree_prediction.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add prediction history for logged-in users
        if self.request.user.is_authenticated:
            predictions = TreePrediction.objects.filter(
                user=self.request.user
            ).order_by('-created_at')[:5]
            
            # Add percentage calculation to each prediction
            for prediction in predictions:
                prediction.survival_percentage = round(prediction.survival_probability * 100, 1)
            
            context['prediction_history'] = predictions
            context['total_predictions'] = TreePrediction.objects.filter(
                user=self.request.user
            ).count()
        else:
            context['prediction_history'] = []
            context['total_predictions'] = 0
        
        # Add tree registration link (landing page with Individual/Organization choice)
        context['tree_registration_url'] = '/tree-registration/'
        
        return context

class PlatformRevenueView(LoginRequiredMixin, TemplateView):
    template_name = 'App/platform_revenue.html'
    login_url = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        # Only admin can access platform revenue dashboard
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Carbon credit transactions
        all_transactions = CarbonTransaction.objects.all()
        user_sales = all_transactions.filter(transaction_type='sell')  # Users selling to platform
        
        # Calculate actual platform revenue (only from completed user sales)
        total_user_sales = sum(t.amount for t in user_sales)  # tonnes bought from users
        
        # Revenue calculations (KES) - Platform acts as marketplace with higher corporate rates
        user_payments = total_user_sales * 300  # Platform pays users KES 300/tonne
        corporate_revenue = total_user_sales * 1000  # Platform sells same credits to corporates at KES 1000/tonne
        gross_profit = corporate_revenue - user_payments  # KES 700 margin per tonne
        
        # Organization verification payments
        verified_reports = Report.objects.filter(status='verified').count()
        verified_trees = TreePlanting.objects.filter(status='verified').count()
        org_payments = (verified_reports + verified_trees) * 5  # KES 5 per verification
        
        # Net platform profit
        net_profit = gross_profit - org_payments
        
        # Add margin calculation to transactions
        recent_transactions = all_transactions.order_by('-created_at')[:10]
        for transaction in recent_transactions:
            if transaction.transaction_type == 'sell':
                transaction.platform_margin = transaction.amount * 700  # KES 700 margin per tonne
            else:
                transaction.platform_margin = 0
        
        context.update({
            'total_user_sales': total_user_sales,
            'user_payments': user_payments,
            'corporate_revenue': corporate_revenue,
            'gross_profit': gross_profit,
            'org_payments': org_payments,
            'net_profit': net_profit,
            'verified_reports': verified_reports,
            'verified_trees': verified_trees,
            'profit_margin': round((gross_profit / corporate_revenue * 100) if corporate_revenue > 0 else 0, 1),
            'recent_transactions': recent_transactions,
            'has_corporate_sales': total_user_sales > 0  # Only show corporate revenue if there are actual sales
        })
        
        return context

from .utils import get_county_environment

def recommend_species(request):
    #from a form
    county_name = request.GET.get("county")  
    #Use env_data to fetch species, playbook, andprediction inputs
    env_data = get_county_environment(county_name)
    
    ...





