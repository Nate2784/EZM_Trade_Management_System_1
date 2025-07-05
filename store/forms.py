# store/forms.py
from django import forms
from .models import Store

class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['name', 'address', 'phone_number']  # exclude 'owner' to avoid user input


from django import forms
from users.models import CustomUser

class AssignManagerForm(forms.Form):
    manager = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role__in=['store_manager', '']),
        label="Select Manager",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Further refine queryset if needed, e.g., only verified users
        self.fields['manager'].queryset = CustomUser.objects.filter(
            is_active=True,
        ).exclude(role__in=['store_owner', 'admin'])

from django import forms
from users.models import CustomUser
from .models import StoreCashier


class AssignCashierForm(forms.Form):
    cashier = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='cashier', is_active=True, store__isnull=True),
        label="Select Cashier",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Only unassigned cashiers are shown"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show cashiers who are not assigned to any store
        self.fields['cashier'].queryset = CustomUser.objects.filter(
            role='cashier',
            is_active=True,
            store__isnull=True
        )


