from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('login/', auth_views.LoginView.as_view(template_name='orders/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/order/create/', views.order_create, name='order_create'),
    path('dashboard/order/<int:pk>/', views.order_detail_admin, name='order_detail_admin'),
    path('dashboard/order/<int:pk>/update/', views.order_update, name='order_update'),
    path('dashboard/order/<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('dashboard/order/<int:pk>/add_tracking/', views.add_tracking, name='add_tracking'),
]
