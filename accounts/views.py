from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm
from .models import Institution


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        institution = Institution.load()
        user = form.save(commit=False)
        user.is_active = not institution.require_approval
        user.save()
        if not user.is_active:
            messages.success(request, "Account created. An administrator will activate it; you can log in after that.")
            return redirect("accounts:login")
        login(request, user)
        messages.success(request, "Welcome. Start by adding the skills you have.")
        return redirect("catalog:my_skills")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
