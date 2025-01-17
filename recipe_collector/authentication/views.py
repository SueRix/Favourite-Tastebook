from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .forms import LoginForm, RegisterForm
# from django.views import View
# from django.contrib.auth.mixins import LoginRequiredMixin



#testing decorator in browser(csrf error)
@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            email = form.cleaned_data.get('email')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name, last_name=last_name)
            login(request, user)
            return redirect('success')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


#for test decorator
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.POST.get('next') or request.GET.get('next') or 'success'
                return redirect(next_url)
            else:
                form.add_error(None, 'Invalid username or password')

    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

@csrf_exempt
def logout_view(request):
    if request.method == "POST" or "GET": #GET added to test in browser
        logout(request)
        return render(request, 'logout_redirect.html', {'redirect_url': 'login'})
    else:
        return redirect('login')



@login_required
def success_of_auth_view(request):
    return render(request, 'success_of_auth.html')

#logic to redirect on protected pages in future
#
# class ProtectedView(LoginRequiredMixin, View):
#     login_url = '/login/'
#     redirect_field_name = 'redirect_to'
#
#     def get(self, request):
#         return render(request, 'protected.html')