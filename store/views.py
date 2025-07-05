from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from Inventory.models import Product, Stock
from transactions.models import Transaction, Receipt, Order as TransactionOrder
from .models import Order, FinancialRecord, Store, StoreCashier
from users.models import CustomUser
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML  # Make sure you have WeasyPrint installed
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
import json

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

from .forms import StoreForm, AssignCashierForm

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


# ============ CASHIER ORDER SYSTEM ============

@login_required
def cashier_dashboard(request):
    """
    Enhanced cashier dashboard with order management capabilities
    """
    if request.user.role != 'cashier':
        messages.error(request, "Access denied. Cashier role required.")
        return redirect('login')

    if not request.user.store:
        messages.error(request, "You are not assigned to any store. Contact your manager.")
        return redirect('login')

    # Get recent transactions for this cashier
    recent_transactions = Transaction.objects.filter(
        store=request.user.store,
        transaction_type='sale'
    ).order_by('-timestamp')[:10]

    # Get pending orders (if any)
    pending_orders = Order.objects.filter(
        customer=request.user,
        transaction__isnull=True
    ).order_by('-created_at')

    # Get store's available products
    available_products = Stock.objects.filter(
        store=request.user.store,
        quantity__gt=0
    ).select_related('product')

    context = {
        'recent_transactions': recent_transactions,
        'pending_orders': pending_orders,
        'available_products': available_products,
        'store': request.user.store,
    }

    return render(request, 'store/cashier_dashboard.html', context)


@login_required
def initiate_order(request):
    """
    Cashier initiates a new order - creates a shopping cart session
    """
    if request.user.role != 'cashier':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if not request.user.store:
        return JsonResponse({'error': 'No store assigned'}, status=400)

    # Initialize or get existing cart from session
    if 'cart' not in request.session:
        request.session['cart'] = {
            'items': [],
            'total': 0,
            'created_at': timezone.now().isoformat(),
            'cashier_id': request.user.id,
            'store_id': request.user.store.id
        }
        request.session.modified = True

    # Get available products for this store
    available_products = Stock.objects.filter(
        store=request.user.store,
        quantity__gt=0
    ).select_related('product').values(
        'product__id', 'product__name', 'product__price',
        'quantity', 'selling_price'
    )

    context = {
        'available_products': list(available_products),
        'cart': request.session.get('cart', {}),
        'store': request.user.store,
    }

    return render(request, 'store/initiate_order.html', context)


