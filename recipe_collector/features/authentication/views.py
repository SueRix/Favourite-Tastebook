from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views import View
from .forms import LoginForm, RegisterForm



class RegisterView(View):
    @staticmethod
    def get(request):
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    @staticmethod
    def post(request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            email = form.cleaned_data.get('email')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
            else:
                user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name, last_name=last_name)
                login(request, user)
                return redirect('main_page')
        else:
            form = RegisterForm()

        return render(request, 'register.html', {'form': form})



class LoginView(View):
    @staticmethod
    def get(request):
        form = LoginForm()
        return render(request, 'login.html', {'form': form})

    @staticmethod
    def post(request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('main_page')
            else:
                form.add_error(None, 'Invalid username or password')

        else:
            form = LoginForm()

        return render(request, 'login.html', {'form': form})


class LogoutView(View):
    @staticmethod
    def post(request):
        logout(request)
        return redirect('login')
