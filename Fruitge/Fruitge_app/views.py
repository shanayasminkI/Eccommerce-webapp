from django.shortcuts import render,redirect,get_object_or_404,HttpResponse
from django.contrib import messages
from . models import *
from django.http import JsonResponse
from django.db import transaction 
from django.http import HttpResponseBadRequest
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login,authenticate
from django.http import Http404
from django.db import transaction
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
from itertools import groupby
from django.utils.timezone import now
from collections import defaultdict
import json


def index_load(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        ac_type = request.POST.get('dropdown_value')  # Account type

        # Authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Set session variable for Buyer
            if ac_type == 'Buyer':
                buyer = buyerSignUp_tb.objects.filter(user=user).first()
                if buyer:
                    # Store buyer data in the session
                    request.session['buyer_id'] = buyer.id
                    request.session['buyer_name'] = buyer.name
                    request.session['buyer_address'] = buyer.address
                    return redirect('buyer_portal')

            elif ac_type == 'Seller':
                seller = sellerSignUp_tb.objects.filter(user=user).first()  # Retrieve the seller
                if seller:
                    # Check approval status
                    if not seller.is_approved:
                        request.session['seller_name'] = seller.name  # Store seller name in session
                        messages.error(request, "Your account is awaiting admin approval.")
                        return redirect('header')  # Redirect back to login page

                    # Store seller name in session for approved accounts
                    request.session['seller_name'] = seller.name
                    return redirect('item_add')  # Redirect Seller to their portal
                else:
                    messages.error(request, "Seller account not found. Please check your details or register.")
                    return redirect('header')  # Redirect back to login page

            elif ac_type == 'Delivery Agent':
                da = deliveryagentSignUp_tb.objects.filter(user=user).first()
                if da:
                    request.session['agent_id'] = da.id
                    request.session['agent_name'] = da.name
                    if not da.is_approved:
                        messages.error(request, "Your account is awaiting admin approval.")
                        return redirect('header')  # Redirect back to login page
                    else:
                        return redirect('deliveryAgent')  # Redirect Delivery Agent to their portal
                else:
                    messages.error(request, "Delivery Agent account not found. Please check your details or register.")
                    return redirect('header')  # Redirect back to login page

            # Default login if no account type matches
            login(request, user)
            return redirect('header')  # Redirect to a generic home or header page

        else:
            messages.error(request, 'Invalid username or password')

    # Load the index page and display images and items if the method is GET
    template = loader.get_template('index.html')
    image = carouselImage.objects.all().order_by('-created_at')
    items = item_tb.objects.all()
    context = {
        'images': image,
        'dummy_array': [1, 2, 3],
        'items': items
    }
    return HttpResponse(template.render(context, request))
  
def contactfun(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        mobile_number = request.POST.get('mob')
        complaint_type = request.POST.get('sel1')
        message = request.POST.get('text')

        # Save the complaint
        Complaint.objects.create(
            name=name,
            email=email,
            mobile_number=mobile_number,
            complaint_type=complaint_type,
            message=message
        )
        return render(request, 'contactUs.html')  # Render the thank you template

    return render(request,'contactUs.html')

def item_add(request):
    # Check if the seller is logged in
    seller_name = request.session.get('seller_name')
    if not seller_name:
        return redirect('/')  # Redirect to login page if not logged in

    # Fetch seller details from the database
    try:
        seller = sellerSignUp_tb.objects.get(name=seller_name)
    except sellerSignUp_tb.DoesNotExist:
        return redirect('/')  # Redirect to login if seller doesn't exist

    # Handle profile updates if the request method is POST
    if request.method == 'POST':
        # Update profile image
        uploaded_image = request.FILES.get('profile_image_seller')
        if uploaded_image:
            if not uploaded_image.content_type.startswith('image/'):
                messages.error(request, "Please upload a valid image file.")
            else:
                seller.profile_image_seller = uploaded_image

        # Update mobile number
        mobile_number = request.POST.get('mobileNo')
        if mobile_number:
            seller.mobileNo = mobile_number

        # Update address
        address = request.POST.get('address')
        if address:
            seller.address = address

        # Update GST number
        gst_number = request.POST.get('gst_no')
        if gst_number:
            seller.gst_no = gst_number

        # Update shop name
        shop_name = request.POST.get('shop_name')
        if shop_name:
            seller.shop_name = shop_name

        # Save seller profile updates
        seller.save()

        # Check if the request is to update expiry date
        item_id = request.POST.get('item_id')
        if item_id:
            try:
                item = item_tb.objects.get(id=item_id)
                new_expiry_date = request.POST.get('expiry_date')

                if new_expiry_date:
                    item.ex_date = new_expiry_date
                    item.save()
                    messages.success(request, "Expiry date updated successfully.")
            except item_tb.DoesNotExist:
                messages.error(request, "Item not found.")

        return redirect('item_add')

    # Fetch seller's items and related data
    items = item_tb.objects.filter(seller=seller).prefetch_related('images')
    buyer_reviews = RatingReview.objects.filter(item__in=items).select_related('buyer', 'item')
    orders = Order.objects.filter(items__item__in=items).distinct()

    # Enrich orders with buyer details
    enriched_orders = []
    for order in orders:
        enriched_order = {
            "order": order,
            "buyer_name": "N/A",
            "buyer_phone": "N/A",
            "buyer_address": "N/A",
        }

        # Ensure buyer details are being correctly fetched
        if order.user:  # Check if the user exists
            try:
                # Query buyerSignUp_tb directly by user
                buyer = buyerSignUp_tb.objects.get(user=order.user)
                enriched_order["buyer_name"] = buyer.name
                enriched_order["buyer_phone"] = buyer.mobileNo
                enriched_order["buyer_address"] = buyer.address
            except buyerSignUp_tb.DoesNotExist:
                pass

        enriched_orders.append(enriched_order)

    # Render the template
    return render(request, 'seller.html', {
        'items': items,
        'orders': enriched_orders,
        'seller': seller,
        'buyer_reviews': buyer_reviews,
        'profile_image': seller.profile_image_seller.url if seller.profile_image_seller else None,
    })

def admin_portal(request):
    if "username" not in request.session:
        return redirect("header")  # Redirect if admin is not logged in

    # Fetch admin details
    try:
        admin_user = admin_tb.objects.get(username=request.session["username"])
        print(admin_user.password)
    except admin_tb.DoesNotExist:
        messages.error(request, "Admin user not found.")
        return redirect("header")

    if request.method == 'POST':
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Compare current password directly (not recommended for security)
        if current_password != admin_user.password:
            messages.error(request, "Current password is incorrect.")
            return redirect("admin_portal")

        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("admin_portal")

        # Update password directly (should ideally be hashed)
        admin_user.password = new_password
        admin_user.save()

        # Success message
        messages.success(request, "Password changed successfully!")
        return redirect("admin_portal")

    # Count the number of users
    total_users = User.objects.count()

    # Get all accounts
    seller_accounts = sellerSignUp_tb.objects.all()
    buyer_accounts = buyerSignUp_tb.objects.all()
    da_accounts = deliveryagentSignUp_tb.objects.all()

    # Get time range from GET request
    time_range = request.GET.get("time_range", "all")

    if time_range == "24h":
        recent_activities = ActivityLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).order_by("-timestamp")
    elif time_range == "7d":
        recent_activities = ActivityLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).order_by("-timestamp")
    else:
        recent_activities = ActivityLog.objects.all().order_by("-timestamp")[:5]

    items = item_tb.objects.prefetch_related("ratingreview_set")

    # Count pending seller and DA accounts
    pending_sellers = sellerSignUp_tb.objects.filter(is_approved=False).count()
    pending_das = deliveryagentSignUp_tb.objects.filter(is_approved=False).count()

    # Count pending orders
    pending_orders_count = Order.objects.filter(
        items__status="pending", is_cancelled=False
    ).distinct().count()
    complaints = Complaint.objects.all().order_by("-created_at")

    # Fetch order items
    order_items = OrderItem.objects.select_related("item__seller").all()

    # Ensure enrich_orders function is defined
    enriched_orders = enrich_orders(order_items) if "enrich_orders" in globals() else []

    # Group orders by order ID
    grouped_orders = defaultdict(lambda: {"order_items": [], "grand_total": 0})

    for enriched_order in enriched_orders:
        order_id = enriched_order["order_item"].order.id
        grouped_orders[order_id]["order_items"].append(enriched_order)
        grouped_orders[order_id]["grand_total"] = enriched_order["order_item"].order.grand_total

    # Ensure grouped_orders_list is initialized
    grouped_orders_list = sorted(
        [
            {"order_id": order_id, "order_data": order_data}
            for order_id, order_data in grouped_orders.items()
        ],
        key=lambda x: x["order_data"]["order_items"][0]["order_item"].order.created_at,
        reverse=True,  # Sort in descending order (latest first)
    ) if grouped_orders else []

    context = {
        "seller_accounts": seller_accounts,
        "buyer_accounts": buyer_accounts,
        "da_accounts": da_accounts,
        "total_users": total_users,
        "recent_activities": recent_activities,
        "pending_sellers": pending_sellers,
        "pending_das": pending_das,
        "pending_orders_count": pending_orders_count,
        "complaints": complaints,
        "grouped_orders": grouped_orders_list,
        "items": items,
        "admin_username": admin_user.username,
    }

    return render(request, "admin.html", context)


    
