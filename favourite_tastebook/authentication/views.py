from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView


class RegisterView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = 'empty'

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class EmptyView(TemplateView):
    template_name = 'empty.html'