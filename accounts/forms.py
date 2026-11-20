from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Department, Institution, User


class DomainCheckMixin:
    """Allow only the institution's email domains, if any are set."""

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        domains = Institution.load().domain_list()
        if domains and email.rsplit("@", 1)[-1].lower() not in domains:
            raise forms.ValidationError("Please use your university email address (" + ", ".join("@" + d for d in domains) + ").")
        return email


class DepartmentChoiceMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.select_related("faculty")
        self.fields["email"].required = True


class SignUpForm(DomainCheckMixin, DepartmentChoiceMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("display_name", "username", "email", "department", "designation", "field")


class ProfileForm(DomainCheckMixin, DepartmentChoiceMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "email", "department", "designation", "field")