def settings_buyer(request, id):
    buyer_id = request.session.get('buyer_id')

    if not buyer_id:
        return redirect('/')
    try:
        buyer = buyerSignUp_tb.objects.get(id=id)

        if request.method == 'POST':
            # Save the updated mobile number, address, and profile image
            mobile_no = request.POST.get('mobileNo')
            address = request.POST.get('address')
            profile_image = request.FILES.get('profile_image_buyer')

            if not mobile_no:
                return redirect('settings_buyer', id=id)

            buyer.mobileNo = mobile_no
            buyer.address = address

            if profile_image:
                buyer.profile_image_buyer = profile_image

            buyer.save()
            return redirect('settings_buyer', id=id)
        # Fetch buyer's reviews and related items
        buyer_reviews = RatingReview.objects.filter(buyer_id=buyer.id).select_related('item')
        # Fetch items with reviews
        items = item_tb.objects.prefetch_related('ratingreview_set')
         # Get the cart count using the get_cart_count function
        cart_count = get_cart_count(request)  # Call the function here
        cancelled_orders = Order.objects.filter(user=buyer.user, is_cancelled=True).order_by('-cancelled_at')
    

        context = {
            'name': buyer.name,
            'cancelled_orders':cancelled_orders,
            'email': buyer.email,
            'mobileNo': buyer.mobileNo,
            'address': buyer.address,
            'profile_image': buyer.profile_image_buyer,
            'buyer_reviews': buyer_reviews,
            'items': items,
            'cart_count':cart_count,
            'buyer_id':buyer_id
        }

        return render(request, 'settings_buyer.html', context)

    except buyerSignUp_tb.DoesNotExist:
        return redirect('/')
    
