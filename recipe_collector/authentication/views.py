from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm, RegisterForm


def registration_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        #if form.is_valid():
            #TODO : write a user creation view using forms

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, 'Invalid username or password')

    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})