from django.contrib import admin
from .models import carouselImage

# Register your models here.
@admin.register(carouselImage)
class caroimgadmin(admin.ModelAdmin):
    list_display = ('title','created_at')