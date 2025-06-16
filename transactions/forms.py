from django import forms
from Inventory.models import Product
from store.models import Store

class SaleItemForm(forms.Form):
    """
    This is the form for a single line item in a sale.
    We will use a FormSet to have multiple instances of this on one page.
    """
    product = forms.ModelChoiceField( 
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control product-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control quantity-input', 'value': 1})
    )

# A FormSet is a factory that creates a class from our SaleItemForm
# 'extra=1' means it will show 1 extra empty form by default.
SaleItemFormSet = forms.formset_factory(SaleItemForm, extra=1)

class SaleForm(forms.Form):
    """
    This is the main form that will contain the store selection
    and the FormSet for all the items.
    """
    store = forms.ModelChoiceField(
        queryset=Store.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )