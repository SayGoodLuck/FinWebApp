from django.db import models

class Users(models.Model):
    id = models.AutoField(primary_key=True)
    password = models.CharField(max_length=120)
    login = models.CharField(max_length=120)


class Cards(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    card_type = models.TextField()
    card_name = models.CharField(max_length=120)
    balance = models.IntegerField(default=0)
    currency = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120, default='Default Bank')


class Transactions(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    card_id = models.ForeignKey(Cards, on_delete=models.CASCADE)
    category_name = models.TextField(null=True)
    date = models.DateField()
    description = models.TextField()
    amount = models.IntegerField()