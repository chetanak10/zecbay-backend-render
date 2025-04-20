# admin_views.py

from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from functools import wraps
from mongoengine.errors import DoesNotExist
from web.models import User, Auction, Bids, Message
from .models import AdminUser

# Admin login view
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            admin = AdminUser.objects.get(username=username)
            if admin.check_password(password):
                request.session['admin_user'] = username
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Incorrect password.")
        except AdminUser.DoesNotExist:
            messages.error(request, "Admin user not found.")

    return render(request, "admin/login.html")

# Superuser Required Decorator
def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get('admin_user'):
            try:
                AdminUser.objects.get(username=request.session['admin_user'])
                return view_func(request, *args, **kwargs)
            except AdminUser.DoesNotExist:
                pass
        return redirect('admin_login')
    return _wrapped_view

# Logout view
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

# Dashboard view
@superuser_required
def dashboard(request):
    return render(request, 'admin/dashboard.html', {
        'users_count': User.objects.count(),
        'auctions_count': Auction.objects.count(),
        'bids_count': Bids.objects.count(),
        'messages_count': Message.objects.count(),
    })

# Other admin views (with the superuser_required decorator)
@superuser_required
def user_list(request):
    users = User.objects.all()
    return render(request, 'admin/users.html', {'users': users})

@superuser_required
def auction_list(request):
    auctions = Auction.objects.all()
    return render(request, 'admin/auctions.html', {'auctions': auctions})

@superuser_required
def bid_list(request):
    bids = Bids.objects.all()
    return render(request, 'admin/bids.html', {'bids': bids})

@superuser_required
def message_list(request):
    valid_messages = []
    for message in Message.objects:
        try:
            _ = message.auction  # Triggers the dereference
            valid_messages.append(message)
        except DoesNotExist:
            continue  # Skip message with missing auction

    return render(request, 'admin/messages.html', {'messages': valid_messages})