def buyer_portal(request):
    buyer_id = request.session.get('buyer_id')  # Ensure 'buyer_id' is stored in the session during login
    buyer_name = request.session.get('buyer_name')
    if not buyer_name:
        return redirect('/')  # Redirect to the login page if the session is missing
    # q = request.GET.get('q')  # This will assign q to the value of 'q' from request.GET or an empty string if 'q' is not found

    # # Fetch all items from the database based on query parameter 'q'
    # if q:
    #     items = item_tb.objects.filter(name__icontains=q)
    # else:
    #     items = item_tb.objects.all()
    items = item_tb.objects.all()
    buyer = buyerSignUp_tb.objects.filter(id=buyer_id).first()

    # Filter by type
    item_type = request.GET.get('type')
    if item_type:
        items = items.filter(type=item_type)

    # Filter by category
    category = request.GET.get('category')
    if category:
        items = items.filter(category=category)

    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            min_price = float(min_price)
            items = items.filter(price_kg__gte=min_price)
        except ValueError:
            pass  # Ignore invalid values for min_price
    if max_price:
        try:
            max_price = float(max_price)
            items = items.filter(price_kg__lte=max_price)
        except ValueError:
            pass  # Ignore invalid values for max_price

    # Filter by quantity range
    min_quantity = request.GET.get('min_quantity')
    max_quantity = request.GET.get('max_quantity')
    if min_quantity:
        try:
            min_quantity = int(min_quantity)
            items = items.filter(quantity__gte=min_quantity)
        except ValueError:
            pass  # Ignore invalid values for min_quantity
    if max_quantity:
        try:
            max_quantity = int(max_quantity)
            items = items.filter(quantity__lte=max_quantity)
        except ValueError:
            pass  # Ignore invalid values for max_quantity

    # Filter specific item types for display
    fruits = items.filter(type='fruits')
    vegetables = items.filter(type='vegetables')
    exotic_fruits = items.filter(type='exotic fruits')
    exotic_vegetables = items.filter(type='exotic vegetables')
    mushrooms = items.filter(type='mushrooms')  # Assuming correct spelling
    salads = items.filter(type='salad items')
    image = carouselImage.objects.all().order_by('-created_at')

    # Retrieve wishlist items from the session
    wishlist_ids = request.session.get('wishlist', [])
    wishlist_items = item_tb.objects.filter(id__in=wishlist_ids).prefetch_related('images')

    # Retrieve cart data from the session (same as in view_cart)
    cart = request.session.get('cart', {})  # Default to an empty dictionary if no cart
    cart_items = []
    item_ids = []

    # Collect item ids and quantities from the cart
    for item_id, quantity in cart.items():
        if isinstance(quantity, int) and quantity > 0:
            item_ids.append(item_id)  # Add valid item_id to the list
        else:
            messages.warning(request, f"Invalid quantity for item ID {item_id}. Skipping item.")

    # Retrieve the items in bulk based on the cart's item IDs
    if item_ids:
        items_in_cart = item_tb.objects.filter(id__in=item_ids)

        # Add selected quantity and total price to the items
        for item in items_in_cart:
            quantity = cart.get(str(item.id), 0)  # Ensure quantity is correctly matched
            item.selected_quantity = quantity
            item.total_price = item.price_kg * quantity
            cart_items.append(item)

    # Set cart count in the buyer portal (similar to view_cart)
    cart_count = len(cart_items) if cart_items else 0  # Ensure cart_count is 0 if no items

    # Prepare context for the template
    context = {
        'buyer_name': buyer_name,
        'items': items,
        # 'data':data,
        'fruits': fruits,
        'vegetables': vegetables,
        'exotic_fruits': exotic_fruits,
        'exotic_vegetables': exotic_vegetables,
        'mushrooms': mushrooms,
        'salads': salads,
        'wishlist_items': wishlist_items,
        'buyer': buyer,
        'images': image,
        'dummy_array': [1, 2, 3],
        'cart_count': cart_count,  # Updated cart_count based on the actual cart
    }

    # Render the buyer portal template
    return render(request, 'buyer.html', context)

def item_details(request, product_id=None):
    buyer_id = request.session.get('buyer_id')  # Retrieve buyer_id from session
    cart_count=get_cart_count(request)
    items = item_tb.objects.all()
    selected_product = get_object_or_404(item_tb, id=product_id) if product_id else None

    # Get similar products (same type, excluding the current one)
    similar_products = items.filter(type=selected_product.type).exclude(id=selected_product.id) if selected_product else []

    context = {
        'selected_product': selected_product,
        'similar_products': similar_products,
        'cart_count':cart_count,
        'items': items,
        'buyer_id': buyer_id,  # Make sure to pass buyer_id to the template
    }

    return render(request, 'item_details.html', context)

def enrich_orders(order_items):
    enriched_orders = []
    last_order_id = None  # Track last processed order ID
    
    for order_item in order_items:
        enriched_order = {
            "order_item": order_item,
            "buyer_name": "N/A",
            "buyer_phone": "N/A",
            "buyer_address": "N/A",
            "seller_name": "N/A",
            "total_price": order_item.total_price,
            "order_created_at": None,  # Will be set only once per order
            "agent_name": "No agent assigned",  # Default agent name
            "is_cancelled": order_item.order.is_cancelled,  # Add cancellation status to the enriched order
        }

        # Set created_at for the first item of each order
        if last_order_id != order_item.order.id:
            enriched_order["order_created_at"] = order_item.order.created_at
            last_order_id = order_item.order.id

        try:
            # Fetch buyer details
            buyer_queryset = order_item.order.user.buyersignup_tb_set.all()
            if buyer_queryset.exists():
                buyer = buyer_queryset.first()
                enriched_order["buyer_name"] = buyer.name
                enriched_order["buyer_phone"] = buyer.mobileNo
                enriched_order["buyer_address"] = buyer.address

            # Fetch seller details if item exists
            if order_item.item and order_item.item.seller:
                seller = order_item.item.seller
                enriched_order["seller_name"] = seller.name

            # Fetch agent name if the order item has an associated delivery agent
            # Fetch the DeliveryAssignment related to the current order_item
            delivery_assignment = DeliveryAssignment.objects.filter(order_item=order_item).first()
            if delivery_assignment:
                enriched_order["agent_name"] = delivery_assignment.delivery_agent.name
        except Exception as e:
            print(f"Error retrieving details for OrderItem {order_item.id}: {e}")

        enriched_orders.append(enriched_order)
    
    return enriched_orders


