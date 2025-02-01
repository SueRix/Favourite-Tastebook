from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'index.html'

class OurProductView(TemplateView):
    template_name = 'our_product.html'

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'