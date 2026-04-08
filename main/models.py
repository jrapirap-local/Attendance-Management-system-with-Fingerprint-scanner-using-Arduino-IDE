from django.db import models # type: ignore
from django.utils import timezone # type: ignore
from main.utils import generate_token
from django.contrib.auth.models import User, AbstractUser, Group, Permission # type: ignore
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth.hashers import make_password, check_password

# ================== Choice Classes ==================
class Gender(models.TextChoices):
    MALE = "Male", "Male"
    FEMALE = "Female", "Female"
    OTHER = "Other", "Other"

class EmploymentStatus(models.TextChoices):
    PERMANENT = "Permanent", "Permanent"
    TEMPORARY = "Temporary", "Temporary"
    CONTRACT = "Contract of Service", "Contract of Service"

class Designation(models.TextChoices):
    DEPT_CHAIR = "Department Chair", "Department Chair"
    DEPT_SECRETARY = "Department Secretary", "Department Secretary"
    IT_COORDINATOR = "IT Program Coordinator", "IT Program Coordinator"
    CS_COORDINATOR = "CS Program Coordinator", "CS Program Coordinator"
    EXT_COORDINATOR = "Department Extension Coordinator", "Department Extension Coordinator"
    RESEARCH_COORDINATOR = "Department Research Coordinator", "Department Research Coordinator"
    INSTRUCTOR = "Instructor", "Instructor"

class AcademicRank(models.TextChoices):
    INSTRUCTOR_1 = "Instructor 1", "Instructor 1"
    INSTRUCTOR_2 = "Instructor 2", "Instructor 2"
    INSTRUCTOR_3 = "Instructor 3", "Instructor 3"
    ASSISTANT_PROF_1 = "Assistant Professor 1", "Assistant Professor 1"
    ASSISTANT_PROF_2 = "Assistant Professor 2", "Assistant Professor 2"
    ASSISTANT_PROF_3 = "Assistant Professor 3", "Assistant Professor 3"
    ASSISTANT_PROF_4 = "Assistant Professor 4", "Assistant Professor 4"
    PROFESSOR_1 = "Professor 1", "Professor 1"
    PROFESSOR_2 = "Professor 2", "Professor 2"
    PROFESSOR_3 = "Professor 3", "Professor 3"
    PROFESSOR_4 = "Professor 4", "Professor 4"
    PROFESSOR_5 = "Professor 5", "Professor 5"

# ================== Custom User Model ==================
class CustomUser(AbstractUser):
    # ================= PERSONAL INFO =================
    profile_id = models.CharField(max_length=50, null=True, blank=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True)

    # ================= EMPLOYMENT =================
    instructor_id = models.CharField(max_length=10, blank=True, null=True)
    employment_status = models.CharField(max_length=50, choices=EmploymentStatus.choices, null=True)
    designation = models.CharField(max_length=100, choices=Designation.choices, null=True)
    academic_rank = models.CharField(max_length=100, choices=AcademicRank.choices, null=True)
    date_of_employment = models.DateField(blank=True, null=True)
    workloads = models.PositiveIntegerField(default=0)

    # ================= EDUCATION =================
    bs_degree = models.CharField(max_length=255, blank=True, null=True)
    masters_degree = models.CharField(max_length=255, blank=True, null=True)
    doctorate_degree = models.CharField(max_length=255, blank=True, null=True)
    eligibility_type = models.CharField(max_length=255, blank=True, null=True)

    # ================= CONTACT =================
    email = models.EmailField(unique=True, null=True)
    contact_info = models.CharField(max_length=20, blank=True, null=True)

    # ================= FILE =================
    profile_pic = models.ImageField(upload_to="instructors/%Y/%m/%d/", blank=True, null=True)

    # ================= BIOMETRICS =================
    main_id = models.CharField(max_length=100, blank=True, null=True)
    backup_id = models.CharField(max_length=100, blank=True, null=True)
    extra_id = models.CharField(max_length=100, blank=True, null=True)
    link_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # ================= SYSTEM =================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    # Account settings
    email_confirmed = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=20, blank=True, null=True)
    is_activated = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=20, blank=True, null=True)

    # Staff & superuser defaults
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_masteradmin = models.BooleanField(default=True)
    
    # Fix reverse accessor clashes
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    def __str__(self):
        return f"{self.username} ({self.first_name} {self.last_name})"
    
class Comlab(models.Model):
    comlab = models.CharField(max_length=150)  # Laboratory Name
    location = models.CharField(max_length=255)
    cards = models.ImageField(upload_to='comlabs/', blank=True, null=True)

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='comlab_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comlab_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)       

    def __str__(self):
        return self.comlab
    