def deliveryAgent(request):
    # Ensure the agent is logged in
    agent_id = request.session.get('agent_id')
    if not agent_id:
        return redirect('/')  # Redirect to login page if not logged in

    try:
        agent = deliveryagentSignUp_tb.objects.get(id=agent_id)
    except deliveryagentSignUp_tb.DoesNotExist:
        return redirect('/')  # Redirect to login if agent doesn't exist

    # Handle the form submission to update agent's details
    if request.method == 'POST':
        # Update profile image
        profile_image = request.FILES.get('profile_image')
        if profile_image:
            if not profile_image.content_type.startswith('image/'):
                messages.error(request, "Please upload a valid image file.")
            else:
                agent.profile_image_agent = profile_image

        # Update other details (mobile number, address, etc.)
        agent.mobileNo = request.POST.get('mobileNo')
        agent.address = request.POST.get('address')
        agent.driving_license_no = request.POST.get('driving_license_no')
        agent.vehicle_no = request.POST.get('vehicle_no')
        agent.preferred_location = request.POST.get('preferred_location')

        # Save the updated agent's information to the database
        agent.save()
        messages.success(request, "Your profile has been updated successfully.")

        return redirect('deliveryAgent')  # Redirect to avoid resubmitting form on refresh

    # Assign only 'picked_up' orders that do not have an assignment yet
    unassigned_picked_up_orders = OrderItem.objects.filter(status='picked_up').exclude(
        id__in=DeliveryAssignment.objects.values_list('order_item_id', flat=True)
    )

    for order_item in unassigned_picked_up_orders:
        DeliveryAssignment.objects.create(
            delivery_agent=agent,
            order_item=order_item
        )

    # Fetch counts
    pending_orders_count = OrderItem.objects.filter(status='pending', order__is_cancelled=False).distinct().count()
    active_deliveries_count = OrderItem.objects.filter(status='picked_up', deliveryassignment__delivery_agent=agent).distinct().count()
    completed_orders_count = OrderItem.objects.filter(status='delivered', deliveryassignment__delivery_agent=agent).distinct().count()

    # Fetch and enrich pending orders
    pending_orders = OrderItem.objects.select_related('item__seller', 'order__user').filter(
        status='pending', order__is_cancelled=False
    )
    enriched_pending_orders = enrich_orders(pending_orders)

    # Fetch orders assigned to this agent
    picked_up_orders = OrderItem.objects.filter(
        status='picked_up',
        deliveryassignment__delivery_agent=agent
    )
    enriched_picked_up_orders = enrich_orders(picked_up_orders)

    # Fetch completed orders & sort by latest assigned_at (approximates delivery time)
    completed_orders = OrderItem.objects.filter(
        status='delivered',
        deliveryassignment__delivery_agent=agent
    ).order_by('-deliveryassignment__assigned_at')  # Orders sorted by last assigned (approximate last delivered first)

    enriched_completed_orders = enrich_orders(completed_orders)

    # Group orders
    grouped_pending_orders = {
        order_id: {
            'order_items': items_list,
            'total_price': sum(item['total_price'] for item in items_list),
            'grand_total': items_list[0]['order_item'].order.grand_total if items_list else 0,
        }
        for order_id, items in groupby(enriched_pending_orders, key=lambda x: x['order_item'].order.id)
        for items_list in [list(items)]  # Convert iterator to list
    }

    grouped_picked_up_orders = {
        order_id: {
            'order_items': items_list,
            'grand_total': items_list[0]['order_item'].order.grand_total if items_list else 0,
        }
        for order_id, items in groupby(enriched_picked_up_orders, key=lambda x: x['order_item'].order.id)
        for items_list in [list(items)]  # Convert iterator to list
    }

    grouped_completed_orders = {
        order_id: {
            'order_items': items_list,
            'grand_total': items_list[0]['order_item'].order.grand_total if items_list else 0,
        }
        for order_id, items in groupby(
            enriched_completed_orders,  # Already sorted list
            key=lambda x: x['order_item'].order.id
        )
        for items_list in [list(items)]  # Convert iterator to list
    }

    # Context data for template
    context = {
        'name': agent.name,
        'email': agent.email,
        'mobileNo': agent.mobileNo,
        'address': agent.address,
        'driving_license_no': agent.driving_license_no,
        'vehicle_no': agent.vehicle_no,
        'preferred_location': agent.preferred_location,
        'profile_image': agent.profile_image_agent.url if agent.profile_image_agent else 'default_image_url',
        'grouped_orders': grouped_pending_orders,
        'pending_orders_count': pending_orders_count,
        'active_deliveries_count': active_deliveries_count,
        'completed_orders_count': completed_orders_count,
        'grouped_picked_up_orders': grouped_picked_up_orders,
        'grouped_completed_orders': grouped_completed_orders,
    }
    return render(request, 'deliveryAgent.html', context)

