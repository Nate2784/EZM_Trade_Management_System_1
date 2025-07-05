from django.shortcuts import render, redirect
from store.models import StoreCashier
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .forms import CustomLoginForm, EditProfileForm, ChangePasswordForm
from .models import CustomUser
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.contrib import messages
import logging
logger = logging.getLogger(__name__)
try:
    from users.templatetags.users_utils import send_otp_email
except ImportError as e:
    logger.error(f"Could not import users.templatetags.users_utils: {e}")
    raise
from django.shortcuts import redirect
from django.conf import settings
from django.core.mail import EmailMessage
import threading

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_otp_email(user):
    subject = "Welcome to EZM Trade — Verify Your Email"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    context = {
        'username': user.username,
        'otp': user.otp_code,
    }

    text_content = f"Hi {user.username},\\nWelcome to EZM Trade!\\nYour OTP code is: {user.otp_code}"
    html_content = render_to_string('users/email_otp.html', context)

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login
from .forms import CustomLoginForm
from store.models import Store
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

def login_view(request):
    if request.user.is_authenticated:
        user = request.user
        if getattr(user, 'is_verified', False):
            # Verified users go to their dashboard pages
            if user.is_superuser or user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'head_manager':
                return redirect('head_manager_page')
            elif user.role == 'store_manager':
                return redirect('store_manager_page')
         
            elif user.role == 'cashier':
                if user.store:
                    return redirect('cashier_dashboard')
                else:
                    return redirect('cashier_page')
            else:
                messages.warning(request, "No role assigned. Contact admin.")
                return redirect('login')



    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if not user.is_active:
                messages.error(request, "Your account is inactive. Please contact the administrator.")
                return redirect('login')

            login(request, user)
            if user.is_first_login:
                return redirect('change_password')
            elif user.role == 'admin':
                    return redirect('admin_dashboard')
            elif user.role == 'head_manager':
                    return redirect('head_manager_settings')

            elif user.role == 'store_manager':
                try:
                    store = Store.objects.get(store_manager=user)
                    return redirect('store_manager_page')
                except Store.DoesNotExist:
                    messages.warning(request, "You are not assigned to manage any store.")
                    return redirect('login')
            elif user.role == 'cashier':
                # Check if cashier is assigned to a store
                if user.store:
                    return redirect('cashier_dashboard')
                else:
                    messages.warning(request, "You are not assigned to any store. Contact your manager.")
                    return redirect('login')

                

            else:
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'head_manager':
                    return redirect('head_manager_page')
                elif user.role == 'store_manager':
                    try:
                        store = Store.objects.get(store_manager=user)
                        return redirect('store_manager_page')
                    except Store.DoesNotExist:
                        messages.warning(request, "You are not assigned to manage any store.")
                        return redirect('login')
                elif user.role == 'cashier':
                    return redirect('cashier_page')
                else:
                    messages.warning(request, "No role assigned. Contact admin.")
                    return redirect('login')
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = CustomLoginForm()

    return render(request, 'users/login.html', {'form': form})

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('login')

# Custom CSRF failure view
from django.views.decorators.csrf import requires_csrf_token
from django.template import RequestContext
from django.http import HttpResponseForbidden