class EquipmentBorrow(models.Model):
    STATUS_CHOICES = [
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ]

    name = models.CharField(max_length=255, verbose_name="Borrower Name")
    date = models.DateField(verbose_name="Date")
    time = models.TimeField(verbose_name="Time")
    equipment = models.CharField(max_length=255, verbose_name="Equipment")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='borrowed')

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='equipment_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)     

    def __str__(self):
        return f"{self.name} - {self.equipment} ({self.status})"
    
class Report(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    report = models.TextField()
    attachment = models.FileField(upload_to='reports/', blank=True, null=True)

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='reports_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_updated'
    )
    last_updated = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return f"{self.name} - {self.date}"
    

class Post(models.Model):
    body = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    is_private = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)
    likes = models.ManyToManyField("CustomUser", related_name="post_likes", blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='news_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='news_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)     

    def __str__(self):
        return self.body[:50]
    
class Comment(models.Model):
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # ✅ FIX
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.body[:20]}"
    
class FingerprintCommand(models.Model):
    CMD_CHOICES = [
        ("ENROLL", "Enroll"),
        ("VERIFY", "Verify"),
        ("DELETE_ALL", "Delete All"),
    ]
    
    cmd = models.CharField(max_length=20, choices=CMD_CHOICES)
    random_id = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.cmd} ({'done' if self.processed else 'pending'})"

class Fingerprint(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="fingerprint",
        null=True
    )

    main_id = models.PositiveIntegerField(unique=True, null=True)
    backup_id = models.PositiveIntegerField(unique=True, null=True)
    extra_id = models.PositiveIntegerField(unique=True, null=True)

    random_id = models.CharField(max_length=20, unique=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - FP({self.main_id})"
    
from django.db import models

from django.db import models
from django.utils import timezone

class FingerprintLogs(models.Model):
    FINGERPRINT_TYPES = [
        ("info", "Info"),
        ("raw", "Raw"),
        ("status", "Status"),
        ("json", "JSON"),
        ("error", "Error"),
    ]

    message = models.TextField()
    log_type = models.CharField(max_length=20, choices=FINGERPRINT_TYPES, default="info")
    fingerprint_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(null=True)
    extra_data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    command_id = models.IntegerField(null=True)

    def __str__(self):
        return f"[{self.log_type}] {self.message[:50]}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # save the new log first

        MAX_LOGS = 1000
        # Count total entries
        total_logs = FingerprintLogs.objects.count()
        if total_logs > MAX_LOGS:
            # Delete the oldest logs to maintain the limit
            excess = total_logs - MAX_LOGS
            oldest_logs = FingerprintLogs.objects.order_by("created_at")[:excess]
            FingerprintLogs.objects.filter(id__in=[log.id for log in oldest_logs]).delete()

def save(self, *args, **kwargs):
    if not self.id:
        self.id = str(uuid.uuid4())
    if not self.random_id:
        import random, string
        self.random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    super().save(*args, **kwargs)
    
class UserBiometric(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    # placeholder for fingerprint/biometric template
    fingerprint_template = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Biometric - {self.user.username}"
        
class Classroom(models.Model):
    name = models.CharField(max_length=100)
    room_code = models.CharField(max_length=20, unique=True)
    capacity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='classroom_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classroom_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)    

    def __str__(self):
        return self.name


class ClassroomSchedule(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    instructor = models.CharField(max_length=100)

    day = models.CharField(max_length=20)  # Monday, Tuesday, etc.
    start_time = models.TimeField()
    end_time = models.TimeField()

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='classroomsched_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classroomsched_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)    

    def __str__(self):
        return f"{self.classroom.name} - {self.day}"
    
class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='course_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='course_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)       

    def __str__(self):
        return self.name    
    
class Subjects(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="subjectcourse",
        null=True
    )

    # ✅ Upload tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name='subject_uploaded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Update tracking
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subject_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)       

    def __str__(self):
        return self.name
    
class Schedule(models.Model):
    DAYS = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
        ("Sunday", "Sunday"),
    ]

    instructor = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="dschedules"
    )

    subject = models.ForeignKey(
        "Subjects",
        on_delete=models.CASCADE,
        related_name="dschedules"
    )

    room = models.ForeignKey(
        "Classroom",
        on_delete=models.CASCADE,
        related_name="classroom_schedules",
        null=True,
        blank=True
    )

    comlab = models.ForeignKey(
        "ComLab",
        on_delete=models.CASCADE,
        related_name="classroom_schedules",
        null=True,
        blank=True
    )

    room_type = models.CharField(max_length=100, blank=True, null=True)

    section = models.CharField(max_length=100, blank=True, null=True)

    day = models.CharField(max_length=10, choices=DAYS)

    start_time = models.TimeField()
    end_time = models.TimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.subject} - {self.day} ({self.start_time} - {self.end_time})"
    

class Attendance(models.Model):
    user = models.ForeignKey("CustomUser", on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)

    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.date}"