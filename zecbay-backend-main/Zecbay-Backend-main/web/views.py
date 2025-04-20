import bcrypt
import random
import string
import json
from .models                        import User, Auction, Bids, Message
from mongoengine                    import DoesNotExist, ValidationError
from bson                           import ObjectId
from django.views.decorators.csrf   import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions         import ObjectDoesNotExist
from rest_framework.response        import Response
from rest_framework                 import status
from rest_framework.decorators      import api_view
from django.core.mail               import send_mail
from django.conf                    import settings
from django.shortcuts               import get_object_or_404
from django.http                    import JsonResponse
from datetime                       import datetime
from pytz                           import timezone

# Define the IST timezone for consistent timestamps
def get_ist_time():
    """ Helper function to get the current IST time """
    import pytz
    from datetime import datetime
    IST = pytz.timezone('Asia/Kolkata')
    return datetime.now(IST)

# Temporary in-memory storage for OTP, verification status, and business details
temp_data = {}

# Temporary in-memory storage for user data
temp_user_data = {}

# Generate random 6-digit userid
def generate_userid():
    return random.randint(100000, 999999)

def generate_username():
    # Randomly pick 4 uppercase letters followed by 4 digits
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    digits  = ''.join(random.choices(string.digits, k=4))
    return letters + digits

# API endpoint for contact form
@api_view(['POST'])
def contact_form_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get("name", "")
            email = data.get("email", "")
            subject = data.get("subject", "")
            message = data.get("message", "")

            full_message = f"""
You have a new contact enquiry from ZecBay:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}
"""

            send_mail(
                subject=f"ZecBay Contact Form: {subject}",
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["zecbay25@gmail.com"],
                fail_silently=False,
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"detail": "Method not allowed"}, status=405)

