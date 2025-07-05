# users/urls.py
from django.urls import path
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from .views import login_view, logout_view, admin_dashboard, store_manager_page, cashier_page, head_manager_page, manage_users, toggle_user_status, change_user_role, view_user_detail, create_user, admin_settings, admin_edit_profile, admin_change_password, head_manager_settings, store_manager_settings, cashier_settings, CustomPasswordChangeView

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('csrf-failure/', csrf_failure, name='csrf_failure'),

    #admin
     path('admin/manage-users/', manage_users, name='manage_users'),
    path('admin/user/<int:user_id>/toggle-status/', toggle_user_status, name='toggle_user_status'),
    path('admin/user/<int:user_id>/change-role/', change_user_role, name='change_user_role'),
    path('admin/user/<int:user_id>/', view_user_detail, name='view_user_detail'),
    path('admin/create-user/', create_user, name='create_user'),

    # Role-based pages
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('head-manager/', head_manager_page, name='head_manager_page'),
    path('store-manager/', store_manager_page, name='store_manager_page'),
    path('cashier/', cashier_page, name='cashier_page'),
    path('admin/settings/', admin_settings, name='admin_settings'),
    path('admin/profile/edit/', admin_edit_profile, name='admin_edit_profile'),
    path('admin/profile/change-password/', admin_change_password, name='admin_change_password'),
    path('head-manager/settings/', head_manager_settings, name='head_manager_settings'),
    path('store-manager/settings/', store_manager_settings, name='store_manager_settings'),
    path('cashier/settings/', cashier_settings, name='cashier_settings'),

    # Generic password change for all authenticated users
    path('account/password/', CustomPasswordChangeView.as_view(), name='password_change'),

    # Password reset URLs
    path('password-reset/', PasswordResetView.as_view(
        template_name='users/password_reset.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt',
        success_url='/users/password-reset/done/'
    ), name='password_reset'),

    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url='/users/password-reset-complete/'
    ), name='password_reset_confirm'),

    path('password-reset-complete/', PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
]
