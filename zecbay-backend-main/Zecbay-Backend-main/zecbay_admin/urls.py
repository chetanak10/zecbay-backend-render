from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    path('', views.dashboard, name='admin_dashboard'),
    path('users/', views.user_list, name='admin_user_list'),
    path('auctions/', views.auction_list, name='admin_auction_list'),
    path('bids/', views.bid_list, name='admin_bid_list'),
    path('messages/', views.message_list, name='admin_message_list'),
]