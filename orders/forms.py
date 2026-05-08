from django import forms
from .models import Order, Tracking

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client', 'description', 'status']
        widgets = {
            'client': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Cliente'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción del trabajo'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class TrackingForm(forms.ModelForm):
    class Meta:
        model = Tracking
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del hito o avance'}),
        }