@login_required
def add_to_cart(request):
    """
    Add product to cart (AJAX endpoint)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if request.user.role != 'cashier':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        # Validate product and stock
        stock = Stock.objects.get(
            product_id=product_id,
            store=request.user.store
        )

        if stock.quantity < quantity:
            return JsonResponse({
                'error': f'Insufficient stock. Available: {stock.quantity}'
            }, status=400)

        # Initialize cart if not exists
        if 'cart' not in request.session:
            request.session['cart'] = {
                'items': [],
                'total': 0,
                'created_at': timezone.now().isoformat(),
                'cashier_id': request.user.id,
                'store_id': request.user.store.id
            }

        cart = request.session['cart']

        # Check if product already in cart
        existing_item = None
        for item in cart['items']:
            if item['product_id'] == product_id:
                existing_item = item
                break

        if existing_item:
            # Update quantity
            new_quantity = existing_item['quantity'] + quantity
            if stock.quantity < new_quantity:
                return JsonResponse({
                    'error': f'Total quantity exceeds stock. Available: {stock.quantity}'
                }, status=400)
            existing_item['quantity'] = new_quantity
            existing_item['subtotal'] = float(Decimal(str(stock.selling_price)) * new_quantity)
        else:
            # Add new item
            cart['items'].append({
                'product_id': product_id,
                'product_name': stock.product.name,
                'price': float(stock.selling_price),
                'quantity': quantity,
                'subtotal': float(Decimal(str(stock.selling_price)) * quantity)
            })

        # Recalculate total
        cart['total'] = sum(item['subtotal'] for item in cart['items'])
        request.session['cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'cart': cart,
            'message': f'Added {quantity} x {stock.product.name} to cart'
        })

    except Stock.DoesNotExist:
        return JsonResponse({'error': 'Product not found in store'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def remove_from_cart(request):
    """
    Remove product from cart (AJAX endpoint)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        cart = request.session.get('cart', {'items': [], 'total': 0})
        cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
        cart['total'] = sum(item['subtotal'] for item in cart['items'])

        request.session['cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'cart': cart,
            'message': 'Item removed from cart'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def complete_order(request):
    """
    Complete the order - create transaction, receipt, and clear cart
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if request.user.role != 'cashier':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        payment_type = data.get('payment_type', 'cash')
        discount_percent = max(0, min(100, float(data.get('discount', 0))))  # Ensure discount is between 0-100
        is_taxable = data.get('taxable', False)
        customer_name = data.get('customer_name', 'Walk-in Customer')
        customer_phone = data.get('customer_phone', '')

        cart = request.session.get('cart')
        if not cart or not cart.get('items'):
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        with transaction.atomic():
            # Calculate totals - convert all to Decimal for consistency
            try:
                subtotal = Decimal(str(sum(item['subtotal'] for item in cart['items'])))
                discount_amount = subtotal * (Decimal(str(discount_percent)) / Decimal('100'))
                taxable_amount = subtotal - discount_amount
                tax_amount = taxable_amount * Decimal('0.05') if is_taxable else Decimal('0')
                total_amount = taxable_amount + tax_amount
            except (ValueError, TypeError, KeyError) as calc_error:
                return JsonResponse({'error': f'Calculation error: {str(calc_error)}'}, status=400)

            # Create main transaction
            transaction_obj = Transaction.objects.create(
                transaction_type='sale',
                quantity=sum(item['quantity'] for item in cart['items']),
                total_amount=total_amount,
                store=request.user.store,
                payment_type=payment_type
            )

            # Create receipt
            receipt = Receipt.objects.create(
                transaction=transaction_obj,
                total_amount=total_amount,
                customer_name=customer_name,
                customer_phone=customer_phone,
                subtotal=subtotal,
                discount_amount=discount_amount,
                discount_percent=Decimal(str(discount_percent)),
                tax_amount=tax_amount
            )

            # Create order entries and update stock
            order_items = []
            for item in cart['items']:
                # Get stock and update quantity
                stock = Stock.objects.select_for_update().get(
                    product_id=item['product_id'],
                    store=request.user.store
                )

                if stock.quantity < item['quantity']:
                    raise ValueError(f"Insufficient stock for {item['product_name']}")

                stock.quantity -= item['quantity']
                stock.save()

                # Create transaction order
                order = TransactionOrder.objects.create(
                    receipt=receipt,
                    transaction=transaction_obj,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price_at_time_of_sale=Decimal(str(item['price']))
                )

                order_items.append({
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'subtotal': item['subtotal']
                })

            # Create financial record
            FinancialRecord.objects.create(
                store=request.user.store,
                cashier=request.user,
                amount=total_amount,
                record_type='revenue'
            )

            # Clear cart
            if 'cart' in request.session:
                del request.session['cart']
                request.session.modified = True

            return JsonResponse({
                'success': True,
                'transaction_id': transaction_obj.id,
                'receipt_id': receipt.id,
                'total_amount': float(total_amount),
                'order_items': order_items,
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'payment_type': payment_type,
                'discount_amount': float(discount_amount),
                'discount_percent': discount_percent,
                'tax_amount': float(tax_amount),
                'subtotal': float(subtotal),
                'message': 'Order completed successfully',
                'receipt_url': f'/stores/receipt/{receipt.id}/',
                'receipt_pdf_url': f'/stores/receipt/{receipt.id}/pdf/',
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Order completion failed: {str(e)}'}, status=500)


@login_required
def generate_receipt_pdf(request, receipt_id):
    """
    Generate and download receipt as PDF
    """
    if request.user.role != 'cashier':
        return HttpResponse("Unauthorized", status=403)

    try:
        receipt = get_object_or_404(Receipt, id=receipt_id)
        transaction_obj = receipt.transaction

        # Verify cashier has access to this receipt
        if transaction_obj.store != request.user.store:
            return HttpResponse("Access denied", status=403)

        # Get order items
        order_items = TransactionOrder.objects.filter(
            transaction=transaction_obj
        ).select_related('receipt', 'product')

        # Calculate breakdown
        subtotal = sum(item.quantity * item.price_at_time_of_sale for item in order_items)

        # Add subtotal to each item for template
        for item in order_items:
            item.subtotal = item.quantity * item.price_at_time_of_sale

        context = {
            'receipt': receipt,
            'transaction': transaction_obj,
            'order_items': order_items,
            'subtotal': receipt.subtotal,
            'store': transaction_obj.store,
            'cashier': request.user,
            'timestamp': transaction_obj.timestamp,
            'customer_name': receipt.customer_name,
            'customer_phone': receipt.customer_phone,
            'discount_amount': receipt.discount_amount,
            'discount_percent': receipt.discount_percent,
            'tax_amount': receipt.tax_amount,
            'payment_method': transaction_obj.payment_type,
        }

        # Render HTML template
        receipt_html = render_to_string('store/receipt_pdf_template.html', context)

        # Generate PDF
        pdf = HTML(string=receipt_html).write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_id}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Error generating receipt: {str(e)}")
        return redirect('cashier_dashboard')


@login_required
def view_receipt(request, receipt_id):
    """
    View receipt details in browser
    """
    if request.user.role != 'cashier':
        messages.error(request, "Access denied")
        return redirect('login')

    try:
        receipt = get_object_or_404(Receipt, id=receipt_id)
        transaction_obj = receipt.transaction

        # Verify access
        if transaction_obj.store != request.user.store:
            messages.error(request, "Access denied to this receipt")
            return redirect('cashier_dashboard')

        # Get order items
        order_items = TransactionOrder.objects.filter(
            transaction=transaction_obj
        ).select_related('receipt', 'product')

        # Add subtotal to each item for template
        for item in order_items:
            item.subtotal = item.quantity * item.price_at_time_of_sale

        context = {
            'receipt': receipt,
            'transaction': transaction_obj,
            'order_items': order_items,
            'store': transaction_obj.store,
            'customer_name': receipt.customer_name,
            'customer_phone': receipt.customer_phone,
        }

        return render(request, 'store/view_receipt.html', context)

    except Exception as e:
        messages.error(request, f"Error viewing receipt: {str(e)}")
        return redirect('cashier_dashboard')


@login_required
def get_cart_status(request):
    """
    Get current cart status (AJAX endpoint)
    """
    cart = request.session.get('cart', {'items': [], 'total': 0})
    return JsonResponse({'cart': cart})


@login_required
def email_receipt(request, receipt_id):
    """
    Email receipt to customer
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if request.user.role != 'cashier':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        customer_email = data.get('email', '').strip()

        if not customer_email:
            return JsonResponse({'error': 'Email address is required'}, status=400)

        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(customer_email)
        except ValidationError:
            return JsonResponse({'error': 'Invalid email address'}, status=400)

        receipt = get_object_or_404(Receipt, id=receipt_id)
        transaction_obj = receipt.transaction

        # Verify cashier has access to this receipt
        if transaction_obj.store != request.user.store:
            return JsonResponse({'error': 'Access denied'}, status=403)

        # Get order items
        order_items = TransactionOrder.objects.filter(
            transaction=transaction_obj
        ).select_related('receipt', 'product')

        # Calculate breakdown
        subtotal = sum(item.quantity * item.price_at_time_of_sale for item in order_items)

        # Add subtotal to each item for template
        for item in order_items:
            item.subtotal = item.quantity * item.price_at_time_of_sale

        context = {
            'receipt': receipt,
            'transaction': transaction_obj,
            'order_items': order_items,
            'subtotal': receipt.subtotal,
            'store': transaction_obj.store,
            'cashier': request.user,
            'timestamp': transaction_obj.timestamp,
            'customer_name': receipt.customer_name,
            'customer_phone': receipt.customer_phone,
            'discount_amount': receipt.discount_amount,
            'discount_percent': receipt.discount_percent,
            'tax_amount': receipt.tax_amount,
            'payment_method': transaction_obj.payment_type,
        }

        # Generate PDF
        receipt_html = render_to_string('store/receipt_pdf_template.html', context)
        pdf = HTML(string=receipt_html).write_pdf()

        # Send email
        from django.core.mail import EmailMessage
        from django.conf import settings

        subject = f'Receipt from {transaction_obj.store.name} - #{receipt.id}'
        message = f"""
Dear Customer,

Thank you for your purchase at {transaction_obj.store.name}!

Please find your receipt attached to this email.

Transaction Details:
- Receipt #: {receipt.id}
- Date: {transaction_obj.timestamp.strftime('%B %d, %Y at %I:%M %p')}
- Total Amount: ${receipt.total_amount}
- Payment Method: {transaction_obj.get_payment_type_display()}

We appreciate your business and look forward to serving you again.

Best regards,
{transaction_obj.store.name}
Phone: {transaction_obj.store.phone_number}
        """.strip()

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer_email],
        )

        # Attach PDF
        email.attach(
            f'receipt_{receipt.id}.pdf',
            pdf,
            'application/pdf'
        )

        # Send email in background thread
        from threading import Thread
        def send_email():
            try:
                email.send()
            except Exception as e:
                print(f"Failed to send email: {e}")

        Thread(target=send_email).start()

        return JsonResponse({
            'success': True,
            'message': f'Receipt has been sent to {customer_email}'
        })

    except Exception as e:
        return JsonResponse({'error': f'Failed to send email: {str(e)}'}, status=500)


