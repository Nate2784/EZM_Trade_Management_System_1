from django.urls import path
from . import views

urlpatterns = [
    # ... other URL patterns
    path('process_sale/', views.process_sale, name='process_sale'),
    path('get_product_price/<int:product_id>/', views.get_product_price, name='get_product_price'),
    path('create_store/', views.create_store, name='create_store'),
    path('manage_store/<int:store_id>/', views.manage_store, name='manage_store'),

    # Cashier Order System URLs
    path('cashier/dashboard/', views.cashier_dashboard, name='cashier_dashboard'),
    path('cashier/initiate-order/', views.initiate_order, name='initiate_order'),
    path('cashier/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cashier/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('cashier/complete-order/', views.complete_order, name='complete_order'),
    path('cashier/cart-status/', views.get_cart_status, name='get_cart_status'),
    path('receipt/<int:receipt_id>/', views.view_receipt, name='view_receipt'),
    path('receipt/<int:receipt_id>/pdf/', views.generate_receipt_pdf, name='generate_receipt_pdf'),
    path('receipt/<int:receipt_id>/email/', views.email_receipt, name='email_receipt'),

    # Store Manager Cashier Assignment URLs
    path('manager/assign-cashier/', views.assign_cashier, name='assign_cashier'),
    path('manager/assign-cashier/<int:store_id>/', views.assign_cashier, name='assign_cashier_to_store'),
    path('manager/remove-cashier/<int:cashier_id>/', views.remove_cashier, name='remove_cashier'),
    path('manager/manage-cashiers/', views.manage_cashiers, name='manage_cashiers'),
]