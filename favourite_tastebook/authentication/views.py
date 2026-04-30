from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView


class RegisterView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    # use your profile app template here
    template_name = 'profile/confirm_delete.html'
    success_url = reverse_lazy('login')

    def get_object(self, queryset=None):
        # restrict user to delete only their own account
        return self.request.user