def signUp(request):
    if request.method == 'POST':
        ac_type = request.POST.get('dropdown_value')  # Account type (Seller, Buyer, Delivery Agent)
        name = request.POST.get('name')
        email = request.POST.get('email')
        mobile_no = request.POST.get('mob')
        password = request.POST.get('pswd')
        confirm_password = request.POST.get('cpswd')
        address = request.POST.get('address')
        opt_address1 = request.POST.get('address1')
        opt_address2 = request.POST.get('address2')

        # Validate mandatory fields
        if not all([name, email, mobile_no, password, confirm_password, address]):
            return render(request, 'Registration_portal.html')

        if password != confirm_password:
            return render(request, 'Registration_portal.html')

        if User.objects.filter(username=name).exists():
            messages.error(request, "The username is already taken. Please choose another.")
            return render(request, 'Registration_portal.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "The email is already registered. Please use a different email.")
            return render(request, 'Registration_portal.html')

        try:
            with transaction.atomic():
                # Create User object
                user = User.objects.create_user(username=name, email=email, password=password)

                if ac_type == 'Seller':
                    gst_no = request.POST.get('gst_no')
                    shop_name = request.POST.get('shop_name')
                
                    sellerSignUp_tb.objects.create(
                        user=user,
                        ac_type=ac_type,
                        name=name,
                        email=email,
                        mobileNo=mobile_no,
                        gst_no=gst_no if gst_no else None,
                        shop_name=shop_name if shop_name else None,
                        address=address,
                        is_approved=False
                    )
                    request.session['seller_name']=name

                    ActivityLog.objects.create(
                        activity_type='new_user',
                        description=f"New {ac_type} account registered: {name} ({email})",
                        user=user
                    )

                elif ac_type == 'Buyer':
                    # Check for duplicate buyer accounts
                    if buyerSignUp_tb.objects.filter(name=name).exists():
                        messages.error(request, f"A buyer account with the name '{name}' already exists.")
                        user.delete()
                        return render(request, 'Registration_portal.html')

                    buyer=buyerSignUp_tb.objects.create(
                        user=user,
                        ac_type=ac_type,
                        name=name,
                        email=email,
                        mobileNo=mobile_no,
                        address=address,
                        opt_address1=opt_address1,
                        opt_address2=opt_address2,
                        password=password 
                         )
                    # Store buyer data in the session
                    request.session['buyer_id']=buyer.id
                    request.session['buyer_name'] = name
                    request.session['buyer_address'] = address

                    ActivityLog.objects.create(
                        activity_type='new_user',
                        description=f"New {ac_type} account registered: {name} ({email})",
                        user=user
                    ) 

                    return redirect('buyer_portal')  # Redirect to buyer portal

                elif ac_type == 'Delivery Agent':
                    dob = request.POST.get('dob')
                    driving_license_no = request.POST.get('driving_license_no')
                    vehicle_no = request.POST.get('vehicle_no')
                    preferred_location = request.POST.get('preferred_location')

                    agent=deliveryagentSignUp_tb.objects.create(
                        user=user,
                        ac_type=ac_type,
                        name=name,
                        email=email,
                        mobileNo=mobile_no,
                        address=address,
                        dob=dob if dob else None,
                        driving_license_no=driving_license_no if driving_license_no else None,
                        vehicle_no=vehicle_no if vehicle_no else None,
                        preferred_location=preferred_location if preferred_location else None,
                        is_approved=False
                    )
                    request.session['agent_id']=agent.id
                    request.session['agent_name'] = name

                    ActivityLog.objects.create(
                        activity_type='new_user',
                        description=f"New {ac_type} account registered: {name} ({email})",
                        user=user
                    )

                else:
                    messages.error(request, "Invalid account type selected.")
                    user.delete()
                    return render(request, 'Registration_portal.html')
                
                # Log the new user registration activity
                ActivityLog.objects.create(
                    activity_type='new_user',
                    description=f"New {ac_type} account registered: {name} ({email})",
                    user=user
                )

                messages.success(request, f"{ac_type} account created successfully! Awaiting admin approval.")
                return render(request,'approval_pending.html')  # Redirect to approval pending page

        except IntegrityError as e:
            messages.error(request, f"An error occurred: {e}")
            return render(request, 'Registration_portal.html')

    return render(request, 'Registration_portal.html')

def item_save(request):
    # Check if the seller is logged in via session
    seller_name = request.session.get('seller_name')
    if not seller_name:
        messages.error(request, "You must be logged in as a seller to add items.")
        return redirect('/')  # Redirect to the login page if the session is missing

    # Fetch the seller's details using the session
    try:
        seller = sellerSignUp_tb.objects.get(name=seller_name)
    except sellerSignUp_tb.DoesNotExist:
        messages.error(request, "Seller account not found.")
        return redirect('/')  # Redirect to login if the seller does not exist

    # Handle the item save logic
    if request.method == 'POST' and 'images' in request.FILES:
        type = request.POST['type']
        if not type:
            raise ValueError("Type must be selected")
        
        name = request.POST['item_name']
        quantity = int(request.POST['quantity'])
        category = request.POST['category']
        if not category:
            raise ValueError("Category must be selected")
        
        price_kg = float(request.POST['price_kg'])
        bulk_num = request.POST['bulk']
        bulk_price = float(request.POST['bulk_price'])
        offer = request.POST.get('offer')  # Using .get() to avoid KeyError
        if offer == '':
            offer = None  # If offer is an empty string, set it to None
        ex_date = request.POST['ex_date']
        specification = request.POST['specification']
        images = request.FILES.getlist('images')  # Get list of uploaded images

        # Save item and images
        try:
            with transaction.atomic():  # Ensure that all operations succeed or fail together
                new_item = item_tb(
                    seller=seller,
                    type=type,
                    name=name,
                    quantity=quantity,
                    category=category,
                    price_kg=price_kg,
                    bulk_num=bulk_num,
                    bulk_price=bulk_price,
                    offfer=offer,
                    ex_date=ex_date,
                    specification=specification
                )
                print(type)
                new_item.save()

                # Save uploaded images
                for image in images:
                    print(f"Saving image: {image.name}")
                    item_image = ItemImage(item=new_item, image=image)
                    item_image.save()

            return redirect('item_add')
        except Exception as e:
            print("Error saving item:", e)
            return render(request, 'seller.html', {'error_message': 'An error occurred while saving the item.'})

    return render(request, 'seller.html')

def db1_wishlist(request, id):
    # print("Adding item to wishlist")
    item = item_tb.objects.get(id=id)
    # print(f"Item ID: {id}")
    if 'wishlist' not in request.session:
        request.session['wishlist'] = []
    if id not in request.session['wishlist']:
        request.session['wishlist'].append(id)
        request.session.modified = True
        print(f"Wishlist updated: {request.session['wishlist']}")
    return redirect('buyer_portal')

def view_cart(request, id=None):
    # Use the id passed in the URL or from the session if id is None
    buyer_id = id or request.session.get('buyer_id')

    if not buyer_id:
        messages.error(request, "You need to log in to access your profile.")
        return redirect('/')  # Redirect to login page if no session or id

    try:
        buyer = buyerSignUp_tb.objects.get(id=buyer_id)
    except buyerSignUp_tb.DoesNotExist:
        messages.error(request, "Buyer not found.")
        return redirect('/')

    # Handle address update via POST request
    if request.method == 'POST' and 'address' in request.POST:
        new_address = request.POST.get('address', '').strip()
        if new_address:
            try:
                buyer.address = new_address
                buyer.save()
                messages.success(request, "Address updated successfully.")
            except Exception as e:
                messages.error(request, f"Error updating address: {e}")
        else:
            messages.error(request, "Address cannot be empty.")

    # Handle cart quantity update via POST request
    if request.method == 'POST' and 'item_id' in request.POST and 'quantity' in request.POST:
        item_id = request.POST.get('item_id')
        new_quantity = int(request.POST.get('quantity', 0))  # Ensure quantity is an integer
        cart = request.session.get('cart', {})

        # Validate the item and quantity
        if item_id in cart and new_quantity >= 1:
            cart[item_id] = new_quantity  # Update quantity in session cart
            request.session['cart'] = cart  # Save the updated cart back to session
            messages.success(request, f"Item {item_id} quantity updated to {new_quantity}.")
        else:
            messages.error(request, "Invalid item or quantity.")

    # Retrieve cart data from session
    cart = request.session.get('cart', {})  # Default to an empty dictionary if no cart
    cart_items = []
    item_ids = []

    # Collect item ids and quantities from the cart
    for item_id, quantity in cart.items():
        if isinstance(quantity, int) and quantity > 0:
            item_ids.append(item_id)  # Add valid item_id to the list
        else:
            messages.warning(request, f"Invalid quantity for item ID {item_id}. Skipping item.")

    # Retrieve the items in bulk based on the cart's item IDs
    if item_ids:
        items = item_tb.objects.filter(id__in=item_ids)

        # Add selected quantity and total price to the items
        for item in items:
            quantity = cart.get(str(item.id), 0)  # Ensure quantity is correctly matched
            item.selected_quantity = quantity
            item.total_price = item.price_kg * quantity
            cart_items.append(item)

    # Get the cart count using the get_cart_count function
    cart_count = get_cart_count(request)  # Call the function here
    
    # Render the cart page with the necessary context
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'buyer_name': buyer.name,
        'buyer_address': buyer.address,
        'buyer_id': buyer_id,
        'cart_count': cart_count,  # Pass cart_count here
    })


