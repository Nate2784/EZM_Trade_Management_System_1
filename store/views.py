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
    if request.user.role != 'cashier':
        return HttpResponse("Unauthorized", status=403)
    
    products = Product.objects.all()
    
    if request.method == 'POST':
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        discount = float(request.POST.get('discount', 0))
        taxable = request.POST.get('taxable') == 'on'
        payment_type = request.POST.get('payment_type', 'cash')

        total = 0
        order_items = []

        try:
            with transaction.atomic():
                # Loop through selected products
                for pid, qty in zip(product_ids, quantities):
                    product = get_object_or_404(Product, pk=pid)
                    qty = int(qty)

                    stock = Stock.objects.get(product=product, store=request.user.store)
                    if stock.quantity < qty:
                        raise ValueError(f"Not enough {product.name} in stock.")
                    stock.quantity -= qty
                    stock.save()

                    item_total = product.price * qty
                    order_items.append((product, qty, item_total))
                    total += item_total

                discount_amt = total * (discount / 100)
                total -= discount_amt
                tax = total * 0.05 if taxable else 0
                total += tax

                # Create Transaction
                transaction_obj = Transaction.objects.create(
                    transaction_type='sale',
                    quantity=sum(int(q) for q in quantities),
                    total_amount=total,
                    store=request.user.store,
                    payment_type=payment_type
                )

                # Create Order entries for each product
                for product, qty, item_total in order_items:
                    Order.objects.create(
                        quantity=qty,
                        price_at_time_of_sale=product.price,
                        transaction=transaction_obj
                    )

                # Create Financial Record
                FinancialRecord.objects.create(
                    store=request.user.store,
                    cashier=request.user,
                    amount=total,
                    record_type='revenue',
                    description=f"POS Sale via {payment_type}"
                )

                # Create Receipt
                receipt = Receipt.objects.create(
                    transaction=transaction_obj,
                    total_amount=total
                )

                # Optional: Generate and return a receipt PDF
                receipt_html = render_to_string('store/receipt_template.html', {
                    'transaction': transaction_obj,
                    'receipt': receipt,
                    'tax': tax,
                    'discount': discount_amt,
                    'payment_type': payment_type,
                    'order_items': order_items,
                })

                pdf = HTML(string=receipt_html).write_pdf()
                return HttpResponse(pdf, content_type='application/pdf')

        except ValueError as e:
            return render(request, 'store/process_sale.html', {
                'products': products,
                'error': str(e)
            })

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
            return redirect('head_manager_page')  # Redirect to haed manager page after successful creation
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
            return redirect('store_owner_page')
        else:
            logger.warning(f"Invalid form data: {form.errors}")
    else:
        form = AssignManagerForm()
    return render(request, 'store/manage_store.html', {'store': store, 'form': form})
