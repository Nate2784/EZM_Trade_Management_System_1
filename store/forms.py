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
        ).exclude(role__in=['head_manager', 'admin'])

from django import forms
from users.models import CustomUser


