"""
URL configuration for FinWebApp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import auth_view
from .plaid_view import exchange_public_token, get_transactions, get_balances
from .dashboard import get_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', auth_view.register, name='register'),
    path('login/', auth_view.login, name='login'),
    path('exchange_public_token/', exchange_public_token, name='exchange_public_token'),
    path('transactions/sync/', get_transactions, name='get_transactions'),
    path('accounts/balance/get', get_balances, name='get_balances'),
    path('dashboard/', get_dashboard, name='get_dashboard'),
]