def remove_item_from_cart(request, item_id):
    cart = request.session.get('cart', {})
    
    # If the item exists in the cart, remove it
    if str(item_id) in cart:
        del cart[str(item_id)]
        request.session.modified = True  # Mark session as modified
    # Redirect to the cart page after removal
    return redirect('view_cart')

def db1_cart(request, id):
    # Initialize the cart in the session if it doesn't exist or is invalid
    if 'cart' not in request.session or not isinstance(request.session['cart'], dict):
        request.session['cart'] = {}
    cart = request.session['cart']

    try:
        # Get the item by ID
        item = item_tb.objects.get(id=id)
    except item_tb.DoesNotExist:
        raise Http404("Item not found")

    # Check stock availability
    if item.quantity == 0:
        # Item is out of stock, return an appropriate response
        return redirect('out_of_stock')  # Replace with actual URL to handle out of stock

    # Add or update the item in the cart
    item_id_str = str(id)
    if item_id_str not in cart:
        cart[item_id_str] = 1  # Add item with quantity 1
    else:
        # Check stock availability before increasing quantity
        if cart[item_id_str] < item.quantity:
            cart[item_id_str] += 1
        else:
            messages.error(request, "Item quantity exceeds stock.")  # Optional message if stock is exceeded

    # Mark the session as modified
    request.session.modified = True

    # Redirect back to the buyer portal or a specified redirect URL
    redirect_to = request.GET.get('redirect_to', 'buyer_portal')
    return redirect(redirect_to)

def update_cart_quantities(request):
    if request.method == 'POST':
        try:
            # Get item IDs and quantities from the POST data
            item_ids = request.POST.getlist('item_ids')
            quantities = request.POST.getlist('quantity')

            # Update the cart item quantities
            for item_id, quantity in zip(item_ids, quantities):
                # Find the cart item by ID
                cart_item = item_tb.objects.get(id=item_id)

                # Subtract the ordered quantity from the available quantity
                new_quantity = cart_item.quantity - int(quantity)

                # Ensure the quantity doesn't go below zero
                if new_quantity >= 0:
                    cart_item.quantity = new_quantity
                    cart_item.save()
                else:
                    messages.error(request, f"Not enough stock for {cart_item.name}.")
                    return redirect('cart')  # Redirect back if there are errors

            messages.success(request, "Cart updated successfully!")
            return redirect('cart')  # Redirect to the cart page or wherever you want

        except Exception as e:
            messages.error(request, f"Error updating cart: {str(e)}")
            return redirect('cart')  # Handle errors and redirect back to the cart page

    return redirect('cart')  # If the method is not POST, redirect back to the cart

def remove_from_wishlist(request, item_id):
    wishlist = request.session.get('wishlist', [])
    if item_id in wishlist:
        wishlist.remove(item_id)
        request.session['wishlist'] = wishlist  # Update the session data
    return redirect('buyer_portal')  # Redirect back to the wishlist page

def clear_wishlist(request):
    if request.method == 'POST':
        request.session['wishlist'] = []  # Clear the wishlist
        messages.success(request, "Wishlist cleared successfully.")
    return redirect('buyer_portal')