# API endpoint to send OTP
@api_view(['POST'])
def send_otp(request):
    if request.method == "POST":
        email = request.data.get("email")

        if not email:
            return JsonResponse({"message": "Email is required"}, status=400)

        # Check if the email already exists in the database
        try:
            user_exists = User.objects.get(email=email)
        except User.DoesNotExist:
            user_exists = None  # No user found

        if user_exists:
            # If the email exists, return an error message
            return JsonResponse({"error": "Email is already registered"}, status=400)

        # If the email doesn't exist, generate and send OTP
        otp = random.randint(100000, 999999)  # Generate a 6-digit OTP

        # Store OTP in memory (simulating temporary storage)
        temp_data[email] = {"otp": otp}

        # Send OTP via email (using Gmail SMTP server)
        try:
            send_mail(
                'Your OTP for verification',
                f'Your OTP is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return JsonResponse({"message": "OTP sent successfully", "otp": otp}, status=200)
        except Exception as e:
            return JsonResponse({"message": f"Error sending OTP: {str(e)}"}, status=500)

    return JsonResponse({"message": "Invalid request method"}, status=400)

# API endpoint to verify OTP
@api_view(['POST'])
def verify_otp(request):
    if request.method == 'POST':
        email = request.data.get('email')
        otp = request.data.get('otp')

        if email in temp_data and temp_data[email]["otp"] == int(otp):
            # OTP matched, proceed with verification
            temp_data[email]["verified"] = True

            # Generate dynamic username and user ID
            username = generate_username()
            userid = generate_userid()

            # Store username and userid in temporary data
            temp_data[email]["username"] = username
            temp_data[email]["userid"] = userid

            return JsonResponse({'message': 'OTP verified successfully', 'username': username, 'userid': userid}, status=200)
        return JsonResponse({'message': 'Invalid OTP'}, status=400)
    return JsonResponse({'message': 'Invalid request method'}, status=400)

# API endpoint to handle business details
@api_view(['POST'])
def business_details(request):
    if request.method == 'POST':
        email = request.data.get('email')
        name = request.data.get('name')
        phone = request.data.get('phone')
        country = request.data.get('country')
        business_details = request.data.get('businessDetails', {})

        # Extract business details from the nested dictionary
        gst_number = business_details.get('gstNumber')
        pan_number = business_details.get('panNumber')
        iec = business_details.get('iec')

        # Ensure OTP is verified
        if email not in temp_data or not temp_data[email].get("verified", False):
            return JsonResponse({"message": "OTP not verified"}, status=400)

        # Store business details in memory temporarily

        temp_data[email]["name"] = name
        temp_data[email]["phone"] = phone
        temp_data[email]["country"] = country
        temp_data[email]["gst_number"] = gst_number
        temp_data[email]["pan_number"] = pan_number
        temp_data[email]["iec"] = iec

        return JsonResponse({'message': 'Business details stored temporarily'}, status=200)
    return JsonResponse({'message': 'Invalid request method'}, status=400)

# API endpoint to handle user sign-up
@api_view(['POST'])
def signup(request):
    if request.method == 'POST':
        password = request.data.get('password')
        email = request.data.get('email')
        user_type = request.data.get('userType')

        # Ensure OTP is verified
        if email not in temp_data or not temp_data[email].get("verified", False):
            return JsonResponse({"message": "OTP not verified"}, status=400)

        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Get the business details from the temporary data
        username = temp_data[email].get("username", generate_username())
        userid = temp_data[email].get("userid", generate_userid())
        name = temp_data[email].get("name", "")
        phone = temp_data[email].get("phone", "")
        country = temp_data[email].get("country", "")
        gst_number = temp_data[email].get("gst_number", "")
        pan_number = temp_data[email].get("pan_number", "")
        iec = temp_data[email].get("iec", "")

        # Create the user
        user = User(
            userid=userid,
            name=name,
            username=username,
            email=email,
            phone=phone,
            country=country,
            password=hashed_password.decode('utf-8'),
            user_type=user_type,
            gst_number=gst_number,
            pan_number=pan_number,
            iec=iec,
        )

        # Save the user to the database
        user.save()

        # Clear temp data after successful registration
        del temp_data[email]

        return JsonResponse({'message': 'User created successfully'}, status=200)
    return JsonResponse({'message': 'Invalid request method'}, status=400)

# API endpoint to handle user signin
@api_view(['POST'])
def signin(request):
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request method"}, status=400)

    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")
    otp = request.data.get("otp")
    user_type = request.data.get("userType")
    send_otp_only = request.data.get("sendOtp")  # A flag to know if it's a send-OTP-only request

    # ======== OTP Sending Flow ========
    if send_otp_only and email:
        verified_user = User.objects.filter(email=email).first()
        if not verified_user:
            return JsonResponse({"message": "No user registered with this email."}, status=404)

        if verified_user.user_type != user_type:
            return JsonResponse({"message": f"User type mismatch. Expected {verified_user.user_type}."}, status=403)

        otp = random.randint(100000, 999999)
        temp_data[email] = {"otp": otp}

        try:
            send_mail(
                subject='Your OTP for ZecBay Login',
                message=f'Your OTP is: {otp}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({"message": "OTP sent successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"message": f"Error sending OTP: {str(e)}"}, status=500)

    # ======== OTP Login Flow ========
    if otp and email:
        if email not in temp_data or temp_data[email]["otp"] != int(otp):
            return JsonResponse({"message": "Invalid OTP."}, status=400)

        # OTP matched, continue
        verified_user = User.objects.filter(email=email).first()
        if not verified_user:
            return JsonResponse({"message": "User not found for this email."}, status=404)

        # Save user temporarily
        user_data = {
            "id": verified_user.userid,
            "name": verified_user.name,
            "email": verified_user.email,
            "username": verified_user.username,
            "phone": verified_user.phone,
            "country": verified_user.country,
            "password": verified_user.password,
            "user_type": verified_user.user_type,
            "verification_status": verified_user.verification_status,
            "business_details": {
                "gst_number": verified_user.gst_number,
                "pan_number": verified_user.pan_number,
                "iec": verified_user.iec,
            }
        }

        temp_user_data[verified_user.userid] = user_data
        return JsonResponse({"message": "OTP login successful", "user": user_data}, status=200)

    # ======== Password Login Flow ========
    if not password or (not username and not email):
        return JsonResponse({"message": "Username/email and password are required."}, status=400)

    try:
        # If email is provided, search by email, else by username
        user = User.objects.filter(email=email).first() if email else User.objects.filter(username=username).first()

        if not user:
            return JsonResponse({"message": "Invalid username/email or password."}, status=401)

        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return JsonResponse({"message": "Invalid password."}, status=401)

        if user.user_type != user_type:
            return JsonResponse({"message": f"User type mismatch. Expected {user.user_type}."}, status=403)

        user_data = {
            "id": user.userid,
            "name": user.name,
            "email": user.email,
            "username": user.username,
            "phone": user.phone,
            "country": user.country,
            "password": user.password,
            "user_type": user.user_type,
            "verification_status": user.verification_status,
            "business_details": {
                "gst_number": user.gst_number,
                "pan_number": user.pan_number,
                "iec": user.iec,
            }
        }

        temp_user_data[user.userid] = user_data
        return JsonResponse({"message": "Login successful", "user": user_data}, status=200)

    except Exception as e:
        return JsonResponse({"message": f"Error during login: {str(e)}"}, status=500)

# API endpoint to fetch user profile
@api_view(['GET'])
@csrf_exempt
def fetch_user_profile(request):
    try:
        # Get user ID from the session
        user_id = request.data.get('id')

        if not user_id:
            return JsonResponse({'message': 'User not authenticated.'}, status=401)

        # Fetch user data from the database by userId
        user = User.objects.get(userid=user_id)

        if not user:
            return JsonResponse({'message': 'User not found.'}, status=404)

        # Send the user profile as the response
        user_profile = {
            "id": user.userid,
            "name": user.name,
            "email": user.email,
            "username": user.username,
            "phone": user.phone,
            "country": user.country,
            "password": user.password,
            "user_type": user.user_type,
            "business_details": {
                "gst_number": user.gst_number,
                "pan_number": user.pan_number,
                "iec": user.iec,
            }
        }

        return JsonResponse(user_profile, status=200)

    except Exception as error:
        print("Error fetching user profile:", error)
        return JsonResponse({'message': 'Internal server error.'}, status=500)

# API endpoint to update user profile
@api_view(['PUT'])
@csrf_exempt
def update_user_profile(request):
    if request.method == "PUT":
        try:
            # Get the user ID from the session
            user_id = request.data.get('id')

            if not user_id:
                return JsonResponse({'message': 'User not authenticated.'}, status=401)

            # Fetch user data from the database by userId
            user = User.objects.get(userid=user_id)

            if not user:
                return JsonResponse({'message': 'User not found.'}, status=404)

            # Get data from the request
            name = request.data.get('name')
            email = request.data.get('email')
            username = request.data.get('username')
            phone = request.data.get('phone')
            country = request.data.get('country')
            user_type = request.data.get('user_type')
            password = request.data.get('password')
            business_details = request.data.get('business_details')  # You can pass business details as a dict

            # Validate required fields
            if not name or not email or not username or not user_type:
                return JsonResponse({'message': 'Name, Email, Username, and UserType are required.'}, status=400)

            # Update user fields
            user.name = name
            user.email = email
            user.phone = phone
            user.username = username
            user.country = country
            user.user_type = user_type

            # If password is provided, hash it and update
            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                user.password = hashed_password.decode('utf-8')

            # Update business details (assuming the business_details are sent as JSON)
            if business_details:
                user.gst_number = business_details.get('gst_number', '')
                user.pan_number = business_details.get('pan_number', '')
                user.iec = business_details.get('iec', '')

            # Save the updated user
            user.save()

            # Prepare the updated user data to return
            updated_user_data = {
                "id": user.userid,
                "name": user.name,
                "email": user.email,
                "username": user.username,
                "phone": user.phone,
                "country": user.country,
                "password": user.password,
                "user_type": user.user_type,
                "business_details": {
                    "gst_number": user.gst_number,
                    "pan_number": user.pan_number,
                    "iec": user.iec,
                }
            }

            return JsonResponse({'message': 'Profile updated successfully.', 'user': updated_user_data}, status=200)

        except DoesNotExist:
            return JsonResponse({'message': 'User not found.'}, status=404)

        except Exception as error:
            print("Error updating user profile:", error)
            return JsonResponse({'message': 'Internal server error.'}, status=500)

    return JsonResponse({'message': 'Invalid request method'}, status=400)

# Fetch all auctions
def get_auctions(request):
    try:
        auctions = Auction.objects.all()  # Get all auctions from MongoDB
        auctions_data = []
        for auction in auctions:
            try:
                user = User.objects.get(pk=auction.user.id)  # Fetch the User using the ObjectId
                created_by = user.username  # Access the username of the user
            except DoesNotExist:
                created_by = "Unknown"

            # Number of bids in the auction
            bid_count = len(auction.bids)
            exporter_ids = []

            for bid in auction.bids:
                try:
                    bid_obj = Bids.objects.get(id=bid.id)
                    exporter_ids.append(str(bid_obj.exporterId.id))
                except Bids.DoesNotExist:
                    continue

            # Recalculate time left dynamically based on current time
            time_left = auction.get_time_left()

            # Number of registrations in the auction
            register_count = len(auction.registered_users)

            # Only include auctions that are still active
            if time_left != "Auction ended":
                auctions_data.append({
                    "id": str(auction.pk),
                    "product_name": auction.product_name,
                    "category": auction.category,
                    "subcategory": auction.subcategory,
                    "initial_price": auction.initial_price,
                    "current_price": auction.current_price,
                    "unit": auction.unit,
                    "quantity": auction.quantity,
                    "round": auction.round,
                    "total_rounds": auction.total_rounds,
                    "time_left": time_left,
                    "bids_count": bid_count,
                    "bid_exporter_ids": exporter_ids,
                    "created_at": auction.created_at.isoformat(),
                    "created_by": created_by,
                    "register_count": register_count
                })
        return JsonResponse({"auctions": auctions_data}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# Fetch auction by ID
def get_auction_by_id(request, auction_id):
    try:
        auction = Auction.objects.get(id=auction_id)

        # Get the User object based on the user ID (stored as ObjectId in Auction)
        try:
            user = User.objects.get(pk=auction.user.id) # Fetch the User using the ObjectId
            created_by = user.username  # Access the username of the user
        except DoesNotExist:
            created_by = "Unknown"  # In case the user does not exist

        # Recalculate time left dynamically based on current time
        time_left = auction.get_time_left()

        # Fetch the bids associated with the auction
        bid_data = []
        lowest_bid_price = auction.current_price
        for bid in auction.bids:
            # Fetch each individual bid from the Bids collection using its ID
            try:
                bid_obj = Bids.objects.get(id=bid.id)  # Fetch the Bid object using its ObjectId
                price = bid_obj.pricePerQuantity

                # Safe float conversion
                price_float = float(price) if price is not None else None

                bid_data.append({
                    "id": str(bid_obj.pk),  # Convert bid PK (ObjectId) to string
                    "exporter_id": str(bid_obj.exporterId.id),  # Convert exporterId (ObjectId) to string
                    "price": price_float,
                    "created_at": bid_obj.createdAt.isoformat(),  # Convert datetime to ISO format string
                })

                # Update lowest bid price
                if price_float is not None and price_float < lowest_bid_price:
                    lowest_bid_price = price_float

            except Bids.DoesNotExist:
                continue

        # If there are bids, update the current price of the auction to the lowest bid price
        if bid_data:
            auction.current_price = lowest_bid_price

        # If the auction has ended, update the time_left and mark the auction as ended
        if time_left == "Auction ended":
            auction.time_left = "Auction ended"
            auction.save()  # Save the auction with the updated status

        # Fetch the winner's bid if the auction has ended
        winner_data = None
        if auction.winner:
            try:
                winner_bid = Bids.objects.get(id=auction.winner.id)  # Fetch the winner bid using the referenced id
                winner_data = {
                    "exporter_id": str(winner_bid.exporterId.id),  # Exporter ID as string
                    "price": float(winner_bid.pricePerQuantity) if winner_bid.pricePerQuantity is not None else None,
                }
            except Bids.DoesNotExist:
                winner_data = None  # If no winner is found

        # Number of registrations in the auction
        register_count = len(auction.registered_users)

        # Prepare the auction data for response
        auction_data = {
            "id": str(auction.pk),
            "product_name": auction.product_name,
            "category": auction.category,
            "subcategory": auction.subcategory,
            "description": auction.description,
            "initial_price": auction.initial_price,
            "current_price": auction.current_price,
            "unit": auction.unit,
            "quantity": auction.quantity,
            "round": auction.round,
            "total_rounds": auction.total_rounds,
            "time_left": time_left,
            "bids": bid_data,
            "created_by": created_by,
            "winner": winner_data,
            "registered_users": [user.username for user in auction.registered_users],
            "register_count": register_count,
        }

        # Save auction data with the updated current_price if necessary
        if bid_data:
            auction.save()  # Save the auction with the updated current_price if bids were placed

        return JsonResponse({
            "auction": auction_data,
        }, status=200)

    except Auction.DoesNotExist:
        return JsonResponse({"error": "Auction not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# API endpoint to register user for auction
@api_view(['POST'])
@csrf_exempt
def register_user_for_auction(request, auction_id):
    if request.method == 'POST':
        try:
            auction = Auction.objects.get(id=auction_id)
        except Auction.DoesNotExist:
            return JsonResponse({"error": "Auction not found"}, status=404)

        try:
            body = json.loads(request.body)
            user_id = body.get("user_id")

            print(f"Received user_id: {user_id}")

            if not user_id:
                return JsonResponse({"error": "User ID is required"}, status=400)

            # Get user object from username
            try:
                user = User.objects.get(userid=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            if auction.register_user(user):
                return JsonResponse({"message": "You have successfully registered for this auction."}, status=200)
            else:
                return JsonResponse({"message": "You are already registered for this auction."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def serialize_objectid(obj):
    """ Helper function to convert ObjectId to string """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: serialize_objectid(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_objectid(item) for item in obj]
    return obj

@api_view(['POST'])
@csrf_exempt
def create_bid(request):
    """ View to create a new bid """
    if request.method == 'POST':
        try:
            print(f"Request data: {request.data}")
            auction_id = request.data.get('auction_id')
            exporter_id = request.data.get('exporter_id')
            price_per_quantity = request.data.get('price_per_quantity')

            if not auction_id or not exporter_id or not price_per_quantity:
                return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                price_per_quantity = float(price_per_quantity)  # Ensure price_per_quantity is a float
            except ValueError:
                return Response({"error": "Invalid bid values."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch related auction and exporter (user)
            try:
                auction = Auction.objects.get(id=auction_id)  # Fetch auction by ObjectId using mongoengine
            except DoesNotExist:
                return Response({"error": "Auction not found."}, status=status.HTTP_404_NOT_FOUND)

            try:
                exporter = User.objects.get(pk=exporter_id)  # Fetch exporter (user) by ID
            except User.DoesNotExist:
                return Response({"error": "Exporter not found."}, status=status.HTTP_404_NOT_FOUND)

            # Create the bid object
            bid = Bids(
                exporterId=exporter,
                auctionID=auction,
                pricePerQuantity=price_per_quantity,  # Set price per quantity
                bidsMade=[f'{price_per_quantity} at {get_ist_time().isoformat()}'],
                createdAt=get_ist_time()
            )
            bid.save()

            auction.bids.append(bid)
            auction.save()

            # After creating a new bid, check for the auction winner
            if auction.bids:
                winner_bid = auction.get_reverse_auction_winner()
                if winner_bid:
                    auction.winner = winner_bid
                    auction.save()
                    return Response({
                        'message': 'Bid created successfully',
                        'bid': serialize_objectid(bid.to_mongo()),
                        'winner_bid': serialize_objectid(winner_bid.to_mongo()),
                        'auction_winner': serialize_objectid(auction.winner.to_mongo())
                    }, status=status.HTTP_201_CREATED)
            return Response({
                'message': 'Bid created successfully',
                'bid': serialize_objectid(bid.to_mongo())
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log or print error details for debugging
            print(f"Error occurred: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@csrf_exempt
def update_bid(request, bid_id):
    """ View to update an existing bid """
    if request.method == 'POST':
        try:
            bid = Bids.objects.get(id=bid_id)  # Fetch the bid by ID

            price_per_quantity = request.data.get('price_per_quantity', bid.pricePerQuantity)  # Same for price
            try:
                price_per_quantity = float(price_per_quantity)  # Ensure price is a float
            except ValueError:
                return Response({"error": "Invalid bid values."}, status=status.HTTP_400_BAD_REQUEST)

            if bid.auctionID.time_left == "Auction ended":
                return JsonResponse({'error': 'Cannot update bid. Auction has ended.'}, status=400)

            bid.pricePerQuantity = price_per_quantity
            bid.add_bid_history(price_per_quantity)  # Add the new bid to history
            bid.save()

            # After updating the bid, check for the auction winner
            auction = bid.auctionID  # Get the related auction
            winner_bid = auction.get_reverse_auction_winner()
            if winner_bid:
                auction.winner = winner_bid
                auction.save()
                return JsonResponse({
                    'message': 'Bid updated successfully',
                    'bid': serialize_objectid(bid.to_mongo()),
                    'winner_bid': serialize_objectid(winner_bid.to_mongo()),
                    'auction_winner': serialize_objectid(auction.winner.to_mongo())
                })
            else:
                return JsonResponse({'message': 'Bid updated successfully', 'bid': serialize_objectid(bid.to_mongo())})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
@csrf_exempt
def delete_bid(request, bid_id):
    """ View to delete a bid """
    if request.method == 'POST':
        try:
            bid = Bids.objects.get(id=bid_id)

            if bid.auctionID.time_left == "Auction ended":
                return JsonResponse({'error': 'Cannot delete bid. Auction has ended.'}, status=400)

            auction = bid.auctionID

            # Delete the bid
            bid.delete()

            # Recalculate current price and winner after deletion
            if auction.bids:
                remaining_bids = Bids.objects(auctionID=auction)

                if remaining_bids:
                    # Find the lowest priced bid (reverse auction logic)
                    winner_bid = min(remaining_bids, key=lambda b: b.pricePerQuantity)
                    auction.current_price = winner_bid.pricePerQuantity
                    auction.winner = winner_bid
                else:
                    # No bids left, reset to initial values
                    auction.current_price = auction.initial_price
                    auction.winner = None
            else:
                auction.current_price = auction.initial_price
                auction.winner = None

            # Update auction.bids list (remove deleted bid)
            auction.bids = [b for b in auction.bids if str(b.id) != str(bid_id)]

            auction.save()

            return JsonResponse({'message': 'Bid deleted successfully'})
        except Bids.DoesNotExist:
            return JsonResponse({'error': 'Bid not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
@csrf_exempt
def list_product(request):
    if request.method == 'POST':
        # Get data from the request
        try:
            product_name = request.data.get("product_name")
            category = request.data.get("category")
            subcategory = request.data.get("subcategory")
            hs_code = request.data.get("hs_code")
            description = request.data.get("description")
            quantity = request.data.get("quantity")
            initial_price = float(request.data.get("initial_price"))
            unit = request.data.get("unit")
            rounds = int(request.data.get("rounds"))
            username = request.data.get("username")

            if not username:
                return JsonResponse({'error': 'Username is required.'}, status=400)

            # Retrieve the user based on the provided username (MongoDB)
            try:
                user = User.objects.get(username=username)  # Look up the user by their username
            except User.DoesNotExist:
                return JsonResponse({'error': 'User does not exist.'}, status=404)

            # Create the Auction product
            auction = Auction(
                product_name=product_name,
                category=category,
                subcategory=subcategory,
                hs_code=hs_code,
                description=description,
                initial_price=initial_price,
                current_price=initial_price,  # Initial price is the current price at the start
                unit=unit,
                quantity=quantity,
                round=rounds,
                total_rounds=rounds,
                time_left="24 hours",
                bids=[],  # No bids yet
                user=user,
                created_at=get_ist_time()
            )
            auction.save()

            # Respond with success
            return JsonResponse({'message': 'Auction created successfully!'}, status=201)

        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def get_auctions_message(request):
    try:
        auctions = Auction.objects.all()
        completed_auctions_data = []

        for auction in auctions:
            # Skip if auction is still active
            if auction.get_time_left() != "Auction ended":
                continue

            # Get importer (auction creator) details
            try:
                importer = User.objects.get(pk=auction.user.id)
                created_by = importer.username
                importer_details = {
                    "id": str(importer.pk),
                    "username": importer.username,
                    "full_name": importer.name,
                    "email": importer.email,
                    "phone_number": importer.phone,
                    "iec": importer.iec,
                }
            except ObjectDoesNotExist:
                created_by = "Unknown"
                importer_details = {
                    "id": str(auction.user.id),
                    "username": "unknown",
                    "full_name": "",
                    "email": "",
                    "phone_number": "",
                    "iec": "",
                }

            # Get exporter (winner) details
            winner_data = None
            exporter_details = None
            if auction.winner:
                try:
                    winner_bid = Bids.objects.get(id=auction.winner.id)
                    exporter = User.objects.get(pk=winner_bid.exporterId.id)
                    winner_data = {
                        "id": str(winner_bid.pk),
                        "exporter_id": str(exporter.id),
                        "price": winner_bid.pricePerQuantity,
                        "created_at": winner_bid.createdAt.isoformat(),
                    }
                    exporter_details = {
                        "id": str(exporter.pk),
                        "username": exporter.username,
                        "full_name": exporter.name,
                        "email": exporter.email,
                        "phone_number": exporter.phone,
                        "iec": exporter.iec,
                    }
                except (Bids.DoesNotExist, User.DoesNotExist):
                    winner_data = None
                    exporter_details = {
                        "id": str(auction.winner.id),
                        "username": "unknown",
                        "full_name": "",
                        "email": "",
                        "phone_number": "",
                        "iec": "",
                    }

            # Assemble full auction data
            auction_data = {
                "id": str(auction.pk),
                "product_name": auction.product_name,
                "category": auction.category,
                "subcategory": auction.subcategory,
                "description": auction.description,
                "initial_price": auction.initial_price,
                "final_price": auction.current_price,
                "unit": auction.unit,
                "quantity": auction.quantity,
                "round": auction.round,
                "total_rounds": auction.total_rounds,
                "created_at": auction.created_at.isoformat(),
                "created_by": created_by,
                "importer_details": importer_details,
                "winner_bid": winner_data,
                "exporter_details": exporter_details
            }

            completed_auctions_data.append(auction_data)

        return JsonResponse({"completed_auctions": completed_auctions_data}, status=200)

    except Exception as e:
        print("Error fetching completed auctions:", e)  # Console print for debugging
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
def send_message(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            auction_id = data['auction_id']
            sender_username = data['sender_username']
            receiver_username = data['receiver_username']
            message_content = data['message']

            try:
                auction = Auction.objects.get(id=auction_id)
            except Auction.DoesNotExist:
                return JsonResponse({'error': 'Auction not found'}, status=404)

            # Create a new message
            message = Message(
                auction=auction,
                sender_username=sender_username,
                receiver_username=receiver_username,
                message=message_content,
                timestamp=get_ist_time()  # Ensure the timestamp is in IST
            )
            message.save()

            # Return the newly created message
            return JsonResponse({
                'status': 'success',
                'message': {
                    'sender': message.sender_username,
                    'receiver': message.receiver_username,
                    'message': message.message,
                    'timestamp': message.timestamp.isoformat()
                }
            }, status=200)

        except KeyError as e:
            return JsonResponse({'error': f'Missing key: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@api_view(['GET'])
def get_messages(request, auction_id):
    # Retrieve all messages for a specific auction
    try:
        auction = Auction.objects.get(id=auction_id)
    except Auction.DoesNotExist:
        return JsonResponse({'error': 'Auction not found'}, status=404)

    # Fetch messages related to the auction, ordered by timestamp
    messages = Message.objects.filter(auction=auction).order_by('timestamp')

    # Serialize messages to JSON format (without using serializers)
    messages_list = [
        {
            'auction_id': str(auction.id),
            'message_id': str(message.id),
            'sender': message.sender_username,
            'receiver': message.receiver_username,
            'message': message.message,
            'timestamp': message.timestamp.isoformat()
        }
        for message in messages
    ]

    return JsonResponse({'messages': messages_list}, status=200)

def dashboard(request):
    # Get the username from the request query parameters
    username = request.GET.get('username')

    if username:
        # Get the user details
        try:
            user = User.objects.get(username=username)
            user_data = {
                "id": user.userid,
                "name": user.name,
                "email": user.email,
                "user_type": user.user_type,
                "verification_status": user.verification_status,
            }
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "User not found"})

        # Check user type and fetch relevant data
        if user.user_type == "importer":

            # Get the auctions related to the user
            auctions = Auction.objects(user=user)

            auction_data = []
            if len(auctions) > 0:
                for auction in auctions:
                    time_left = auction.get_time_left()
                    bid_count = len(auction.bids)

                    # 🆕 Add winner bid details (if exists)
                    winner_bid = None
                    if auction.winner:
                        winner_bid = {
                            "id": str(auction.winner.id),
                            "price": auction.winner.pricePerQuantity,
                            "exporter_id": str(auction.winner.exporterId.id),
                            "created_at": auction.winner.createdAt.isoformat()
                        }

                    auction_data.append({
                        "id": str(auction.id),
                        "product_name": auction.product_name,
                        "category": auction.category,
                        "subcategory": auction.subcategory,
                        "initial_price": auction.initial_price,
                        "current_price": auction.current_price,
                        "unit": auction.unit,
                        "quantity": auction.quantity,
                        "round": auction.round,
                        "total_rounds": auction.total_rounds,
                        "time_left": time_left,
                        "bid_count": bid_count,
                        "winner_bid": winner_bid
                    })
            else:
                return JsonResponse({"success": False, "message": "No auctions found"})

            # Return both user and auction details in one response
            return JsonResponse({
                "success": True,
                "user": user_data,
                "auctions": auction_data
            })

        elif user.user_type == "exporter":
            # Get the bids related to the user
            bids = Bids.objects.filter(exporterId=user.userid)
            bid_data = []
            if bids:
                for bid in bids:
                    auction = Auction.objects.get(id=bid.auctionID.id)  # Fetch auction details using auctionID
                    winner_bid_id = auction.winner.id if auction.winner else None
                    bid_data.append({
                        "id": str(bid.id),
                        "auctionID": str(bid.auctionID),
                        "pricePerQuantity": bid.pricePerQuantity,
                        "auctionid": str(auction.id),
                        "category": auction.category,
                        "subcategory": auction.subcategory,
                        "timeLeft": auction.get_time_left(),
                        "winner_bid_id": str(winner_bid_id),
                    })
            else:
                return JsonResponse({"success": False, "message": "No bids found"})

            # Return both user and bid details in one response
            return JsonResponse({
                "success": True,
                "user": user_data,
                "bids": bid_data
            })

        else:
            return JsonResponse({"success": False, "message": "Invalid user type"})

    return JsonResponse({"success": False, "message": "Username parameter missing"})