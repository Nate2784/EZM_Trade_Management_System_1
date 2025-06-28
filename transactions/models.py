from django.db import models
from django.conf import settings


class Transaction(models.Model):
    """
    Logs every inventory movement, such as sales, restocks, or transfers.
    This provides a complete audit trail.
    """
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('restock', 'Restock'),
        ('transfer', 'Transfer'),
        ('refund', 'Refund'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('mobile', 'Mobile Money'),
        ('bank', 'Bank Transfer'),
       
    ]
    # Use strings 'app_name.ModelName' to define relationships to other apps.
    # product = models.ForeignKey('Inventory.Product', on_delete=models.CASCADE) # Remove this line
    quantity = models.IntegerField(help_text="Quantity of product involved. Can be negative for sales.")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Add this line
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='cash')

    def __str__(self):
        # We use try-except blocks to avoid errors if related objects don't exist yet
        try:
            # product_name = self.product.name # Remove this line
            store_name = self.store.name
            return f'{self.transaction_type} of {self.quantity} at {store_name} via {self.payment_type}' # Update this line
        except (AttributeError,):
            return f'Transaction ID: {self.id}'


class FinancialRecord(models.Model):
    """
    Tracks all revenues and expenses for each store to monitor profitability.
    """
    RECORD_TYPES = [
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, related_name='financial_records')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    record_type = models.CharField(max_length=10, choices=RECORD_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.record_type} of {self.amount} at {self.store.name}'

class Receipt(models.Model):
    """
    Represents a receipt generated for a sales transaction.
    """
    # This relationship is fine as-is because Transaction is defined in the same file.
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, limit_choices_to={'transaction_type': 'sale'})
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Receipt for transaction {self.transaction.id}'

class Order(models.Model):
    """
    Links multiple products and their quantities to a single receipt,
    representing the items in a customer's purchase.
    """
    # This relationship is also fine as Receipt is defined above in the same file.
    # We allow it to be null to handle the workflow where orders are created before the receipt.
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True
    )
    # This must be a string to avoid the circular import with the 'inventory' app.
    # product = models.ForeignKey('Inventory.Product', on_delete=models.CASCADE, related_name='transaction_orders') # Remove this line
    quantity = models.PositiveIntegerField()
    price_at_time_of_sale = models.DecimalField(max_digits=10, decimal_places=2)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='orders', null=True, blank=True) # Add this line

    def __str__(self):
        receipt_id = self.receipt.id if self.receipt else "unassigned"
        return f'{self.quantity} of {self.product.name} for receipt {receipt_id}'