def order_now(request):
    # Retrieve buyer_id from session
    buyer_id = request.session.get('buyer_id')
    if not buyer_id:
        messages.error(request, "You need to log in to place an order.")
        return redirect('/')  # Redirect to the login page if buyer_id is not in session

    # Retrieve the buyer's details using buyer_id
    try:
        buyer = buyerSignUp_tb.objects.get(id=buyer_id)
    except buyerSignUp_tb.DoesNotExist:
        messages.error(request, "Buyer not found.")
        return redirect('/')  # Redirect to home page if buyer does not exist

    # Handle the order placement when POST request is made
    if request.method == "POST":
        selected_items = request.POST.get('selected_items', '')
        quantities = request.POST.get('quantities', '')
        print(f"Selected Items: {selected_items}")
        print(f"Quantities: {quantities}")

        if not selected_items or not quantities:
            messages.error(request, "Invalid data submitted. No items selected.")
            return redirect('view_cart')  # Redirect to the cart page with error

        try:
            item_ids = [int(id) for id in selected_items.split(',') if id.isdigit()]
            quantities = [int(qty) for qty in quantities.split(',') if qty.isdigit()]
        except ValueError:
            messages.error(request, "Invalid data format.")
            return redirect('view_cart')  # Redirect to the cart page with error

        if len(item_ids) != len(quantities):
            messages.error(request, "Mismatched items and quantities.")
            return redirect('view_cart')  # Redirect to the cart page with error

        total_amount = Decimal(0)
        gst_amount = Decimal(0)
        order_items = []

        # Use transaction to ensure that all DB operations are atomic
        with transaction.atomic():
            # Collect the items and their prices
            for item_id, quantity in zip(item_ids, quantities):
                try:
                    item = item_tb.objects.get(id=item_id)

                    # Check if the selected quantity is greater than the available stock
                    if quantity > item.quantity:
                        messages.error(request, f"Selected quantity for item ID {item_id} exceeds available stock. Available quantity: {item.quantity}.")
                        return redirect('view_cart')  # Redirect to the cart page with error

                    if quantity <= 0:
                        messages.error(request, f"Invalid quantity for item ID {item_id}. Quantity must be greater than zero.")
                        return redirect('view_cart')  # Redirect to the cart page with error

                    # Get the price and calculate the total
                    item_price = item.offer_price()  # Assuming this method exists
                    total_price = item_price * quantity
                    order_items.append({
                        "item": item,
                        "quantity": quantity,
                        "price": item_price,
                        "total_price": total_price,
                    })

                    total_amount += Decimal(total_price)

                except item_tb.DoesNotExist:
                    messages.error(request, f"Item with ID {item_id} does not exist.")
                    return redirect('view_cart')  # Redirect to the cart page with error

            # Calculate GST and Grand Total
            gst_amount = total_amount * Decimal(0.18)  # 18% GST
            grand_total = total_amount + gst_amount

            # Create the order
            order = Order(
                user=buyer.user,  # Use the buyer object
                total_amount=total_amount,
                gst_amount=gst_amount,
                grand_total=grand_total
            )
            order.save()

            # Create OrderItems associated with the Order
            for order_item in order_items:
                OrderItem.objects.create(
                    order=order,
                    item=order_item['item'],
                    quantity=order_item['quantity'],
                    price=order_item['price'],
                    total_price=order_item['total_price'],
                    status='pending'  # Set the status to 'pending' by default
                )

            # Reduce the item quantities after the order is successfully created
            for order_item in order_items:
                item = order_item['item']
                quantity = order_item['quantity']
                item.reduce_quantity(quantity)  # Reduce the stock based on the quantity ordered
            return redirect('order_confirmation', order_id=order.id)

    # If not a POST request, return an error message
    messages.error(request, "Invalid request method.")
    return redirect('view_cart')  # Redirect to the cart page with error


def order_confirmation(request, order_id):
    # Get buyer_id from session, ensure it's converted to integer if needed
    buyer_id = request.session.get('buyer_id')

    if not buyer_id:
        messages.error(request, "You need to log in to view the order.")
        return redirect('/')  # Redirect to login if not logged in

    try:
        buyer = buyerSignUp_tb.objects.get(id=buyer_id)
    except buyerSignUp_tb.DoesNotExist:
        messages.error(request, "Buyer not found.")
        return redirect('/')  # Redirect to home if buyer doesn't exist

    # Fetch the correct order using order_id
    order = get_object_or_404(Order, id=order_id, user=buyer.user)

    # Get all items in this order
    order_items = OrderItem.objects.filter(order=order)

    # Check if any items have been delivered
    completed_orders = order_items.filter(status='delivered')
    
    # Get the cart count using the get_cart_count function
    cart_count = get_cart_count(request)  # Call the function here
    

    if request.method == "POST":
        if not completed_orders.exists():
            messages.error(request, "You can only rate delivered orders.")
            return redirect('order_confirmation', order_id=order.id)

        try:
            rating = int(request.POST.get('rating'))
            review = request.POST.get('review', '').strip()
        except ValueError:
            messages.error(request, "Invalid rating value.")
            return redirect('order_confirmation', order_id=order.id)

        for item in completed_orders:
            # Check if a review already exists
            existing_review = RatingReview.objects.filter(buyer=buyer, item=item.item).first()
            if existing_review:
                existing_review.rating = rating
                existing_review.review = review
                existing_review.save()
            else:
                RatingReview.objects.create(
                    buyer=buyer,
                    item=item.item,
                    rating=rating,
                    review=review
                )
        messages.success(request, "Thank you for your feedback!")
        return redirect('order_confirmation', order_id=order.id)

    # Pass completed_orders_exist to the template
    return render(request, 'order_confirmation.html', {
        'order': order,
        'order_items': order_items,
        'completed_orders_exist': completed_orders.exists(),
        'cart_count': cart_count,
         'buyer_id': buyer_id,
    })

