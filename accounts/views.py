from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

def builder2(request):
    return render(request, "builder2.html")

def login_view(request):
    error_message = None
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "login2.html", {"error": "Invalid credentials"})

    return render(request, "login2.html")

@login_required
def dashboard(request):
    return render(request, "admin/dashboard.html")

@login_required
def news(request):
    return render(request, "admin/news.html")

@login_required
def instructor(request):
    return render(request, "admin/instructor.html")

@login_required
def instructornew(request):
    return render(request, "admin/instructor-new.html")

@login_required
def sidebar(request):
    return render(request, "admin/sidebar.html")

@login_required
def attendance(request):
    return render(request, "admin/attendance.html")