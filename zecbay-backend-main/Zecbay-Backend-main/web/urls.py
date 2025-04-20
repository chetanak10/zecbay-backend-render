from django.urls    import path, re_path
from Zecbay         import consumers
from . import views

urlpatterns = [
    path("api/contact/", views.contact_form_view, name="contact-form"),
    path('api/user/send-otp/', views.send_otp, name='send-otp'),
    path('api/user/verify-otp/', views.verify_otp, name='verify-otp'),
    path('api/user/business-details/', views.business_details, name='business-details'),
    path('api/user/signup/', views.signup, name='signup'),
    path('api/user/login/', views.signin, name='login'),
    path('api/user/profile/', views.fetch_user_profile, name='profile'),
    path('api/user/profile-update/', views.update_user_profile, name='update-profile'),
    path('api/auctions/', views.get_auctions, name='get_auctions'),
    path('api/auctions/<str:auction_id>/', views.get_auction_by_id, name='get_auction_by_id'),
    path('api/auctions/<str:auction_id>/register/', views.register_user_for_auction, name='register-user'),
    path('api/list-product/', views.list_product, name='list_product'),
    path('api/dashboard/', views.dashboard, name='dashboard'),
    path('api/auctions_message/', views.get_auctions_message, name='get_auctions_message'),
    path('api/messages/send/', views.send_message, name='send_message'),
    path('api/messages/<str:auction_id>/', views.get_messages, name='get_messages'),
    path('api/bids/create/', views.create_bid, name='create_bid'),
    path('api/bids/update/<str:bid_id>/', views.update_bid, name='update_bid'),
    path('api/bids/delete/<str:bid_id>/', views.delete_bid, name='delete_bid'),

    # WebSocket URL for bidding
    re_path(r'ws/bids/(?P<auction_id>\d+)/$', consumers.BidConsumer.as_asgi()),
]
