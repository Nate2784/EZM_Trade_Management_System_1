from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from .models import Product, Stock
from .forms import ProductForm, StockCreateForm, StockUpdateForm

# --- Custom Permission Mixins ---

class StoreOwnerMixin(UserPassesTestMixin):
    """Limits access to Store Owners only."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'head_manager'

class ManagerAndOwnerMixin(UserPassesTestMixin):
    """Limits access to Store Owners and Store Managers."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['head_manager', 'store_manager']

class ManagerOnlyMixin(UserPassesTestMixin):
    """Limits access to Store Managers only."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'store_manager'

class ObjectManagerRequiredMixin(UserPassesTestMixin):
    """
    Limits access to the Store Owner or the specific Store Manager of the object.
    Used for updating a specific stock item.
    """
    def test_func(self):
        user = self.request.user
        if user.role == 'head_manager':
            return True  # Store owner can edit any stock
        
        obj = self.get_object() # Gets the Stock instance
        
        if user.role == 'store_manager' and hasattr(obj, 'store'):
            return obj.store.manager == user # Is the user the manager of this stock's store?
        return False

# --- Product Views (Catalog Management) ---

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'

class ProductCreateView(LoginRequiredMixin, ManagerAndOwnerMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/form_template.html'
    extra_context = {'title': 'Create New Product'}
    success_url = reverse_lazy('product_list')

class ProductUpdateView(LoginRequiredMixin, ManagerAndOwnerMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/form_template.html'
    extra_context = {'title': 'Edit Product'}
    success_url = reverse_lazy('product_list')

class ProductDeleteView(LoginRequiredMixin, StoreOwnerMixin, DeleteView):
    model = Product
    template_name = 'inventory/confirm_delete_template.html'
    extra_context = {'title': 'Delete Product'}
    success_url = reverse_lazy('product_list')


# --- Stock Views (Inventory Management) ---

class StockListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = 'inventory/stock_list.html'
    context_object_name = 'stock_levels'

    def get_queryset(self):
        """
        Overrides the default queryset to filter stock based on user role and the correct models.
        """
        user = self.request.user
        
        if user.role == 'head_manager':
            return Stock.objects.all().select_related('product', 'store')
        
        elif user.role == 'store_manager':
            # --- CORRECTED LOGIC ---
            # We now get the store from the manager's assignment object: user.managed_store.store
            if hasattr(user, 'managed_store'):
                return Stock.objects.filter(store=user.managed_store.store).select_related('product', 'store')
        
        elif user.role == 'cashier':
            # --- CORRECTED LOGIC ---
            # We do the same for the cashier's assignment object: user.cashier_store.store
             if hasattr(user, 'cashier_store'):
                return Stock.objects.filter(store=user.cashier_store.store).select_related('product', 'store')
        
        # Return an empty list if the user has no role or assigned store
        return Stock.objects.none()

class StockCreateView(LoginRequiredMixin, ManagerOnlyMixin, CreateView):
    model = Stock
    form_class = StockCreateForm
    template_name = 'inventory/form_template.html'
    extra_context = {'title': 'Add New Stock Item'}
    success_url = reverse_lazy('stock_list')

    def form_valid(self, form):
        # Assign the stock to the manager's store automatically before saving.
        form.instance.store = self.request.user.managed_store
        
        # Prevent creating a duplicate stock item
        product = form.cleaned_data.get('product')
        if Stock.objects.filter(store=form.instance.store, product=product).exists():
            messages.error(self.request, f"{product.name} is already stocked in your store. Please update the existing record instead.")
            return redirect('stock_list')

        messages.success(self.request, f"Successfully added {product.name} to your store's inventory.")
        return super().form_valid(form)

class StockUpdateView(LoginRequiredMixin, ObjectManagerRequiredMixin, UpdateView):
    model = Stock
    form_class = StockUpdateForm
    template_name = 'inventory/form_template.html'
    extra_context = {'title': 'Update Stock'}
    success_url = reverse_lazy('stock_list')

class StockDeleteView(LoginRequiredMixin, StoreOwnerMixin, DeleteView):
    model = Stock
    template_name = 'inventory/confirm_delete_template.html'
    extra_context = {'title': 'Delete Stock Record'}
    success_url = reverse_lazy('stock_list')