# ============ STORE MANAGER CASHIER ASSIGNMENT ============

@login_required
def assign_cashier(request, store_id=None):
    """
    Store manager assigns a cashier to their store
    """
    if request.user.role != 'store_manager':
        messages.error(request, "Access denied. Store manager role required.")
        return redirect('login')

    # Get the store managed by this user
    try:
        if store_id:
            store = get_object_or_404(Store, id=store_id, store_manager=request.user)
        else:
            store = Store.objects.get(store_manager=request.user)
    except Store.DoesNotExist:
        messages.error(request, "You are not assigned to manage any store.")
        return redirect('store_manager_page')

    if request.method == 'POST':
        form = AssignCashierForm(request.POST)
        if form.is_valid():
            cashier = form.cleaned_data['cashier']

            # Assign cashier to store
            cashier.store = store
            cashier.save()

            # Create or update StoreCashier record
            store_cashier, created = StoreCashier.objects.get_or_create(
                store=store,
                cashier=cashier,
                defaults={'is_active': True}
            )
            if not created:
                store_cashier.is_active = True
                store_cashier.save()

            messages.success(request, f"Successfully assigned {cashier.get_full_name() or cashier.username} as cashier for {store.name}")
            return redirect('store_manager_page')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AssignCashierForm()

    # Get currently assigned cashiers
    assigned_cashiers = CustomUser.objects.filter(
        store=store,
        role='cashier',
        is_active=True
    )

    context = {
        'form': form,
        'store': store,
        'assigned_cashiers': assigned_cashiers,
    }

    return render(request, 'store/assign_cashier.html', context)


