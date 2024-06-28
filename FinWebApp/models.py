from django.contrib.auth.models import User
from django.db import models


class PlaidToken(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cursor = models.CharField(max_length=255)


class Cards(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.CharField(max_length=255, default="bank")
    card_type = models.TextField(default="card")
    card_name = models.CharField(max_length=120, default="card")
    card_number = models.IntegerField(default=0)
    balance = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    currency = models.CharField(max_length=120)


class Transactions(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.CharField(max_length=255, default="bank")
    amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    merchant_name = models.CharField(max_length=120, default="merchant")
    category = models.TextField()
    date = models.DateField()


