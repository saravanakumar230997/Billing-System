from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.mail import send_mail
from .models import Product, Bill, BillItem
from .forms import ProductForm
from django.db import transaction

def billing_page(request):
    products = Product.objects.all()
    denominations = [500, 50, 20, 10, 5, 2, 1]
    return render(request, 'billing_page.html', {'products': products,'denominations': denominations})

@transaction.atomic
def generate_bill(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        denominations = {int(k): int(v) for k, v in request.POST.items() if k.isdigit()}
        paid_amount = float(request.POST.get('paid_amount', 0))

        total_price_without_tax = 0
        total_tax = 0
        bill_items = []

        for product_id, quantity in zip(product_ids, quantities):
            try:
                product = Product.objects.get(product_id=product_id)
                unit_price = product.price
                tax = product.tax_percentage * float(quantity) * unit_price / 100
                purchase_price = unit_price * int(quantity)
                total_price = purchase_price + tax

                total_price_without_tax += purchase_price
                total_tax += tax

                if product.available_stocks < int(quantity):
                    return HttpResponse(f"Not enough stock for {product.name}", status=400)
                product.available_stocks -= int(quantity)
                product.save()

                bill_items.append({
                    'product': product,
                    'quantity': int(quantity),
                    'purchase_price': purchase_price,
                    'tax_amount': tax,
                    'total_price': total_price
                })

            except Product.DoesNotExist:
                return HttpResponse(f"Product with ID {product_id} does not exist.", status=404)

        net_price = total_price_without_tax + total_tax
        balance = paid_amount - net_price

        
        bill = Bill.objects.create(
            customer_email=email,
            total_price_without_tax=total_price_without_tax,
            total_tax=total_tax,
            net_price=net_price,
            paid_amount=paid_amount,
            balance=balance
        )
        for item in bill_items:
            BillItem.objects.create(
                bill=bill,
                product=item['product'],
                quantity=item['quantity'],
                purchase_price=item['purchase_price'],
                tax_amount=item['tax_amount'],
                total_price=item['total_price']
            )
        change_denominations = calculate_denominations(balance, denominations)

        
    
        send_mail(
            subject="Invoice",
            message=f"Your invoice: Total: {net_price}, Paid: {paid_amount}, Balance: {balance}",
            from_email="saravanakumar0997@gmail.com",
            recipient_list=[email]
        )

        context = {
            'bill': bill,
            'bill_items': bill.items.all(),
            'change_denominations': change_denominations
        }
        return render(request, 'bill_summary.html', context)

    return redirect('billing_page')



def previous_purchases(request):
    email = request.GET.get('email')
    if email:
        bills = Bill.objects.filter(customer_email=email).order_by('-created_at')
        return render(request, 'previous_purchases.html', {'bills': bills})
    return redirect('billing_page')



def calculate_denominations(balance, denominations):
    result = {}
    for denom in sorted(denominations.keys(), reverse=True):
        if balance <= 0:
            break
        count = min(balance // denom, denominations[denom])
        result[denom] = count
        balance -= denom * count
    return result


def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save() 
            return redirect('product_list') 
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})
