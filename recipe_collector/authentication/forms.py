from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=15, required=True, label="Username")
    first_name = forms.CharField(max_length=30, required=False, label='First Name')
    last_name = forms.CharField(max_length=30, required=False, label='Last Name')
    email = forms.EmailField(max_length=254, required=True, label='Email')
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='Password')
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True, label='Confirm Password')