@login_required
def remove_cashier(request, cashier_id):
    """
    Store manager removes a cashier from their store
    """
    if request.user.role != 'store_manager':
        messages.error(request, "Access denied. Store manager role required.")
        return redirect('login')

    try:
        store = Store.objects.get(store_manager=request.user)
        cashier = get_object_or_404(CustomUser, id=cashier_id, store=store, role='cashier')

        # Remove cashier from store
        cashier.store = None
        cashier.save()

        # Deactivate StoreCashier record
        StoreCashier.objects.filter(store=store, cashier=cashier).update(is_active=False)

        messages.success(request, f"Successfully removed {cashier.get_full_name() or cashier.username} from {store.name}")

    except Store.DoesNotExist:
        messages.error(request, "You are not assigned to manage any store.")
    except Exception as e:
        messages.error(request, f"Error removing cashier: {str(e)}")

    return redirect('store_manager_page')


@login_required
def manage_cashiers(request):
    """
    Store manager view to manage all cashiers for their store
    """
    if request.user.role != 'store_manager':
        messages.error(request, "Access denied. Store manager role required.")
        return redirect('login')

    try:
        store = Store.objects.get(store_manager=request.user)
    except Store.DoesNotExist:
        messages.error(request, "You are not assigned to manage any store.")
        return redirect('store_manager_page')

    # Get assigned cashiers
    assigned_cashiers = CustomUser.objects.filter(
        store=store,
        role='cashier',
        is_active=True
    )

    # Get available cashiers (not assigned to any store)
    available_cashiers = CustomUser.objects.filter(
        role='cashier',
        is_active=True,
        store__isnull=True
    )

    context = {
        'store': store,
        'assigned_cashiers': assigned_cashiers,
        'available_cashiers': available_cashiers,
    }

    return render(request, 'store/manage_cashiers.html', context)
