from django.db import models
from datetime import date
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone   



# Create your models here.

class admin_tb(models.Model):
    username=models.CharField(max_length=50,unique=True)
    password=models.CharField(max_length=50)

class sellerSignUp_tb(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='sellerSignUp_tb')
    ac_type=models.CharField(max_length=100)
    name=models.CharField(max_length=50,unique=True)
    email=models.EmailField()
    mobileNo=models.CharField(max_length=15)
    password=models.CharField(max_length=50)
    address = models.TextField(null=True, blank=True) 
    gst_no=models.CharField(max_length=50,blank=True,null=True,default=None)
    shop_name=models.CharField(max_length=50,blank=True,null=True,default=None)
    profile_image_seller=models.ImageField(upload_to='profile_image/',null=True,blank=True)
    is_approved = models.BooleanField(default=False) 



    def __str__(self):
        return self.name
    
class buyerSignUp_tb(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ac_type=models.CharField(max_length=100)
    name=models.CharField(max_length=50,unique=True)
    email=models.EmailField()
    mobileNo=models.CharField(max_length=15)
    password=models.CharField(max_length=50)
    address = models.TextField(null=True, blank=True)
    opt_address1=models.TextField(null=True,blank=True)
    opt_address2=models.TextField(null=True,blank=True)
    profile_image_buyer=models.ImageField(upload_to='profile_image/',null=True,blank=True)

    
    

    def __str__(self):
        return self.name
    
class deliveryagentSignUp_tb(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ac_type=models.CharField(max_length=100)
    name=models.CharField(max_length=50,unique=True)
    email=models.EmailField()
    mobileNo=models.CharField(max_length=15)
    password=models.CharField(max_length=50)
    address = models.TextField(null=True, blank=True)
    dob=models.DateField(null=True, blank=True,default=None)
    driving_license_no=models.CharField(max_length=50, null=True,default=None)
    vehicle_no=models.CharField(max_length=50,null=True,default=None)
    preferred_location=models.CharField(max_length=200,null=True,default=None)
    profile_image_agent=models.ImageField(upload_to='profile_image/',null=True,blank=True)
    is_approved = models.BooleanField(default=False) 

    

    def __str__(self):
        return self.name
   
class item_tb(models.Model):
    seller = models.ForeignKey(sellerSignUp_tb, on_delete=models.CASCADE)
    type=models.CharField(max_length=100)
    name=models.CharField(max_length=100)
    quantity=models.IntegerField()
    category=models.CharField(max_length=100)
    price_kg=models.IntegerField()
    bulk_num=models.CharField(max_length=100)
    bulk_price=models.IntegerField()
    offfer=models.IntegerField(blank=True,null=True)
    ex_date=models.DateField()
    specification=models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True) 
   
     # Automatically set the current date and time
     

    def offer_price(self):
        if self.offfer:
            return round(self.price_kg*(1-self.offfer/100),2)
        return self.price_kg
    
    def is_expired(self):
           return self.ex_date < date.today()
    def is_near_expiry(self):
        delta = (self.ex_date - date.today()).days
        return 0 <= delta <= 7 
     
    def days_to_expiry(self):
        if self.ex_date:
            delta = (self.ex_date - date.today()).days
            return delta if delta >= 0 else 0
        return 0
    

    def reduce_quantity(self, quantity_to_reduce):
        print(f"Attempting to reduce {quantity_to_reduce} from item {self.name} (current quantity: {self.quantity})")
        if self.quantity >= quantity_to_reduce:
            self.quantity -= quantity_to_reduce
            self.save()
            print(f"Quantity reduced successfully. New quantity: {self.quantity}")
        else:
            raise ValueError("Not enough stock available")

    
    def __str__(self):
        return f"{self.name} - {self.quantity} in stock"
    
    class Meta:
        ordering = ["-created_at"]


   
    def __str__(self):
        return self.name
    @property
    def average_rating(self):
     reviews = RatingReview.objects.filter(item=self)
     if reviews.exists():
        return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
     return 0

    
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"Order {self.id} - {self.user.username}"
    @property
    def is_cancellable(self):
        return timezone.now() - self.created_at <= timedelta(minutes=10)
    def cancel(self):
        self.is_cancelled = True
        self.cancelled_at = timezone.now()
        self.save()




class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(item_tb, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('picked_up', 'picked_up'),('delivered','delivered')], default='pending')  # Set default to 'pending'

class ItemImage(models.Model):
    item = models.ForeignKey(item_tb, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='pictures/')

    def __str__(self):
        return f"Image for{self.item.name}"
    
class carouselImage(models.Model):
    title=models.CharField(max_length=100)
    image=models.ImageField(upload_to='carousel_picture/')
    discription=models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)    

    def __str__(self):
        return self.title

class ActivityLog(models.Model):
    ACTIVITY_CHOICES = [
        ('new_user', 'New User Registration'),
        ('order_placed', 'Order Placed'),
        ('complaint_submitted', 'Complaint Submitted'),
    ]
    
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_activity_type_display()} by {self.user.username} on {self.timestamp}"


class Complaint(models.Model):
    COMPLAINT_CHOICES = [
        ('general_inquiry', 'General Inquiry'),
        ('technical_support', 'Technical Support'),
        ('billing', 'Billing and Payments'),
        ('feedback', 'Provide Feedback'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=15)
    complaint_type = models.CharField(max_length=50, choices=COMPLAINT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.complaint_type}"
    
class RatingReview(models.Model):
    buyer = models.ForeignKey(buyerSignUp_tb, on_delete=models.CASCADE)
    item = models.ForeignKey(item_tb, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # Ratings between 1 to 5
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} - {self.rating} stars by {self.buyer.name}"

    

    

class DeliveryAssignment(models.Model):
    delivery_agent = models.ForeignKey(deliveryagentSignUp_tb, on_delete=models.CASCADE)
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    
