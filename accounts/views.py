# Standard library
import json
import random
import string
import time
from datetime import date, datetime
from itertools import chain

# Third-party
import pandas as pd
import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Django core
from django.contrib import messages
from django.contrib.auth import (
    authenticate, login, logout, get_user_model, update_session_auth_hash
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

# Local apps
from main.forms import UploadFileForm
from main.models import (
    Comlab, EquipmentBorrow, Report, Post, Comment,
    CustomUser, Subjects, Classroom, Schedule,
    Fingerprint, FingerprintCommand, FingerprintLogs,
    Course
)
from main.serializer import FingerprintSerializer

User = get_user_model()

def parse_date(date_str):
    formats = [
        "%Y-%m-%d",  # 2001-12-12
        "%m/%d/%Y",  # 12/12/2001
        "%d/%m/%Y",  # 12/12/2001 (alternative)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None  # invalid format

def superadmin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect("forbidden")
        return view_func(request, *args, **kwargs)
    return wrapper

def comming_soon(request):
    return render(request, "404.html")

def forbidden_page(request):
    return render(request, "405.html", status=403)

def builder2(request):
    return render(request, "builder2.html")

def login_view(request):
    if request.user.is_authenticated:
        if user.is_active == False:
            logout(request)
            messages.success(request, "You have been logged out.")
            return redirect(request, "login2.html")  # Replace 'login' with your login URL name
        if request.user.is_superuser:
            return redirect("dashboard")
        else:
            return redirect("../instructor/dashboard/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "All fields are required")
            return render(request, "login2.html")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active == False:
                messages.error(request, "Account is disabled, please see administrator")
                return render(request, "login2.html", {"error": "Account is disabled, please see administrator"})            
            login(request, user)
            if user.is_superuser:
                return redirect("dashboard")
            else:
                return redirect("../instructor/dashboard/")
        else:
            messages.error(request, "Invalid credentials")
            return render(request, "login2.html", {"error": "Invalid credentials"})

    return render(request, "login2.html")

@login_required
def logout_view(request):
    """Logs out the user and shows a confirmation page."""
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have successfully logged out.")
        return redirect('login')  # Replace 'login' with your login URL name

    return render(request, 'logout.html')

def org_chart(request):
    # Org chart data
    dept_chair = CustomUser.objects.filter(designation='Department Chair')
    dept_chair_sec = CustomUser.objects.filter(designation='Department Secretary')
    it_prog_coo = CustomUser.objects.filter(designation='IT Program Coordinator')
    cs_prog_coo = CustomUser.objects.filter(designation='CS Program Coordinator')
    dept_coo = CustomUser.objects.filter(designation='Department Extension Coordinator' and 'Department Research Coordinator')
    instructors = CustomUser.objects.filter(designation='Instructor')
    staff_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=False)
    admin_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=True)
    context = {
        # Org chart
        'dept_chair': dept_chair,
        'admin': admin_list,
        'instructors': instructors,
        'staff_list': staff_list,
        'dept_chair_sec': dept_chair_sec,
        'it_prog_coo': it_prog_coo,
        'cs_prog_coo': cs_prog_coo,
        'dept_coo': dept_coo,

    }

    return render(request, "admin/organization-chart.html", context)

def org_chart2(request):
    # Org chart data
    dept_chair = CustomUser.objects.filter(designation='Department Chair')
    dept_chair_sec = CustomUser.objects.filter(designation='Department Secretary')
    it_prog_coo = CustomUser.objects.filter(designation='IT Program Coordinator')
    cs_prog_coo = CustomUser.objects.filter(designation='CS Program Coordinator')
    dept_coo = CustomUser.objects.filter(designation='Department Extension Coordinator' and 'Department Research Coordinator')
    instructors = CustomUser.objects.filter(designation='Instructor')
    staff_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=False)
    admin_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=True)
    context = {
        # Org chart
        'dept_chair': dept_chair,
        'admin': admin_list,
        'instructors': instructors,
        'staff_list': staff_list,
        'dept_chair_sec': dept_chair_sec,
        'it_prog_coo': it_prog_coo,
        'cs_prog_coo': cs_prog_coo,
        'dept_coo': dept_coo,

    }

    return render(request, "org.html", context)

@login_required
@superadmin_required
def dashboard(request):
    # Latest items
    latest_classrooms = Classroom.objects.order_by('-created_at')[:5]
    latest_instructors = CustomUser.objects.order_by('-date_joined')[:5]
    latest_comlabs = Comlab.objects.order_by('-created_at')[:5]
    latest_subjects = Subjects.objects.order_by('-created_at')[:5]

    # Org chart data
    instructors = CustomUser.objects.filter(is_staff=False)  # adjust if needed
    staff_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=False)
    admin_list = CustomUser.objects.filter(is_staff=True, is_masteradmin=True)

    # Combine timeline
    combined_items = list(chain(
        [{'type': 'Classroom', 'name': room.name, 'created_at': room.created_at} for room in latest_classrooms],
        [{'type': 'Instructor', 'name': instructor.get_full_name() or instructor.username, 'created_at': instructor.date_joined} for instructor in latest_instructors],
        [{'type': 'ComLab', 'name': lab.comlab, 'created_at': lab.created_at} for lab in latest_comlabs],
        [{'type': 'Subject', 'name': subject.name, 'created_at': subject.created_at} for subject in latest_subjects],
    ))

    combined_items.sort(key=lambda x: x['created_at'], reverse=True)

    context = {
        # Stats
        'total_classrooms': Classroom.objects.count(),
        'total_comlabs': Comlab.objects.count(),
        'total_subjects': Subjects.objects.count(),
        'total_instructors': CustomUser.objects.count(),

        # Timeline
        'combined_items': combined_items,

        # News
        'pinned_news': Post.objects.filter(is_pinned=True).order_by('-created_at')[:5],

        # Org chart
        'admin': admin_list,
        'instructors': instructors,
        'staff_list': staff_list,
    }

    return render(request, "admin/dashboard.html", context)

@superadmin_required
@login_required
def database_settings(request):
    return render(request, "admin/database-settings.html")

@superadmin_required
@login_required
def admin(request):
    return render(request, "admin/admin-users.html")

@superadmin_required
@login_required
def news(request):
    return render(request, "admin/news.html")

@superadmin_required
@login_required
def classroom(request):
    return render(request, "admin/classroom.html")

@superadmin_required
@login_required
def subject(request):
    return render(request, "admin/subject.html")

@superadmin_required
@login_required
def instructor(request):
    instructor = CustomUser.objects.filter(is_staff=False).order_by('last_name')
    return render(request, 'admin/instructor.html', {'inst': instructor})

@superadmin_required
@login_required
def instructornew(request):
    return render(request, "admin/instructor-new.html")

@superadmin_required
@login_required
def student(request):
    student = CustomUser.objects.filter(is_staff=False).order_by('last_name')
    return render(request, 'admin/student.html', {'stud': student})

@superadmin_required
@login_required
def studentnew(request):
    return render(request, "admin/student-new.html")

@superadmin_required
@login_required
def sidebar(request):
    return render(request, "admin/sidebar.html")

@superadmin_required
@login_required
def navbar(request):
    return render(request, "admin/navbar.html")

@superadmin_required
@login_required
def profileviewer(request):
    return render(request, "admin/profile-viewer.html")

@superadmin_required
@login_required
def instructorattendance(request):  
    return render(request, "admin/instructor-attendance.html")

@superadmin_required
@login_required
def instructordtr(request):
    return render(request, "admin/instructor-dtr.html")

@superadmin_required
@login_required
def courses(request):
    return render(request, "admin/courses.html")

@superadmin_required
@login_required
def instructorprofile(request, id):
    instructor = CustomUser.objects.get(id=id)
    return render(request, 'admin/instructor-profile.html', {
        'instructor': instructor
    })

@superadmin_required
@login_required
def studentprofile(request, id):
    student = CustomUser.objects.filter(is_staff=False).get(id=id)  # replace YourModel
    return render(request, 'admin/student-profile.html', {
        'student': student
    })

def generate_username(first_name, last_name):
    base = f"{first_name}{last_name}".lower().replace(" ", "")
    rand = random.randint(1000, 9999)
    return f"{base}{rand}"

