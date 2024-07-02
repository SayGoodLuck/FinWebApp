from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.decorators import api_view


@api_view(['POST'])
def register(request):
    if request.content_type != 'application/json':
        return JsonResponse({'error': 'Unsupported Content-Type'}, status=400)
    data = request.data
    form = UserCreationForm(data)
    if form.is_valid():
        form.save()
        return JsonResponse("User Created", safe=False)
    else:
        return JsonResponse({'error': form.errors})


@api_view(['POST'])
def login(request):
    if request.content_type != 'application/json':
        return JsonResponse({'error': 'Unsupported Content-Type'}, status=400)
    data = request.data
    username = data.get('username')
    password = data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        auth_login(request, user)
        return JsonResponse("Login Successful", safe=False)
    else:
        return JsonResponse({'error': 'Invalid Credentials'})


def logout(request):
    auth_logout(request)


def page(request):
    return HttpResponse("MainPage")


@login_required
def home(request):
    return render(request, 'home.html')
