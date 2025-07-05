from django.db import models
from users.models import CustomUser
from transactions.models import Transaction

class Store(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, default='')
    store_manager = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_store')

    def __str__(self):
        return self.name

class Order(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # items = models.ManyToManyField('Inventory.Product', related_name='store_orders') # Remove this line
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True) # Add this line

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username}"

class FinancialRecord(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    cashier = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    record_type = models.CharField(max_length=50)  # e.g., 'revenue', 'expense'

    def __str__(self):
        return f"{self.record_type} - {self.amount} - {self.timestamp}"

class StoreCashier(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    cashier = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.cashier.username} - {self.store.name}"