def global_search(request):
    query = request.GET.get("q", "")
    results = []

    if query:

        # Instructor search
        instructors = CustomUser.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_superuser=False,
            is_staff=False
        )

        for i in instructors:
            results.append({
                "title": f"{i.first_name} {i.last_name}",
                "type": i.designation + " | " + i.academic_rank,
                "url": reverse("instructor-profile", args=[i.id])
            })

        # Classroom search
        classes = Classroom.objects.filter(name__icontains=query)[:5]

        for c in classes:
            results.append({
                "title": c.name,
                "type": "Class",
                "url": reverse("classroom") + f"?open={c.id}"
            })

        # Comlab search
        comlab = Comlab.objects.filter(comlab__icontains=query)[:5]

        for c in comlab:
            results.append({
                "title": c.comlab,
                "type": "ComLab",
                "url": reverse("comlab") + f"?open={c.id}"
            })   

        # Subject search
        subject = Subjects.objects.filter(name__icontains=query)[:5]

        for c in subject:
            results.append({
                "title": c.name,
                "type": "Subject",
                "url": reverse("subject") + f"?open={c.id}"
            })                       

    return JsonResponse({"results": results})

def global_search_instructor_only(request):
    query = request.GET.get("q", "")
    results = []

    if query:

        # Instructor search
        instructors = CustomUser.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_superuser=False,
            is_staff=False
        )[:5]

        for i in instructors:
            results.append({
                "title": f"{i.first_name} {i.last_name}",
                "type": i.designation + " | " + i.academic_rank,
                "url": reverse("view-profile", args=[i.id])
            })                      

    return JsonResponse({"results": results})

#region ComLab
@superadmin_required
@login_required
def comlab(request):
    # ===== AJAX REQUESTS =====
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == "POST":
        action = request.POST.get('action')

        # ----- DELETE -----
        if action == 'delete':
            pk = request.POST.get('id')
            if not pk:
                return JsonResponse({'success': False, 'message': 'No ID provided.'})

            comlab = get_object_or_404(Comlab, pk=pk)
            comlab.delete()
            return JsonResponse({'success': True, 'message': 'Item deleted successfully!'})

        # ----- UPDATE -----
        elif action == 'update':
            try:
                obj = Comlab.objects.get(id=request.POST.get('id'))
                obj.comlab = request.POST.get('comlab')
                obj.location = request.POST.get('location')
                obj.last_updated_by = request.user 
                if request.FILES.get('cards'):
                    obj.cards = request.FILES.get('cards')

                obj.save()

                return JsonResponse({
                    "success": True,
                    "id": obj.id,
                    "comlab": obj.comlab,
                    "location": obj.location,
                    "image": obj.cards.url if obj.cards else ""
                })
            except Comlab.DoesNotExist:
                return JsonResponse({"success": False, "error": "Not found"})

        # ----- UNKNOWN ACTION -----
        else:
            return JsonResponse({"success": False, "error": "Invalid action"})

    # ===== NORMAL PAGE LOAD =====
    comlabs = Comlab.objects.all().order_by('-id')
    return render(request, 'admin/comlab.html', {'cl': comlabs})

@superadmin_required
@login_required
def add_comlab(request):
    if request.method == 'POST':
        comlab = request.POST.get('comlab')
        location = request.POST.get('location')
        image = request.FILES.get('cards')

        new_comlab = Comlab.objects.create(
            comlab=comlab,
            location=location,
            cards=image,
            created_by = request.user 
        )

        return JsonResponse({
            'success': True,
            'id': new_comlab.id,
            'name': new_comlab.comlab,
            'location': new_comlab.location,
            'image_url': new_comlab.cards.url if new_comlab.cards else '/static/image/comlab.jpg'
        })

    return JsonResponse({'success': False})

#endregion

#region EQ
@superadmin_required
@login_required
def get_equipment_list(request):
    equip = list(EquipmentBorrow.objects.all().order_by('-id').values())
    return JsonResponse({'eq': equip})

@superadmin_required
@login_required
def mark_returned(request, id):
    if request.method == "POST":
        try:
            item = EquipmentBorrow.objects.get(id=id)
            item.last_updated_by = request.user 
            item.status = "returned"
            item.save()
            return JsonResponse({"success": True, "message": "Marked as returned"})
        except EquipmentBorrow.DoesNotExist:
            return JsonResponse({"success": False, "message": "Item not found"})

# @csrf_exempt  # needed if AJAX doesn't send CSRF token properly
@superadmin_required
@login_required
def save_equipment_borrow(request):
    if request.method == "POST":
        name = request.POST.get("name")
        date = request.POST.get("date")
        time = request.POST.get("time")
        equipment = request.POST.get("equipment")
        status = request.POST.get("status", "borrowed")

        # Save to database
        borrow_record = EquipmentBorrow.objects.create(
            name=name,
            date=date,
            time=time,
            equipment=equipment,
            status=status,
            created_by = request.user 
        )

        return JsonResponse({
            "success": True,
            "message": "Record saved successfully!",
            "data": {
                "id": borrow_record.id,
                "name": borrow_record.name,
                "date": borrow_record.date,
                "time": borrow_record.time,
                "equipment": borrow_record.equipment,
                "status": borrow_record.status
            }
        })
    
    return JsonResponse({"success": False, "message": "Invalid request method"})
#endregion

#region Reports
@superadmin_required
@login_required
def add_report(request):
    if request.method == "POST":
        name = request.POST.get('name')
        date = request.POST.get('date')
        time = request.POST.get('time')
        report_text = request.POST.get('report')
        attachment = request.FILES.get('attachment')   

        Report.objects.create(
            name=name,
            date=date,
            time=time,
            report=report_text,
            attachment=attachment,
            created_by = request.user 
        )   

        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'})

@superadmin_required
@login_required
def get_reports(request):
    reports = Report.objects.all().order_by('-id')

    data = []

    for r in reports:
        data.append({
            'id': r.id,
            'name': r.name,
            'date': r.date.strftime("%m/%d/%Y") if r.date else '',
            'time': r.time.strftime("%I:%M %p") if r.time else '',
            'report': r.report,

            # ✅ attachment
            'attachment': r.attachment.url if r.attachment else '',

            # ✅ NEW: upload info
            'created_by': r.created_by.username if r.created_by else 'Unknown',
            'uploaded_at': r.created_at.strftime("%m/%d/%Y %I:%M %p") if r.created_at else '',

            # ✅ NEW: last update info
            'last_updated_by': r.last_updated_by.username if r.last_updated_by else '',
            'last_updated': r.last_updated.strftime("%m/%d/%Y %I:%M %p") if r.last_updated else '',
        })

    return JsonResponse({'rp': data})

def delete_report(request, report_id):
    if request.method == "POST":
        try:
            report = Report.objects.get(id=report_id)
            # Optionally delete the file from storage
            if report.attachment:
                report.attachment.delete(save=False)
            report.delete()
            return JsonResponse({'status': 'success'})
        except Report.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Report not found'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def edit_report(request, report_id):
    if request.method == "POST":
        try:
            report = Report.objects.get(id=report_id)
            report.name = request.POST.get('name')
            # report.date = request.POST.get('date')
            # report.time = request.POST.get('time')
            report.report = request.POST.get('report')

            # Replace attachment if new file uploaded
            attachment = request.FILES.get('attachment')
            report.last_updated_by = request.user 

            if attachment:
                if report.attachment:
                    report.attachment.delete(save=False)
                report.attachment = attachment

            report.save()
            return JsonResponse({'status': 'success'})
        except Report.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Report not found'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
#endregion

#region News
@superadmin_required
@login_required
def post_feed(request):
    posts = Post.objects.select_related('created_by').prefetch_related('likes').order_by('-is_pinned', '-created_at')

    data = []

    for p in posts:
        comments = p.comments.all().order_by('created_at')
        # =========================
        # USER SAFE HANDLING
        # =========================
        user = p.created_by

        if user:
            full_name = user.get_full_name() or user.username
        else:
            full_name = "Unknown User"

        # =========================
        # PROFILE PIC SAFE
        # =========================
        profile_pic = None
        initials = "".join([n[0] for n in full_name.split()][:2]).upper()

        if user and hasattr(user, "profile_pic") and user.profile_pic:
            try:
                profile_pic = user.profile_pic.url
                initials = None
            except:
                profile_pic = None

        # =========================
        # LIKES SAFE
        # =========================
        likes_count = p.likes.count() if hasattr(p, "likes") else 0
        liked_by_me = p.likes.filter(id=request.user.id).exists() if hasattr(p, "likes") else False

        data.append({
            "id": p.id,
            "body": p.body,
            "image": p.image.url if p.image else None,

            "is_pinned": p.is_pinned,
            "is_announcement": p.is_announcement,
            "is_private": p.is_private,

            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),

            "created_by": full_name,
            "profile_pic": profile_pic,
            "initials": initials,

            "likes_count": likes_count,
            "comments": [
                {
                    "user": c.user.get_full_name(),
                    "body": c.body,
                    "created_at": c.created_at.strftime("%b %d, %I:%M %p")
                }
                for c in comments
            ],
            "liked_by_me": liked_by_me
        })

    return JsonResponse({"posts": data})

