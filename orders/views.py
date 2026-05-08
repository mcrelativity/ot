from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order, Tracking
from .forms import OrderForm, TrackingForm

def landing_page(request):
    order = None
    error = None
    if request.method == 'POST':
        tracking_code = request.POST.get('tracking_code', '').strip()
        if tracking_code:
            try:
                order = Order.objects.get(tracking_code=tracking_code)
            except Order.DoesNotExist:
                error = "No se encontró ninguna orden con ese código."
        else:
            error = "Por favor ingrese un código de seguimiento."
    return render(request, 'orders/landing.html', {'order': order, 'error': error})

@login_required
def dashboard(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'orders/dashboard.html', {'orders': orders})

@login_required
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = OrderForm()
    return render(request, 'orders/order_form.html', {'form': form, 'title': 'Crear Orden de Trabajo'})

@login_required
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = OrderForm(instance=order)
    return render(request, 'orders/order_form.html', {'form': form, 'title': f'Actualizar Orden {order.tracking_code}', 'order': order})

@login_required
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('dashboard')
    return render(request, 'orders/order_confirm_delete.html', {'order': order})

@login_required
def order_detail_admin(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'orders/order_detail_admin.html', {'order': order})

@login_required
def add_tracking(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = TrackingForm(request.POST)
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.order = order
            tracking.save()
            return redirect('order_detail_admin', pk=order.pk)
    else:
        form = TrackingForm()
    return render(request, 'orders/tracking_form.html', {'form': form, 'order': order})