@requires_csrf_token
def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view that redirects to login with an error message
    """
    messages.error(request, "Your session has expired. Please log in again.")
    return redirect('login')

from django.shortcuts import render
from django.contrib.auth import get_user_model

User = get_user_model()
@login_required
def admin_dashboard(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()

    users = User.objects.order_by('-date_joined')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'users': users,
    }
    return render(request, 'mainpages/admin_dashboard.html', context)

@login_required
def head_manager_page(request):
    if request.user.role != 'head_manager':
        messages.warning(request, "Access denied. You don't have permission to access this page.")
        return redirect('login')

    stores = Store.objects.all().select_related('store_manager')

    return render(request, 'mainpages/head_manager_page.html', {
        'stores': stores
    })

@login_required
def store_manager_page(request):
    store = None
    try:
        store = Store.objects.get(store_manager=request.user)
    except Store.DoesNotExist:
        messages.warning(request, "You are not assigned to manage any store.")
        return redirect('admin_dashboard')

    cashier_assignment = None
    if store:
        cashier_assignment = StoreCashier.objects.filter(store=store, is_active=True).first()

    return render(request, 'mainpages/store_manager_page.html', {
        'store': store,
        'cashier_assignment': cashier_assignment
    })
from store.models import Order
from transactions.models import Transaction

@login_required
def cashier_page(request):
    # Check if user is a cashier
    if request.user.role != 'cashier':
        messages.error(request, "Access denied. Cashier role required.")
        return redirect('login')

    # Get transactions for this cashier's store if assigned
    transactions = []
    if request.user.store:
        transactions = Transaction.objects.filter(
            store=request.user.store,
            transaction_type='sale'
        ).order_by('-timestamp')[:10]

    return render(request, 'mainpages/cashier_page.html', {
        'transactions': transactions,
        'has_store': bool(request.user.store)
    })

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from .forms import ChangeUserRoleForm, CustomUserCreationFormAdmin
from django.core.paginator import Paginator

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@user_passes_test(is_admin)
def manage_users(request):
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    page_number = request.GET.get('page')

    users = User.objects.all()

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users.order_by('username'), 5)
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
        'search_query': search_query,
        'role_filter': role_filter,
        'total_users': users.count(),
        'is_admin': role_filter == 'admin',
        'is_head_manager': role_filter == 'head_manager',
        'is_store_manager': role_filter == 'store_manager',
        'is_cashier': role_filter == 'cashier',
    }
    logger.debug(f"page_obj: {page_obj}")
    logger.debug(f"page_obj.paginator.page_range: {page_obj.paginator.page_range}")
    return render(request, 'admin/manage_users.html', context)

@user_passes_test(is_admin)
def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone_number = request.POST.get('phone_number')

        context = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number,
            'role': role
        }

        if not all([username, first_name, last_name, email, password, role]):
            messages.error(request, "All required fields must be filled.")
            return render(request, 'admin/create_user.html', context)

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, 'admin/create_user.html', context)

        try:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                role=role,
                phone_number=phone_number,
            )

            subject = "Account Created"
            message = f"Your account has been created.\\n" \
                      f"Username: {user.username}\\n" \
                      f"Password: {password}\\n" \
                      f"Phone Number: {user.phone_number}"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            send_mail(subject, message, from_email, to_email, fail_silently=True)

            messages.success(request, f"User {user.username} created successfully. Email sent with credentials.")
            return redirect('manage_users')
        except Exception as e:
            messages.error(request, f"Error creating user: {e}")
            return render(request, 'admin/create_user.html', context)
    else:
        return render(request, 'admin/create_user.html')

@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('manage_users')

@user_passes_test(is_admin)
def view_user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'admin/user_detail.html', {'user': user})

@user_passes_test(is_admin)
def change_user_role(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = ChangeUserRoleForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('manage_users')
    else:
        form = ChangeUserRoleForm(instance=user)
    return render(request, 'admin/change_user_role.html', {'form': form, 'user': user})

@login_required
def admin_settings(request):
    if request.user.role == 'admin':
        return render(request, 'admin/admin_settings.html')
    elif request.user.role == 'head_manager':
        return redirect('head_manager_settings')
    elif request.user.role == 'store_manager':
        return redirect('store_manager_settings')
    elif request.user.role == 'cashier':
        return redirect('cashier_settings')
    else:
        messages.warning(request, "No role assigned. Contact admin.")
        return redirect('login')

@login_required
def admin_edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('admin_settings')
        else:
            messages.error(request, 'Error updating profile.')
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def admin_change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data['old_password']
            new_password1 = form.cleaned_data['new_password1']
            if request.user.check_password(old_password):
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')
                return redirect('admin_settings')
            else:
                messages.error(request, 'Incorrect old password.')
    else:
        form = ChangePasswordForm()
    return render(request, 'users/change_password.html', {'form': form})

@login_required
def head_manager_settings(request):
    # Mark user as no longer first login after visiting settings
    if request.user.is_first_login:
        request.user.is_first_login = False
        request.user.save()
        messages.info(request, "Welcome! Please update your password and profile information.")

    return render(request, 'mainpages/head_manager_settings.html')

@login_required
def store_manager_settings(request):
    return render(request, 'mainpages/store_manager_settings.html')

@login_required
def cashier_settings(request):
    return render(request, 'mainpages/cashier_settings.html')


class CustomPasswordChangeView(PasswordChangeView):
    """
    Custom Password Change View that redirects users to their appropriate dashboard
    based on their role after successful password change.
    """
    template_name = 'users/password_change.html'

    def get_success_url(self):
        """
        Redirect to the appropriate dashboard based on user role
        """
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return reverse_lazy('admin_dashboard')
        elif user.role == 'head_manager':
            return reverse_lazy('head_manager_page')
        elif user.role == 'store_manager':
            return reverse_lazy('store_manager_page')
        elif user.role == 'cashier':
            return reverse_lazy('cashier_page')
        else:
            # Default fallback
            return reverse_lazy('login')
