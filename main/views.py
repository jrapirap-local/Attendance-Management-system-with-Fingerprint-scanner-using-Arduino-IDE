from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# Create your views here.

# def login_view(request):
#     if request.method == "POST":
#         username = request.POST["username"]
#         password = request.POST["password"]

#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             login(request, user)
#             return redirect("dashboard")
#         else:
#             return render(request, "login.html", {"error": "Invalid credentials"})

#     return render(request, "login.html")
    
def index(request):
    return render(request, 'index.html')
    
def builder(request):
    return render(request, 'builder.html')

def news(request):
    return render(request, 'news.html')

@login_required
def dashboard(request):
    return render(request, "Dashboard")

def user_logout(request):
    logout(request)
    return redirect("index")