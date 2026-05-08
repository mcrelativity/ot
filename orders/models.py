from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('FINALIZADA', 'Finalizada'),
    ]

    tracking_code = models.CharField(max_length=20, unique=True, blank=True)
    client = models.CharField(max_length=150)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDIENTE')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            last_order = Order.objects.order_by('-id').first()
            if last_order:
                last_id = last_order.id
                self.tracking_code = f"OT-{(last_id + 1):04d}"
            else:
                self.tracking_code = "OT-0001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_code} - {self.client}"

class Tracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trackings')
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Seguimiento: {self.order.tracking_code} - {self.date.strftime('%Y-%m-%d %H:%M')}"