def new_posts(request):
    latest_id = request.GET.get('latest_id', 0)

    posts = Post.objects.filter(id__gt=latest_id).order_by('-id')

    data = []

    for p in posts:
        comments = p.comments.all().order_by('created_at')
        # =========================
        # USER SAFE HANDLING
        # =========================
        user = p.created_by

        if user:
            full_name = user.get_full_name() or user.username
        else:
            full_name = "Unknown User"

        # =========================
        # PROFILE PIC SAFE
        # =========================
        profile_pic = None
        initials = "".join([n[0] for n in full_name.split()][:2]).upper()

        if user and hasattr(user, "profile_pic") and user.profile_pic:
            try:
                profile_pic = user.profile_pic.url
                initials = None
            except:
                profile_pic = None

        # =========================
        # LIKES SAFE
        # =========================
        likes_count = p.likes.count() if hasattr(p, "likes") else 0
        liked_by_me = p.likes.filter(id=request.user.id).exists() if hasattr(p, "likes") else False

        data.append({
            "id": p.id,
            "body": p.body,
            "image": p.image.url if p.image else None,

            "is_pinned": p.is_pinned,
            "is_announcement": p.is_announcement,
            "is_private": p.is_private,

            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),

            "created_by": full_name,
            "profile_pic": profile_pic,
            "initials": initials,

            "likes_count": likes_count,
            "comments": [
                {
                    "user": c.user.get_full_name(),
                    "body": c.body,
                    "created_at": c.created_at.strftime("%b %d, %I:%M %p")
                }
                for c in comments
            ],
            "liked_by_me": liked_by_me
        })        

    return JsonResponse({"posts": data})

def toggle_like(request, post_id):
    post = Post.objects.get(id=post_id)
    user = request.user

    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True

    return JsonResponse({
        "success": True,
        "liked": liked,
        "likes_count": post.likes.count()
    })


