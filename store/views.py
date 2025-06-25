from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from Inventory.models import Product, Stock
from transactions.models import Transaction
from .models import Order, FinancialRecord
from users.models import CustomUser
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML  # Make sure you have WeasyPrint installed

@login_required
def process_sale(request):
    products = Product.objects.all()
    if request.method == 'POST':
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        discount = float(request.POST.get('discount'))
        taxable = request.POST.get('taxable') == 'on'
        payment_type = request.POST.get('payment_type')

        total = 0
        order_items = []

        try:
            with transaction.atomic():
                # Create Order
                order = Order.objects.create(
                    customer=request.user,  # Assuming the logged-in user is the customer
                    total_amount=0 # Initialize total amount to 0
                )

                # Reduce product stock and calculate item totals
                for product_id, quantity in zip(product_ids, quantities):
                    product = get_object_or_404(Product, pk=product_id)
                    quantity = int(quantity)

                    # Reduce product stock
                    try:
                        stock = Stock.objects.get(product=product, store=request.user.store)
                    except Stock.DoesNotExist:
                        raise ValueError(f"{product.name} not in stock")
                    if stock.quantity < quantity:
                        raise ValueError(f"Not enough stock for {product.name}")
                    stock.quantity -= quantity
                    stock.save()

                    # Calculate item total
                    item_total = product.price * quantity
                    order_items.append((product, quantity, item_total))
                    total += item_total

                # Calculate totals
                discount_amount = total * (discount / 100)
                total -= discount_amount
                tax = total * 0.05 if taxable else 0
                total += tax

                order.total_amount = total
                order.save()

                # Create Transaction
                transaction_obj = Transaction.objects.create(
                    sale_type='POS',
                    quantity=sum(int(q) for q in quantities),
                    user=request.user,
                    total_amount=total,
                    store=request.user.store
                )

                order.transaction = transaction_obj # Associate the transaction with the order
                order.save()

                # Create Financial Record
                FinancialRecord.objects.create(
                    store=request.user.store,
                    cashier=request.user,
                    amount=total,
                    record_type='revenue'
                )

                # Generate Receipt (basic HTML)
                receipt_html = render_to_string('store/receipt_template.html', {'order': order, 'total': total, 'tax': tax, 'discount': discount_amount, 'payment_type': payment_type, 'order_items': order_items})
                # Generate PDF
                # html = HTML(string=receipt_html)
                # pdf_file = html.write_pdf()
                # response = HttpResponse(pdf_file, content_type='application/pdf')
                # response['Content-Disposition'] = 'filename="receipt.pdf"'
                # return HttpResponse(receipt_html)

        except ValueError as e:
            return render(request, 'store/process_sale.html', {'products': products, 'error': str(e)})

    return render(request, 'store/process_sale.html', {'products': products})

def get_product_price(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    return JsonResponse({'price': product.price})

from django.shortcuts import render

from .forms import StoreForm

def create_store(request):
    if request.method == 'POST':
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save()
            return redirect('head_manager_page')  # Redirect to store owner page after successful creation
    else:
        form = StoreForm()
    return render(request, 'store/create_store.html', {'form': form})

from django.shortcuts import render, get_object_or_404
from .models import Store

import logging
from .forms import AssignManagerForm

logger = logging.getLogger(__name__)

@login_required
def manage_store(request, store_id):
    store = get_object_or_404(Store, pk=store_id)
    if request.method == 'POST':
        form = AssignManagerForm(request.POST)
        if form.is_valid():
            manager = form.cleaned_data['manager']
            logger.info(f"Assigning manager {manager.username} to store {store.name}")
            store.store_manager = manager
            store.save()
            manager.store = store
            manager.save()
            logger.info(f"Successfully assigned manager {manager.username} to store {store.name}")
            from django.contrib import messages
            messages.success(request, f"Successfully assigned {manager.username} to {store.name}")
            return redirect('head_manager_page')
        else:
            logger.warning(f"Invalid form data: {form.errors}")
    else:
        form = AssignManagerForm()
    return render(request, 'store/manage_store.html', {'store': store, 'form': form})