def delete_review(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(RatingReview, id=review_id)
        
        # Check if the logged-in user owns the review
        buyer_id = request.session.get('buyer_id')
        if review.buyer_id == buyer_id:
            review.delete()
            messages.success(request, "Review deleted successfully.")
        else:
            messages.error(request, "You are not authorized to delete this review.")
        
    return redirect('settings_buyer', id=buyer_id)

# Function to calculate the cart count
def get_cart_count(request):
    """
    This function returns the number of items in the cart
    stored in the session.
    """
    # Get the cart from the session (default to an empty dictionary if not present)
    cart = request.session.get('cart', {})
    
    # Return the number of items in the cart (the number of distinct item IDs)
    return len(cart)

def view_orders(request):
    # Get the buyer_id from the session or fallback to None
    buyer_id = request.session.get('buyer_id')
    
    # Redirect if there's no buyer_id in the session
    if not buyer_id:
        return redirect('/')
    
    orders = []

    if request.user.is_superuser:
        orders = Order.objects.filter(is_cancelled=False)
    else:
        try:
            # Fetch the buyer using the buyer_id
            buyer = buyerSignUp_tb.objects.get(id=buyer_id)
            orders = Order.objects.filter(user=buyer.user, is_cancelled=False)
        except buyerSignUp_tb.DoesNotExist:
            return redirect('/')  # If buyer doesn't exist, redirect

   
    # Get the cart count using the get_cart_count function
    cart_count = get_cart_count(request)  # Call the function here
    
    # Pass the required data to the template
    context = {
        'orders': orders,
        'buyer_id': buyer_id,  # Pass the buyer_id to the template for URL generation
        'cart_count': cart_count  # Pass the cart count to the template
    }

    return render(request, 'view_orders.html', context)


def products_on_offer(request):
    buyer_id = request.session.get('buyer_id')
    # Get the offer percentage from the query parameter
    offer_percentage = request.GET.get('offer')
    cart_count = get_cart_count(request)  # Call the function here

    try:
        if offer_percentage:
            # Convert to integer for comparison
            offer_percentage = int(offer_percentage)
            # Filter products with the offer percentage less than or equal to the specified value
            products = item_tb.objects.filter(offfer__lte=offer_percentage)
        else:
            # Default behavior: Show all products with any offer
            products = item_tb.objects.filter(offer__isnull=False).exclude(offer='')

    except ValueError:
        # Handle invalid query parameters
        return HttpResponseBadRequest("Invalid offer percentage.")

    context = {
        'products': products,
        'cart_count':cart_count,
        'buyer_id':buyer_id,
        'offer_percentage': offer_percentage,  # Pass it to the template for display
    }  
    return render(request, 'products_on_offer.html', context)

def admin_login(request):
    return render(request,'admin_login.html')

def admin_fun(request):
    if request.method=='POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            admin=admin_tb.objects.get(username=username)

            if admin.password==password:
                request.session['username'] = username
                return redirect('admin_portal')
            else:
                messages.error(request,'Incorrect password')
            
        except admin_tb.DoesNotExist:
                messages.error(request,'User not found')
    return redirect('admin_login')

def approve_account(request, account_type, account_id):
    if account_type == 'seller':
        account = get_object_or_404(sellerSignUp_tb, id=account_id)
    elif account_type == 'da':
        account = get_object_or_404(deliveryagentSignUp_tb, id=account_id)
    else:
        return redirect('admin_portal')  # Redirect if the account type is invalid
    
    if not account.is_approved:
        account.is_approved = True
        account.save()
    
    return redirect('admin_portal')

def edit_account(request, account_type, account_id):
    if account_type == 'seller':
        account = get_object_or_404(sellerSignUp_tb, id=account_id)
    elif account_type == 'buyer':
        account = get_object_or_404(buyerSignUp_tb, id=account_id)
    elif account_type == 'da':
        account = get_object_or_404(deliveryagentSignUp_tb, id=account_id)
    else:
        return redirect('admin_portal')  # Redirect if the account type is invalid
    
     # Format the date of birth for the 'da' account type
    if account_type == 'da' and account.dob:
        # Ensure dob is in the correct format for the HTML date input field
        account.dob = account.dob.strftime('%Y-%m-%d') if isinstance(account.dob, datetime) else str(account.dob)
    if request.method == 'POST':
        account.name = request.POST.get('name')
        account.email = request.POST.get('email')
        account.mobileNo = request.POST.get('mobileNo')
        account.address = request.POST.get('address')

        if account_type == 'seller':
            account.gst_no = request.POST.get('gst_no')
            account.shop_name = request.POST.get('shop_name')
        elif account_type == 'da':
            account.dob = request.POST.get('dob')
            account.driving_license_no = request.POST.get('driving_license_no')
            account.vehicle_no = request.POST.get('vehicle_no')
            account.preferred_location = request.POST.get('preferred_location')

        account.save()
        return redirect('admin_portal')
    
    return render(request, 'edit_account.html', {'account': account, 'account_type': account_type})

def delete_account(request, account_id, account_type):
    if request.method == 'POST':
        try:
            if account_type == 'seller':
                account = sellerSignUp_tb.objects.get(id=account_id)
            elif account_type == 'buyer':
                account = buyerSignUp_tb.objects.get(id=account_id)
            elif account_type == 'da':
                account = deliveryagentSignUp_tb.objects.get(id=account_id)
            else:
                messages.error(request, "Invalid account type.")
                return redirect('admin_portal')

            # Delete the account
            account.delete()
            messages.success(request, f"{account_type.capitalize()} account deleted successfully.")
            return redirect('admin_portal')

        except ObjectDoesNotExist:
            messages.error(request, f"{account_type.capitalize()} account does not exist.")
            return redirect('admin_portal')
    else:
        return redirect('admin_portal')
def logout(request):
    # Get the buyer_id from the session (if it's a buyer)
    buyer_id = request.session.get('buyer_id')
    
    # Clear the entire session (this will flush the session for all users)
    request.session.flush()

    # If the user was a buyer, restore their cart
    if buyer_id:
        # Retrieve and preserve the cart before the session is flushed
        buyer_cart = request.session.get('cart', {})
        
        # Reinitialize the session
        request.session.create()

        # Set the cart back for the buyer in the new session
        request.session['cart'] = buyer_cart
        request.session.modified = True

    # Redirect to the homepage or login page
    return redirect('/')
def cancel_order(request, order_id):
    # Retrieve the order and ensure it belongs to the logged-in user
    buyer_id = request.session.get('buyer_id')
    buyer = buyerSignUp_tb.objects.get(id=buyer_id)
    order = get_object_or_404(Order, id=order_id, user=buyer.user)

    # Check if the order is cancellable
    # Cancel the order
    if order.is_cancellable:
       order.is_cancelled = True
       order.cancelled_at = now()  # Ensure this is being set
       order.save()
       print(order.is_cancelled, order.cancelled_at)

       messages.success(request, "Your order has been successfully cancelled.")
    else:
        messages.error(request, "Order cancellation is no longer allowed.")
    
    # Redirect to a relevant page, such as order details or orders list
    return redirect('view_orders')  # Replace with the correct view name (e.g., 'order_details' or 'view_orders')

@csrf_exempt
def update_order_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            new_status = data.get('status')


            # Validate inputs
            if not order_id or not new_status:
                print("Invalid input data")
                return JsonResponse({'success': False, 'error': 'Invalid input data'})

            # Fetch all OrderItems for the given order_id
            order_items = OrderItem.objects.filter(order__id=order_id)
            if not order_items.exists():
                print("Order not found")
                return JsonResponse({'success': False, 'error': 'Order not found'})

            # Update the status for each order item
            order_items.update(status=new_status)

            print(f"Order status updated for order_id={order_id}")
            return JsonResponse({
                'success': True,
                'order_id': order_id,
                'new_status': new_status,
            })
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    return redirect('deliveryAgent')