@superadmin_required
@login_required
def create_post(request):
    pinned = request.POST.get("is_pinned") == "on"
    try:
        if request.POST.get("is_announcement") == "on" :
            pinned = True

        user = request.user

        if user:
            full_name = user.get_full_name() or user.username
        else:
            full_name = "Unknown User"

        # =========================
        # PROFILE PIC SAFE
        # =========================
        profile_pic = None
        initials = "".join([n[0] for n in full_name.split()][:2]).upper()

        if user and hasattr(user, "profile_pic") and user.profile_pic:
            try:
                profile_pic = user.profile_pic.url
                initials = None
            except:
                profile_pic = None

        # =========================
        # LIKES SAFE
        # =========================
        likes_count = 0
        liked_by_me = False        
        
        post = Post.objects.create(
            body=request.POST.get("body"),
            is_pinned=pinned,
            is_announcement=request.POST.get("is_announcement") == "on",
            is_private=request.POST.get("is_private") == "on",
            image=request.FILES.get("image"),
            created_by=request.user
        )

        return JsonResponse({
            "success": True,
            "post": {
                "id": post.id,
                "body": post.body,
                "is_pinned": post.is_pinned,
                "is_announcement": post.is_announcement,
                "image": post.image.url if post.image else None,

                "created_by": full_name,
                "profile_pic": profile_pic,
                "initials": initials,

                "likes_count": likes_count,
                "liked_by_me": liked_by_me
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

@superadmin_required
@login_required
def add_comment(request, post_id):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Login required"}, status=403)

    try:
        data = json.loads(request.body)
        body = data.get("body")

        if not body:
            return JsonResponse({"success": False, "message": "Empty comment"}, status=400)

        post = get_object_or_404(Post, id=post_id)

        comment = Comment.objects.create(
            post=post,
            user=request.user,
            body=body
        )

        return JsonResponse({
            "success": True,
            "comment": {
                "id": comment.id,
                "user": comment.user.username,
                "body": comment.body,
                "created_at": comment.created_at.strftime("%b %d, %I:%M %p")
            }
        })

    except Exception as e:
        print("ERROR:", str(e))  # 👈 shows in terminal
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
def delete_post(request, post_id):
    try:
        post = Post.objects.get(id=post_id)

        # Only allow if user is superadmin or creator
        if request.user.is_superuser or post.created_by_id == request.user.id:
            post.delete()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Permission denied"})

    except Post.DoesNotExist:
        return JsonResponse({"success": False, "error": "Post not found"}, status=404)
    
def post_list(request):
    page = request.GET.get('page', 1)

    posts = Post.objects.all().order_by('-created_at')
    paginator = Paginator(posts, 5)  # 5 posts per load

    page_obj = paginator.get_page(page)

    data = []

    for p in page_obj:
        comments = p.comments.all().order_by('created_at')
        # =========================
        # USER SAFE HANDLING
        # =========================
        user = p.created_by

        if user:
            full_name = user.get_full_name() or user.username
        else:
            full_name = "Unknown User"

        # =========================
        # PROFILE PIC SAFE
        # =========================
        profile_pic = None
        initials = "".join([n[0] for n in full_name.split()][:2]).upper()

        if user and hasattr(user, "profile_pic") and user.profile_pic:
            try:
                profile_pic = user.profile_pic.url
                initials = None
            except:
                profile_pic = None

        # =========================
        # LIKES SAFE
        # =========================
        likes_count = p.likes.count() if hasattr(p, "likes") else 0
        liked_by_me = p.likes.filter(id=request.user.id).exists() if hasattr(p, "likes") else False

        data.append({
            "id": p.id,
            "body": p.body,
            "image": p.image.url if p.image else None,

            "is_pinned": p.is_pinned,
            "is_announcement": p.is_announcement,
            "is_private": p.is_private,

            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),

            "created_by": full_name,
            "profile_pic": profile_pic,
            "initials": initials,

            "likes_count": likes_count,
            "comments": [
                {
                    "user": c.user.get_full_name(),
                    "body": c.body,
                    "created_at": c.created_at.strftime("%b %d, %I:%M %p")
                }
                for c in comments
            ],
            "liked_by_me": liked_by_me
        })  

    return JsonResponse({
        "posts": data
    })
#endregion

#region Student
@superadmin_required
@login_required
def add_student(request):
    if request.method == "POST":
        try:
            data = request.POST
            files = request.FILES

            birthday = data.get("birthday")
            age = None

            username = generate_username(
                data.get("first_name", ""),
                data.get("last_name", "")
            )

            # Calculate age
            if birthday:
                bday = date.fromisoformat(birthday)
                today = date.today()
                age = today.year - bday.year - (
                    (today.month, today.day) < (bday.month, bday.day)
                )

            # ✅ Convert fingerprint values safely
            fp_main = int(data.get("main")) if data.get("main") else None
            fp_backup = int(data.get("backup")) if data.get("backup") else None
            fp_extra = int(data.get("extra")) if data.get("extra") else None

            with transaction.atomic():
                link_id = generate_random_id(10)

                user = CustomUser.objects.create(
                    username=username,
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    middle_name=data.get("middle_name"),
                    email=data.get("email"),
                    contact_info=data.get("contact_no"),
                    birthday=birthday or None,
                    age=age,
                    gender=data.get("gender"),
                    status=data.get("status"),
                    position="Student",
                    organization="",
                    link_id=link_id,
                    is_staff=False,
                    is_masteradmin=False,
                )

                Fingerprint.objects.create(
                    main_id=fp_main,
                    backup_id=fp_backup,
                    extra_id=fp_extra,
                    random_id=link_id,
                    user_id=user.id
                )

                # Set password
                user.set_password(username)

                # Profile image
                if "profile_picture" in files:
                    user.profile_pic = files["profile_picture"]

                user.save()

                # Assign group
                group, _ = Group.objects.get_or_create(name="Student")
                user.groups.add(group)

            return JsonResponse({
                "success": True,
                "message": "Student created successfully",
                "username": username
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

    return JsonResponse({
        "success": False,
        "message": "Invalid request"
    })
#endregion

#region Instructor
@superadmin_required
@login_required
def add_instructor(request):
    if request.method == "POST":
        try:
            data = request.POST
            files = request.FILES

            birthday = data.get("birthday")
            age = None

            username = generate_username(
                data.get("first_name", ""),
                data.get("last_name", "")
            )

            # Calculate age
            if birthday:
                bday = date.fromisoformat(birthday)
                today = date.today()
                age = today.year - bday.year - (
                    (today.month, today.day) < (bday.month, bday.day)
                )

            with transaction.atomic():
                link_id = generate_random_id(10)

                user = CustomUser.objects.create(
                    username=username,
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    middle_name=data.get("middle_name"),
                    email=data.get("email"),
                    contact_info=data.get("contact_info"),
                    birthday=birthday or None,
                    age=age,
                    gender=data.get("gender"),
                    employment_status=data.get("employment_status"),
                    academic_rank=data.get("academic_rank"),
                    designation=data.get("designation"),
                    date_of_employment=data.get("date_of_employment"),
                    workloads=data.get("workloads"),

                    instructor_id=data.get("instructor_id"),
                    bs_degree=data.get("bs_degree"),
                    masters_degree=data.get("masters_degree"),
                    doctorate_degree=data.get("doctorate_degree"),
                    eligibility_type=data.get("eligibility_type"),

                    main_id=data.get("main_id") or None,
                    backup_id=data.get("backup_id") or None,
                    extra_id=data.get("extra_id") or None,
                    is_masteradmin=False,
                )

                # Set password
                user.set_password("Default123")

                # Profile image
                if "profile_picture" in files:
                    user.profile_pic = files["profile_picture"]

                user.save()

                # Assign group
                group, _ = Group.objects.get_or_create(name="Instructor")
                user.groups.add(group)

            return JsonResponse({
                "success": True,
                "message": "Instructor created successfully",
                "username": username
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

    return JsonResponse({
        "success": False,
        "message": "Invalid request"
    })

@csrf_exempt
@login_required
@superadmin_required
def update_instructor(request, id):
    if request.method == "POST":
        birthday = request.POST.get("birthday")
        age = None

        if birthday:
            bday = date.fromisoformat(birthday)
            today = date.today()
            age = today.year - bday.year - (
                (today.month, today.day) < (bday.month, bday.day)
            )

        try:
            instr = CustomUser.objects.get(id=id)
            instr.profile_pic = request.FILES.get("fileUpload")
            instr.first_name = request.POST.get("first_name")
            instr.last_name = request.POST.get("last_name")
            instr.middle_name = request.POST.get("middle_name")
            instr.email = request.POST.get("email")
            instr.contact_info = request.POST.get("contact_info")
            instr.birthday = birthday or None
            instr.age = age
            instr.gender = request.POST.get("gender")
            instr.employment_status = request.POST.get("employment_status")
            instr.academic_rank = request.POST.get("academic_rank")
            instr.designation = request.POST.get("designation")

            date_emp = request.POST.get("date_of_employment")
            instr.date_of_employment = date_emp or None

            instr.instructor_id = request.POST.get("instructor_id")
            instr.bs_degree = request.POST.get("bs_degree")
            instr.masters_degree = request.POST.get("masters_degree")
            instr.doctorate_degree = request.POST.get("doctorate_degree")
            instr.eligibility_type = request.POST.get("eligibility_type")
            instr.workloads = request.POST.get("workloads")  # match your form

            instr.save()

            return JsonResponse({"success": True})

        except CustomUser.DoesNotExist:
            return JsonResponse({"success": False, "message": "Instructor not found."})

    return JsonResponse({"success": False, "message": "Invalid request"})

@csrf_exempt
@login_required
@superadmin_required
def save_fingerprint(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    instructor_id = request.POST.get("instructor_id")
    main = request.POST.get("main_id")
    backup = request.POST.get("backup_id")
    extra = request.POST.get("extra_id")

    if not instructor_id:
        return JsonResponse({"success": False, "error": "Instructor ID missing"})

    try:
        fingerprint = Fingerprint.objects.get(user_id=instructor_id)
        fingerprint.main_id = main
        fingerprint.backup_id = backup
        fingerprint.extra_id = extra
        fingerprint.save()

        return JsonResponse({"success": True})

    except Fingerprint.DoesNotExist:
        return JsonResponse({"success": False, "error": "Fingerprint record not found"})
    

@superadmin_required
@login_required
def instructor_password_reset(request):
    try:
        user = CustomUser.objects.get(id=request.POST.get('user_id'))
        user.set_password("Default123")

        user.save()

        return JsonResponse({
            "status": "success",
            "message": "Password set to default",
            "id": user.id
        })
    except Comlab.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"})
    
@superadmin_required
@login_required
def instructor_account_disable(request):
    try:
        user = CustomUser.objects.get(id=request.POST.get('user_id'))
        user.is_active=False

        user.save()

        return JsonResponse({
            "status": "success",
            "message": "Account disabled",
            "id": user.id
        })
    except Comlab.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"})
    
@superadmin_required
@login_required
def instructor_account_enable(request):
    try:
        user = CustomUser.objects.get(id=request.POST.get('user_id'))
        user.is_active=True

        user.save()

        return JsonResponse({
            "status": "success",
            "message": "Account enabled",
            "id": user.id
        })
    except Comlab.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"})
#endregion

#region Class
@superadmin_required
@login_required
def class_Instructor_list(request):
    users = CustomUser.objects.filter(
        is_active=True,
        is_staff=False
    ).exclude(
        id__in=Classroom.objects.values_list('instructor_id', flat=True)
    )

    data = []
    for user in users:
        data.append({
            "id": user.id,
            "name": user.get_full_name() or user.username
        })

    return JsonResponse({"instructors": data})

@superadmin_required
@login_required
def class_Instructor_list_edit(request):
    users = CustomUser.objects.filter(
        is_active=True,
        is_staff=False
    )

    data = []
    for user in users:
        data.append({
            "id": user.id,
            "name": user.get_full_name() or user.username
        })

    return JsonResponse({"instructors": data})

@superadmin_required
@login_required
def classroom_dashboard(request):
    return render(request, "classroom_dashboard.html")

@login_required
def classroom_list(request):
    classrooms = Classroom.objects.all().order_by('-id')
    
    data = []
    for c in classrooms:
        instructor_name = None
        instructor_id = None

        if c.instructor:  # ✅ safe check
            instructor_name = f"{c.instructor.first_name} {c.instructor.last_name}"
            instructor_id = c.instructor.id

        data.append({
            "id": c.id,
            "name": c.name,
            "room_code": c.room_code,
            "capacity": c.capacity,
            "description": c.description,
            "instructor": instructor_name,
            "instructor_id": instructor_id
        })

    return JsonResponse({"classrooms": data})

@superadmin_required
@login_required
def classroom_create_ajax(request):
    if request.method == "POST":

        name = request.POST.get("name")
        room_code = request.POST.get("room_code")
        capacity = request.POST.get("capacity")
        description = request.POST.get("description")
        instructor_id = request.POST.get("instructor")

        if not name or not room_code:
            return JsonResponse({"status": "error", "message": "Missing fields"})

        if Classroom.objects.filter(room_code=room_code).exists():
            return JsonResponse({"status": "error", "message": "Room code already exists"})

        instructor = None
        if instructor_id:
            try:
                instructor = User.objects.get(pk=instructor_id)
            except User.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Instructor not found"})

        classroom = Classroom.objects.create(
            name=name,
            room_code=room_code,
            capacity=capacity,
            description=description,
            instructor=instructor,  # can be None
            created_by=request.user
        )

        return JsonResponse({
            "status": "success",
            "message": "Classroom created",
            "id": classroom.id
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})
    
# UPDATE CLASSROOM
@superadmin_required
@login_required
def classroom_update_ajax(request, pk):
    if request.method == "POST":
        instructor_id = request.POST.get("instructor")
        instructor = None
        if instructor_id:
            try:
                instructor = User.objects.get(pk=instructor_id)
            except User.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Instructor not found"})
        try:
            classroom = Classroom.objects.get(pk=pk)

            classroom.name = request.POST.get("name")
            classroom.room_code = request.POST.get("room_code")
            classroom.capacity = request.POST.get("capacity")
            classroom.description = request.POST.get("description")
            classroom.instructor = instructor
            classroom.updated_by = request.user 

            classroom.save()

            return JsonResponse({"status": "success", "message": "Updated successfully"})
        except:
            return JsonResponse({"status": "error", "message": "Update failed"})


# DELETE CLASSROOM
@superadmin_required
@login_required
def classroom_delete_ajax(request, pk):
    if request.method == "POST":
        try:
            classroom = Classroom.objects.get(pk=pk)
            classroom.delete()
            return JsonResponse({"status": "success", "message": "Deleted"})
        except:
            return JsonResponse({"status": "error", "message": "Delete failed"})
#endregion

#region Course
@superadmin_required
@login_required
def course_create_ajax(request):
    if request.method == "POST":
        
        course_name = request.POST.get("course_name")
        course_code = request.POST.get("course_code")
        description = request.POST.get("description")

        if not course_name or not course_code:
            return JsonResponse({"status": "error", "message": "Missing fields"})

        if Course.objects.filter(code=course_code).exists():
            return JsonResponse({"status": "error", "message": "Course code already exists"})

        course = Course.objects.create(
            name=course_name,
            code=course_code,
            description=description,
            created_by=request.user 
        )

        return JsonResponse({
            "status": "success",
            "message": "Subject created",
            "id": course.id
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})

@superadmin_required
@login_required
def course_update_ajax(request, pk):
    if request.method == "POST":
        try:
            course = Course.objects.get(pk=pk)

            course.name = request.POST.get("name")
            course.room_code = request.POST.get("room_code")
            course.description = request.POST.get("description")
            course.last_updated_by_id = request.user 

            course.save()

            return JsonResponse({"status": "success", "message": "Updated successfully"})
        except:
            return JsonResponse({"status": "error", "message": "Update failed"})

@superadmin_required
@login_required
def course_list(request):
    course = Course.objects.all().order_by('-name')
    
    data = []
    for c in course:
        data.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "description": c.description
        })

    return JsonResponse({"course": data})

@superadmin_required
@login_required
def course_delete_ajax(request, pk):
    if request.method == "POST":
        try:
            course = Course.objects.get(pk=pk)
            course.delete()
            return JsonResponse({"status": "success", "message": "Deleted"})
        except:
            return JsonResponse({"status": "error", "message": "Delete failed"})
#endregion

#region Subjects
@superadmin_required
@login_required
def subject_create_ajax(request):
    if request.method == "POST":
        
        subject_name = request.POST.get("subject_name")
        subject_code = request.POST.get("subject_code")
        description = request.POST.get("description")

        if not subject_name or not subject_code:
            return JsonResponse({"status": "error", "message": "Missing fields"})

        if Subjects.objects.filter(code=subject_code).exists():
            return JsonResponse({"status": "error", "message": "Subject code already exists"})

        subjects = Subjects.objects.create(
            name=subject_name,
            code=subject_code,
            description=description,
            created_by=request.user 
        )

        return JsonResponse({
            "status": "success",
            "message": "Subject created",
            "id": subjects.id
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})

@superadmin_required
@login_required
def subject_update_ajax(request, pk):
    if request.method == "POST":
        try:
            classroom = Subjects.objects.get(pk=pk)

            classroom.name = request.POST.get("name")
            classroom.room_code = request.POST.get("room_code")
            classroom.description = request.POST.get("description")
            classroom.last_updated_by_id = request.user 

            classroom.save()

            return JsonResponse({"status": "success", "message": "Updated successfully"})
        except:
            return JsonResponse({"status": "error", "message": "Update failed"})

@superadmin_required
@login_required
def subject_list(request):
    subject = Subjects.objects.all().order_by('-name')
    data = []
    for c in subject:
        course = Course.objects.filter(id=c.course_id)[:1]
        data.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "description": c.description,
            "course": course[0].name,
            "cid": course[0].id,
        })

    return JsonResponse({"subjects": data})

@superadmin_required
@login_required
def subject_delete_ajax(request, pk):
    if request.method == "POST":
        try:
            subject = Subjects.objects.get(pk=pk)
            subject.delete()
            return JsonResponse({"status": "success", "message": "Deleted"})
        except:
            return JsonResponse({"status": "error", "message": "Delete failed"})
#endregion

#region Scheduling
@login_required
def class_schedule_list(request, pk):
    # Detect if pk belongs to classroom or comlab
    schedule_instance = (
        Schedule.objects.filter(room_id=pk).first() or
        Schedule.objects.filter(comlab_id=pk).first()
    )

    # If no schedule exists at all
    if not schedule_instance:
        return JsonResponse({
            "schedules": [],
            "message": "No schedule available"
        })

    room_type = schedule_instance.room_type.lower()

    # Filter based on detected type
    if room_type == "classroom":
        schedules = Schedule.objects.filter(room_id=pk).order_by('-id')
    elif room_type == "comlab":
        schedules = Schedule.objects.filter(comlab_id=pk).order_by('-id')
    else:
        schedules = Schedule.objects.none()

    # If still empty
    if not schedules.exists():
        return JsonResponse({
            "schedules": [],
            "message": "No schedule available"
        })

    data = []
    for s in schedules:
        start = s.start_time.strftime('%H:%M') if s.start_time else ""
        end = s.end_time.strftime('%H:%M') if s.end_time else ""

        data.append({
            "id": s.id,
            "subject": str(s.subject),
            "instructor": str(s.instructor) if s.instructor else "",  # ✅ FIX
            "day": s.day,
            "start": start,
            "end": end,
        })

    return JsonResponse({"schedules": data})

        
@login_required
def schedule_list(request):
    instructor_id = request.GET.get("instructor_id")

    schedules = Schedule.objects.select_related("subject", "room")

    # ✅ Apply filter if provided
    if instructor_id:
        schedules = schedules.filter(instructor_id=instructor_id)

    schedules = schedules.order_by("-id")

    data = []
    for s in schedules:
        rm = "";
        start = s.start_time.strftime('%H:%M') if s.start_time else ""
        end = s.end_time.strftime('%H:%M') if s.end_time else ""
        if s.room_type == "classroom":
            rm =  str(s.room)
        else:
            rm =  str(s.comlab)
        data.append({
            "id": s.id,
            "subject": str(s.subject),
            "room": rm,
            "instructor_id": s.instructor.id,
            "day": s.day,
            "start": start,
            "end": end,
        })

    return JsonResponse({"schedules": data})

@superadmin_required
@login_required
def instructor_get_schedule_per_id(request):
    schedule_id = request.POST.get("id")

    if not schedule_id:
        return JsonResponse({"error": "Missing schedule id"}, status=400)

    try:
        s = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        return JsonResponse({"error": "Schedule not found"}, status=404)

    room = str(s.room) if s.room_type == "classroom" else str(s.comlab)

    data = {
        "id": s.id,
        "subject": str(s.subject),
        "subject_id": s.subject.id,
        "section": str(s.section),
        "room": room,
        "room_id": s.room.id,        
        "day": s.day,
        "start": s.start_time.strftime('%H:%M') if s.start_time else "",
        "end": s.end_time.strftime('%H:%M') if s.end_time else "",
    }

    return JsonResponse({"solo_sched": data})

@superadmin_required
@login_required  
def instructor_update_schedule_per_id(request):
    try:
        schedule_id = request.POST.get("sched_id")
        subject = request.POST.get("subject_ereq")
        room = request.POST.get("classroom_ereq")
        room_type = request.POST.get("room_type")
        days = request.POST.getlist("selectedDays")
        start_time = request.POST.get("start_etime")
        end_time = request.POST.get("end_etime")
        instructor_id = request.POST.get("instructor_id")

        if not all([schedule_id, subject, room_type, start_time, end_time]) or not days:
            return JsonResponse({"success": False, "error": "All fields are required"})

        day_map = {
            "Monday": "M", "Tuesday": "T", "Wednesday": "W",
            "Thursday": "TH", "Friday": "F",
            "Saturday": "SAT", "Sunday": "SUN"
        }

        base_sched = Schedule.objects.get(id=schedule_id)

        created = []
        skipped_days = []

        for i, day in enumerate(days):
            short_day = day_map.get(day, day)

            # Conflict check
            conflict_filter = Q(day=short_day)
            if room_type == "classroom":
                conflict_filter &= Q(room_id=room)
            else:
                conflict_filter &= Q(comlab_id=room)

            conflict = Schedule.objects.filter(conflict_filter)\
                .exclude(id=schedule_id)\
                .filter(start_time__lt=end_time, end_time__gt=start_time)\
                .exists()
            print("ROOM:", room)
            print("TYPE:", room_type)
            if i == 0:
                # Always update the base schedule for the first selected day
                base_sched.subject_id = subject
                base_sched.start_time = start_time
                base_sched.end_time = end_time
                base_sched.room_type = room_type

                if room_type == "classroom":
                    base_sched.room_id = room
                else:
                    base_sched.comlab_id = room

                base_sched.day = short_day
                base_sched.save()

            else:
                if conflict:
                    skipped_days.append(day)
                    continue  # do not create
                # Create new schedule
                if room_type == "classroom":
                    new_sched = Schedule.objects.create(
                        subject_id=subject,
                        day=short_day,
                        start_time=start_time,
                        end_time=end_time,
                        room_type=room_type,
                        room_id=room,
                        instructor_id=instructor_id,
                    )
                else :
                    new_sched = Schedule.objects.create(
                        subject_id=subject,
                        day=short_day,
                        start_time=start_time,
                        end_time=end_time,
                        room_type=room_type,
                        comlab_id=room,
                        instructor_id=instructor_id,
                    )


                created.append({
                    "id": new_sched.id,
                    "day": new_sched.day,
                    "subject": str(new_sched.subject),
                    "room": str(new_sched.room) if room_type == "classroom" else str(new_sched.comlab),
                    "time": f"{new_sched.start_time} - {new_sched.end_time}"
                })

        response = {"success": True, "created": created}

        if skipped_days:
            response["skipped_days"] = skipped_days
            response["message"] = "Some days were skipped due to conflicts."

        return JsonResponse(response)

    except Schedule.DoesNotExist:
        return JsonResponse({"success": False, "error": "Schedule not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
        
@superadmin_required
@login_required
def add_schedule(request):
    try:
        subject = request.POST.get("subject_req")
        classroom = request.POST.get("room")      # from frontend
        comlab = request.POST.get("comlab")       # from frontend
        days = request.POST.getlist("days")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        instructor_id = request.POST.get("instructor_id")

        # ✅ Validate
        if not all([subject, start_time, end_time, instructor_id]) or not days:
            return JsonResponse({
                "success": False,
                "error": "All fields are required"
            })

        if classroom and comlab:
            return JsonResponse({
                "success": False,
                "error": "Only one room type allowed"
            })

        if not classroom and not comlab:
            return JsonResponse({
                "success": False,
                "error": "Room is required"
            })

        room_type = "classroom" if classroom else "comlab"
        room_id = classroom or comlab

        day_map = {
            "Monday": "M",
            "Tuesday": "T",
            "Wednesday": "W",
            "Thursday": "TH",
            "Friday": "F",
            "Saturday": "SAT",
            "Sunday": "SUN"
        }

        created = []

        for day in days:
            short_day = day_map.get(day, day)

            # ✅ Conflict check (handles both room types)
            conflict_query = Q(instructor_id=instructor_id)

            if room_type == "classroom":
                conflict_query |= Q(room_id=room_id)
            else:
                conflict_query |= Q(comlab_id=room_id)

            conflict = Schedule.objects.filter(
                conflict_query,
                day=short_day
            ).filter(
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()

            if conflict:
                return JsonResponse({
                    "success": False,
                    "error": f"Schedule conflict on {day}"
                })

            # ✅ Create schedule
            if room_type == "classroom":
                schedule = Schedule.objects.create(
                    subject_id=subject,
                    room_id=room_id,
                    day=short_day,
                    start_time=start_time,
                    room_type="classroom",
                    end_time=end_time,
                    instructor_id=instructor_id
                )
                room_name = str(schedule.room)

            else:
                schedule = Schedule.objects.create(
                    subject_id=subject,
                    comlab_id=room_id,
                    day=short_day,
                    start_time=start_time,
                    room_type="comlab",
                    end_time=end_time,
                    instructor_id=instructor_id
                )
                room_name = str(schedule.comlab)

            created.append({
                "id": schedule.id,
                "day": schedule.day,
                "subject": str(schedule.subject),
                "room": room_name,
                "time": f"{schedule.start_time} - {schedule.end_time}"
            })

        return JsonResponse({
            "success": True,
            "data": created
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        })

@superadmin_required
@login_required   
def delete_schedule(request):
    try:
        Schedule.objects.get(id=request.POST.get("sched_id")).delete()
        return JsonResponse({"success": True})
    except:
        return JsonResponse({"success": False})    

@superadmin_required
@login_required   
def clean(self):
    if self.start_time >= self.end_time:
        raise ValidationError("End time must be after start time.")

    conflicts = Schedule.objects.filter(
        instructor=self.instructor,
        day=self.day,
        start_time__lt=self.end_time,
        end_time__gt=self.start_time
    ).exclude(id=self.id)

    if conflicts.exists():
        raise ValidationError("Schedule conflict detected.")

@superadmin_required
@login_required    
def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)

@superadmin_required
@login_required  
def subject_scheduling_api(request):
    subjects = Subjects.objects.all().order_by('name') 

    data = [
        {
            "id": s.id,
            "name": s.name
        }
        for s in subjects
    ]

    return JsonResponse({"subjects": data})

@superadmin_required
@login_required  
def classroom_scheduling_api(request):
    classrooms = Classroom.objects.all().order_by('name')
    comlabs = Comlab.objects.all().order_by('comlab')

    combined_data = []

    # Add classrooms
    for c in classrooms:
        combined_data.append({
            "id": c.id,
            "name": c.name,
            "type": "classroom"
        })

    # Add comlabs
    for cb in comlabs:
        combined_data.append({
            "id": cb.id,
            "name": cb.comlab,
            "type": "comlab"
        })

    return JsonResponse({
        "class": combined_data
    })


#endregion

#region Bulk uploader
@superadmin_required
@login_required  
def calculate_age(birthday):
    if birthday:
        today = date.today()
        return today.year - birthday.year - (
            (today.month, today.day) < (birthday.month, birthday.day)
        )
    return None

@superadmin_required
@login_required  
def preview_users(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        VALID_GENDERS = ['Male', 'Female', 'Other']
        VALID_EMPLOYMENT_STATUS = ['Permanent', 'Temporary', 'Contract of Service']
        VALID_ACADEMIC_RANK = ['Instructor 1', 'Instructor 2', 'Instructor 3', 'Assistant Professor 1', 'Assistant Professor 2', 'Assistant Professor 3', 'Assistant Professor 4', 'Professor 1', 'Professor 2', 'Professor 3', 'Professor 4', 'Professor 5']
        VALID_DESIGNATION = ['Department Chair', 'Department Secretary', 'IT Program Coordinator','CS Program Coordinator','Department Extension Coordinator','Department Research Coordinator']

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            data = []
            errors = []

            for i, row in df.iterrows():
                row_errors = []

                username = generate_username(
                    row.get("first_name", ""),
                    row.get("last_name", "")
                )
                instructor_id = row.get("instructor_id")
                email = str(row.get("email", "")).strip()
                # ✅ Parse birthday safely
                birthday = row.get("birthday")
                age = None
                parsed_birthday = None
                date_of_employment = row.get("date_of_employment")
                parsed_date_of_employment = None                
                if birthday:
                    parsed_birthday = parse_date(str(birthday).strip())
                    
                    if parsed_birthday:
                        today = date.today()
                        age = today.year - parsed_birthday.year - (
                            (today.month, today.day) < (parsed_birthday.month, parsed_birthday.day)
                        )
                    else:
                        row_errors.append("Invalid birthday format")
                    
                if date_of_employment:
                    parsed_date_of_employment = parse_date(str(date_of_employment).strip())    

                # ❌ REQUIRED FIELDS CHECK
                if not username:
                    row_errors.append("Username is required")

                if not email:
                    row_errors.append("Email is required")

                # ❌ DUPLICATE CHECK
                if username and CustomUser.objects.filter(username=username).exists():
                    row_errors.append("Username already exists")

                if instructor_id and CustomUser.objects.filter(instructor_id=instructor_id).exists():
                    row_errors.append("Instructor ID already exists")

                # ❌ VALIDATION
                gender = str(row.get("gender", "")).strip()
                if gender and gender not in VALID_GENDERS:
                    row_errors.append("Invalid gender")

                employment_status = str(row.get("employment_status", "")).strip()
                if employment_status and employment_status not in VALID_EMPLOYMENT_STATUS:
                    row_errors.append("Invalid employment status")

                designation = str(row.get("designation", "")).strip()
                if designation and designation not in VALID_DESIGNATION:
                    row_errors.append("Invalid designation")

                academic_rank = str(row.get("academic_rank", "")).strip()
                if academic_rank and academic_rank not in VALID_ACADEMIC_RANK:
                    row_errors.append("Invalid academic rank")

                # STATUS FLAG
                can_upload = len(row_errors) == 0

                data.append({
                    "username": username,
                    "instructor_id": instructor_id,
                    "first_name": str(row.get("first_name", "")).strip(),
                    "last_name": str(row.get("last_name", "")).strip(),
                    "middle_name": str(row.get("middle_name", "")).strip(),
                    "email": email,
                    "gender": gender,
                    "birthday": parsed_birthday,
                    "age": age,
                    "academic_rank": academic_rank,
                    "designation": designation,
                    "employment_status": employment_status,
                    "date_of_employment": parsed_date_of_employment,
                    "can_upload": can_upload,
                    "errors": row_errors,
                    "is_staff": False
                })

                if not can_upload:
                    errors.append(f"Row {i+1}: {', '.join(row_errors)}")

            return JsonResponse({
                "success": True,
                "data": data,
                "errors": errors
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False})

@superadmin_required
@login_required  
def preview_users_student(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        VALID_GENDERS = ['Male', 'Female', 'Other']

        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            data = []
            errors = []

            for i, row in df.iterrows():
                row_errors = []

                username = generate_username(
                    row.get("first_name", ""),
                    row.get("last_name", "")
                )
                instructor_id = row.get("instructor_id")
                email = str(row.get("email", "")).strip()

                # ❌ REQUIRED FIELDS CHECK
                if not username:
                    row_errors.append("Username is required")

                if not email:
                    row_errors.append("Email is required")

                # ❌ DUPLICATE CHECK
                if username and CustomUser.objects.filter(username=username).exists():
                    row_errors.append("Username already exists")

                if instructor_id and CustomUser.objects.filter(instructor_id=instructor_id).exists():
                    row_errors.append("Instructor ID already exists")

                # ❌ VALIDATION
                gender = str(row.get("gender", "")).strip()
                if gender and gender not in VALID_GENDERS:
                    row_errors.append("Invalid gender")

                status = "Enrolled"


                # STATUS FLAG
                can_upload = len(row_errors) == 0

                data.append({
                    "username": username,
                    "first_name": str(row.get("first_name", "")),
                    "last_name": str(row.get("last_name", "")),
                    "email": email,
                    "gender": gender,
                    "position": "Student",
                    "organization": "",
                    "status": status,
                    "can_upload": can_upload,
                    "errors": row_errors,
                    "is_staff": False
                })

                if not can_upload:
                    errors.append(f"Row {i+1}: {', '.join(row_errors)}")

            return JsonResponse({
                "success": True,
                "data": data,
                "errors": errors
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False})

@superadmin_required
@login_required  
def bulk_upload_users_ajax(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            users = body.get("users", [])

            results = []

            with transaction.atomic():  # ✅ ensures all-or-nothing
                for row in users:
                    try:
                        first_name = row.get("first_name")
                        last_name = row.get("last_name")
                        instructor_id = row.get("instructor_id")
                        email = row.get("email")

                        username = row.get("username")

                        birthday = row.get("birthday")
                        age = row.get("age")


                        # ✅ Create user
                        user = CustomUser.objects.create(
                            instructor_id=instructor_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            middle_name=row.get("middle_name"),
                            email=email,
                            contact_info=row.get("contact_info"),
                            birthday=birthday,
                            age=age,
                            gender=row.get("gender"),
                            employment_status=row.get("employment_status"),
                            academic_rank=row.get("academic_rank"),
                            designation=row.get("designation"),
                            date_of_employment=row.get("date_of_employment"),
                            is_masteradmin=False,
                        )

                        # ✅ Set password properly
                        user.set_password("Default123")
                        user.save()

                        results.append({
                            "username": username,
                            "status": "success"
                        })

                    except Exception as e:
                        results.append({
                            "username": username,
                            "status": "failed",
                            "error": str(e)
                        })

            return JsonResponse({
                "success": True,
                "results": results
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            })

    return JsonResponse({"success": False})

@superadmin_required
@login_required  
def instructor_table(request):
    inst = CustomUser.objects.filter(is_superuser=False)

    return render(request, "partials/instructor_bulk_table.html", {
        "inst": inst
    })
#endregion

#region Admin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

CustomUser = get_user_model()

@superadmin_required
@login_required
@csrf_exempt  # Only if using AJAX without CSRF token
def create_admin(request):
    if request.method == "POST":
        # Correct POST keys based on modal inputs
        username = request.POST.get('user_name')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Basic validation
        if not all([username, first_name, last_name, email, password]):
            return JsonResponse({"status": "error", "message": "All fields are required"}, status=400)

        try:
            user = CustomUser(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_active=True,
                is_superuser=True,
                is_masteradmin=False,
            )
            user.set_password(password)  # ✅ Hash password
            user.save()
        except IntegrityError:
            return JsonResponse({"status": "error", "message": "Username or email already exists"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

        return JsonResponse({"status": "success", "message": "Admin user created successfully"})

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)

@superadmin_required
@login_required    
def update_admin(request, pk):
    if request.method == "POST":
        try:
            admin = CustomUser.objects.get(id=pk)
            
            # Update fields
            admin.first_name = request.POST.get("first_name", admin.first_name)
            admin.last_name = request.POST.get("last_name", admin.last_name)
            email = request.POST.get("email")
            if email:
                admin.email = email

            # Update password if provided
            password = request.POST.get("password")
            if password:
                admin.set_password(password)

            admin.save()

            return JsonResponse({"success": True})

        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

@superadmin_required
@login_required
def admin_users(request):
    users = CustomUser.objects.filter(is_superuser=True)

    data = [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "email": u.email
        }
        for u in users
    ]

    return JsonResponse({"users": data})

@superadmin_required
@login_required
def delete_admin(request, pk):
    if request.method == "POST":

        # 🔒 Only superadmins can delete
        if not request.user.is_superuser:
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # 🔍 Get target user first
        try:
            user = CustomUser.objects.get(id=pk)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # 🚫 Prevent self-delete
        if request.user.id == user.id:
            return JsonResponse({
                "error": "You cannot delete your own account."
            })

        # 🔢 Count superadmins
        superadmin_count = CustomUser.objects.filter(is_superuser=True).count()

        # 🚫 Prevent deleting last superadmin
        if user.is_superuser and superadmin_count <= 1:
            return JsonResponse({
                "error": "Cannot delete the last superadmin."
            })

        # ✅ Delete user
        user.delete()

        return JsonResponse({"status": "deleted"})
    
@superadmin_required
@login_required
def update_profile_photo(request, pk):
    if request.method == "POST" and request.FILES.get("image"):
        profile = CustomUser.objects.get(pk=pk)

        profile.profile_pic = request.FILES.get('image')
        profile.save()

        return JsonResponse({
            "success": True,
            "image_url": profile.profile_pic.url
        })

    return JsonResponse({"success": False, "error": "Invalid request"})

@superadmin_required
@login_required
def update_profile(request, pk):
    if request.method == "POST":
        try:
            profile = CustomUser.objects.get(pk=pk)

            profile.first_name = request.POST.get("first_name")
            profile.last_name = request.POST.get("last_name")

            profile.middle_name = request.POST.get("middle_name")
            profile.contact_info = request.POST.get("contact_number")
            profile.position = request.POST.get("position")
            profile.organization = request.POST.get("organization")
            profile.degree = request.POST.get("degree")
            profile.school = request.POST.get("school")
            
            profile.save()

            return JsonResponse({"status": "success", "message": "Updated successfully"})
        except:
            return JsonResponse({"status": "error", "message": "Update failed"})
#endregion

#region Test
def fingerprint_commands(request):
    """
    Device polls this endpoint to get pending commands
    """
    commands = FingerprintCommand.objects.filter(processed=False).order_by("created_at")
    cmd_list = [{"id": c.id, "cmd": c.cmd} for c in commands]
    return JsonResponse(cmd_list, safe=False)

# @api_view(['POST'])
def enroll_fingerprint(request):
    serializer = FingerprintSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def generate_random_id(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@csrf_exempt
def start_enroll(request):
    if request.method == "POST":
        try:
            random_id = generate_random_id()
            cmd = FingerprintCommand.objects.create(cmd="ENROLL", random_id=random_id)
            return JsonResponse({
                "success": True,
                "message": "ENROLL command queued",
                "id": cmd.id,
                "random_id": cmd.random_id
            })
        except Exception as e:
            # This will catch any error and show it in the response
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)

@csrf_exempt
def set_fingerprint_logs(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message = data.get("message", "")
        log_type = data.get("type", "info")
        fingerprint_id = data.get("fingerprint_id") or data.get("main") or data.get("backup")

        timestamp = timezone.now()

        extra_data = {k: v for k, v in data.items() if k not in ["message", "type", "timestamp", "fingerprint_id", "main", "backup"]}

        log_entry = FingerprintLogs.objects.create(
            message=message,
            log_type=log_type,
            fingerprint_id=fingerprint_id,
            timestamp=timestamp,
            extra_data=extra_data
        )

        print("Saved log:", log_entry.id, log_entry.timestamp, log_entry.message)
        return JsonResponse({"status": "saved", "log_id": log_entry.id})

    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def get_fingerprint_logs(request):
    if request.method == "GET":
        # Fetch unread logs only
        logs = FingerprintLogs.objects.filter(is_read=False).order_by("-created_at").values(
            "id", "message", "log_type", "fingerprint_id", "timestamp", "extra_data", "created_at"
        )

        return JsonResponse({"logs": list(logs)})

    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
@csrf_exempt
def get_fingerprint_logs_update(request, pk):
    if request.method == "POST":
        updated = FingerprintLogs.objects.filter(pk=pk).update(is_read=True)

        if updated:
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def start_verify(request):
    if request.method == "POST":
        # Create VERIFY command
        cmd = FingerprintCommand.objects.create(cmd="VERIFY")
        return JsonResponse({"success": True, "message": "VERIFY command queued"})
    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)



@csrf_exempt
def verify_fingerprint(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        data = json.loads(request.body)
        try:
            match_id = int(data.get("match_id"))
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "message": "Invalid match_id"})
        action = data.get("action")  # 👈 NEW

        if not action:
            return JsonResponse({"success": False, "message": "No action provided"})

        fingerprint = Fingerprint.objects.filter(
            Q(main_id=match_id) | Q(backup_id=match_id) | Q(extra_id=match_id)
        ).first()

        if not fingerprint:
            return JsonResponse({"success": False, "message": "Fingerprint not found"})

        return JsonResponse({"success": False, "message": "Invalid action"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt  # Since fetch is sending JSON
def fingerprint_command(request):
    """
    Proxy endpoint to send commands to local fingerprint scanner API.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        command = data.get("command")

        if command != "VERIFY":
            return JsonResponse({"success": False, "message": "Invalid command"}, status=400)

        # Send request to local fingerprint API
        response = requests.post(
            "http://127.0.0.1:8000/api/fingerprint/commands/",
            json={"command": command},
            timeout=5
        )

        api_data = response.json()

        # Expected response should have a 'success' key and optionally 'template'
        return JsonResponse({
            "success": api_data.get("success", False),
            "template": api_data.get("template", ""),
            "message": api_data.get("message", "")
        })

    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "message": f"Scanner unreachable: {str(e)}"}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
    
@csrf_exempt
def fingerprint_command_detail(request, cmd_id):
    try:
        cmd = FingerprintCommand.objects.get(id=cmd_id)
    except FingerprintCommand.DoesNotExist:
        return JsonResponse({"success": False, "message": "Command not found"}, status=404)

    if request.method == "DELETE":
        cmd.delete()
        return JsonResponse({"success": True, "message": "Command deleted"})

    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)

latest_status = {
    "state": "idle",
    "message": "Waiting..."
}

@api_view(['GET'])
def fingerprint_status(request):
    return Response(latest_status)


def getprofilebyfp(request, id):
    fingerprint = Fingerprint.objects.filter(
        Q(main_id=id) | Q(backup_id=id) | Q(extra_id=id)
    ).first()

    if not fingerprint:
        return JsonResponse({
            "success": False,
            "message": "Fingerprint not found"
        })

    user = fingerprint.user

    return JsonResponse({
        "success": True,
        "user": {
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "image": user.profile_pic.url if user.profile_pic else "/static/image/maleSil.jpg"
        }
    })
#endregion

# region Other-Users
@login_required
def dashboard_ins(request):
    return render(request, "users/dashboard.html")

@login_required
def news_ins(request):
    instructor = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'users/news.html', {
        'instructor': instructor
    })

@login_required
def schedule_ins(request):
    instructor = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'users/schedule.html', {
        'instructor': instructor
    })

@login_required
def dtr_ins(request):
    instructor = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'users/dtr.html', {
        'instructor': instructor
    })

@login_required
def profile_ins(request):
    instructor = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'users/profile.html', {
        'instructor': instructor
    })

@login_required
def update_my_profile(request):
    if request.method == "POST":
        birthday = request.POST.get("birthday")
        age = None

        if birthday:
            bday = date.fromisoformat(birthday)
            today = date.today()
            age = today.year - bday.year - (
                (today.month, today.day) < (bday.month, bday.day)
            )

        try:
            instr = CustomUser.objects.get(id=request.POST.get("id"))
            # only update if file exists
            if request.FILES.get("fileUpload"):
                instr.profile_pic = request.FILES.get("fileUpload")
            instr.first_name = request.POST.get("first_name")
            instr.last_name = request.POST.get("last_name")
            instr.middle_name = request.POST.get("middle_name")
            instr.email = request.POST.get("email")
            instr.contact_info = request.POST.get("contact_info")
            instr.birthday = birthday or None
            instr.age = age
            instr.gender = request.POST.get("gender")
            instr.employment_status = request.POST.get("employment_status")
            instr.academic_rank = request.POST.get("academic_rank")
            instr.designation = request.POST.get("designation")

            date_emp = request.POST.get("date_of_employment")
            instr.date_of_employment = date_emp or None

            instr.instructor_id = request.POST.get("instructor_id")
            instr.bs_degree = request.POST.get("bs_degree")
            instr.masters_degree = request.POST.get("masters_degree")
            instr.doctorate_degree = request.POST.get("doctorate_degree")
            instr.eligibility_type = request.POST.get("eligibility_type")
            instr.workloads = request.POST.get("workloads")  # match your form

            instr.save()

            return JsonResponse({"success": True})

        except CustomUser.DoesNotExist:
            return JsonResponse({"success": False, "message": "Instructor not found."})

    return JsonResponse({"success": False, "message": "Invalid request"})

@login_required
def change_my_password(request):
    if request.method == "POST":
        user = request.user

        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not user.check_password(current_password):
            return JsonResponse({"success": False, "error": "Current password is incorrect"})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "Passwords do not match"})

        if len(new_password) < 6:
            return JsonResponse({"success": False, "error": "Password must be at least 6 characters"})

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})

@login_required
def send_password_reset_email(request):
    if request.method == "POST":
        email = request.user.email
        if not email:
            return JsonResponse({"success": False, "error": "No email associated with this account"})
        
        # Use Django's default password reset system
        from django.contrib.auth.forms import PasswordResetForm
        form = PasswordResetForm({"email": email})
        if form.is_valid():
            form.save(request=request, use_https=True, email_template_name="password_ret_email.html")
            return JsonResponse({"success": True})
        
        return JsonResponse({"success": False, "error": "Failed to send email"})
    return JsonResponse({"success": False, "error": "Invalid request"})

@login_required
def view_profile(request, id):
    instructor = CustomUser.objects.get(id=id)
    return render(request, 'users/profileViewer.html', {
        'instructor': instructor
    })

# endregion

# region Other-Student
@login_required
def dashboard_student(request):
    return render(request, "others/dashboard.html")

@login_required
def news_student(request):
    student = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'others/news.html', {
        'student': student
    })

@login_required
def schedule_student(request):
    return render(request, "others/schedule.html")

@login_required
def dtr_student(request):
    return render(request, "others/dtr.html")

@login_required
def profile_student(request):
    student = CustomUser.objects.get(id=request.user.id) 
    return render(request, 'others/profile.html', {
        'student': student
    })

@login_required
def update_my_profile_student(request):
    if request.method == "POST":
        try:
            student = CustomUser.objects.get(id=request.POST.get("id"))

            student.first_name = request.POST.get("first_name")
            student.last_name = request.POST.get("last_name")
            student.email = request.POST.get("email")
            student.contact_info = request.POST.get("contact_info")

            if request.POST.get("birthday"):
                birth_date = date.fromisoformat(request.POST.get("birthday"))
                today = date.today()
                age = today.year - birth_date.year - (
                    (today.month, today.day) < (birth_date.month, birth_date.day)
                )
            student.birthday = request.POST.get("birthday")
            student.age = age or "N/A"
            # 🖼️ Handle image upload
            if request.FILES.get("profile_pic"):
                student.profile_pic = request.FILES["profile_pic"]

            student.save()

            return JsonResponse({
                "success": True,
                "profile_pic_url": student.profile_pic.url if student.profile_pic else None
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False})


@login_required
def change_my_password_student(request):
    if request.method == "POST":
        user = request.user

        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not user.check_password(current_password):
            return JsonResponse({"success": False, "error": "Current password is incorrect"})

        if new_password != confirm_password:
            return JsonResponse({"success": False, "error": "Passwords do not match"})

        if len(new_password) < 6:
            return JsonResponse({"success": False, "error": "Password must be at least 6 characters"})

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})

@login_required
def send_password_reset_email_student(request):
    if request.method == "POST":
        email = request.user.email
        if not email:
            return JsonResponse({"success": False, "error": "No email associated with this account"})
        
        # Use Django's default password reset system
        from django.contrib.auth.forms import PasswordResetForm
        form = PasswordResetForm({"email": email})
        if form.is_valid():
            form.save(request=request, use_https=True, email_template_name="password_ret_email.html")
            return JsonResponse({"success": True})
        
        return JsonResponse({"success": False, "error": "Failed to send email"})
    return JsonResponse({"success": False, "error": "Invalid request"})

# endregion