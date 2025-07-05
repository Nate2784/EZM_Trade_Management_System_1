from django.shortcuts import render
from django.db.models import F
from Inventory.models import Product, Stock

def analytics_page(request):
    total_products = Product.objects.count()
    low_stock_items = Stock.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    monthly_sales_data = [10, 20, 15, 25, 30, 22, 18, 28, 35, 40, 38, 45]  # Replace with actual data fetching logic

    context = {
        'total_products': total_products,
        'low_stock_items': low_stock_items,
        'monthly_sales_data': monthly_sales_data
    }
    return render(request, 'mainpages/analytics_page.html', context)