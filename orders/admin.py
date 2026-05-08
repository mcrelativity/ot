from django.contrib import admin
from .models import Order, Tracking

class TrackingInline(admin.TabularInline):
    model = Tracking
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'client', 'status', 'created_at')
    search_fields = ('tracking_code', 'client')
    list_filter = ('status', 'created_at')
    readonly_fields = ('tracking_code', 'created_at')
    inlines = [TrackingInline]

@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin):
    list_display = ('order', 'date')
    search_fields = ('order__tracking_code', 'description')
