from django.db import models # type: ignore
from django.utils import timezone # type: ignore
from django.contrib.auth.models import User # type: ignore


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
class UserData(models.Model):
    profile_id = models.IntegerField(default=1)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    data_field = models.CharField(max_length=255)
    profile_picture = models.ImageField(upload_to='profile_pictures', null=True, blank=True)
    bio = models.TextField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Existing fields
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    address = models.CharField(max_length=255, null=True, blank=True)  # Assuming you want address in your profile
    date_of_birth = models.DateField(null=True, blank=True)  # You can add date_of_birth if needed
    age = models.IntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    current_workplace = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)

    # New fields
    working_experience = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}"
    
class Attendance(models.Model):
    IdNum = models.CharField(max_length=5, default='')
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    #username = models.CharField(max_length=100, unique=True)
    #email = models.EmailField(unique=True)
    #address = models.TextField()
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    #gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date = models.DateField(null=True, blank=True)
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('leave', 'Leave'),
        ('in', 'In'),
        ('out', 'Out'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in')  # Adding the status field with choices

    def __str__(self):
        return self.first_name
    
class History(models.Model):
    IdNum = models.CharField(max_length=5, default='')
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    time_in = models.TimeField(null=True, blank=True, default=timezone.now)
    time_out = models.TimeField(null=True, blank=True, default=timezone.now)
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    attendance = models.OneToOneField(Attendance, on_delete=models.CASCADE)
    monday_start = models.TimeField(null=True, blank=True)
    monday_end = models.TimeField(null=True, blank=True)
    tuesday_start = models.TimeField(null=True, blank=True)
    tuesday_end = models.TimeField(null=True, blank=True)
    wednesday_start = models.TimeField(null=True, blank=True)
    wednesday_end = models.TimeField(null=True, blank=True)
    thursday_start = models.TimeField(null=True, blank=True)
    thursday_end = models.TimeField(null=True, blank=True)
    friday_start = models.TimeField(null=True, blank=True)
    friday_end = models.TimeField(null=True, blank=True)
    saturday_start = models.TimeField(null=True, blank=True)
    saturday_end = models.TimeField(null=True, blank=True)
    sunday_start = models.TimeField(null=True, blank=True)
    sunday_end = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"Schedule for {self.attendance.IdNum}"

class Employee(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    )

    WHEREABOUTS_CHOICES = (
        ('IN', 'IN'),
        ('OUT', 'OUT'),
        ('CLASS', 'CLASS'),
        ('OFFICIAL BUSINESS', 'OFFICIAL BUSINESS'),
        ('ON LEAVE', 'ON LEAVE'),
        ('MEETING', 'MEETING'),
    )

    idNum = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    birthday = models.DateField(default='1999-05-24')
    age = models.PositiveIntegerField(default=25)

    # Dynamic choices via ForeignKey
    status = models.ForeignKey('StatusofEmployment', on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    position = models.ForeignKey('AcademicalRank', on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    organization = models.ForeignKey('Designation', on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")

    profile = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    whereabouts = models.CharField(max_length=20, default='OUT', choices=WHEREABOUTS_CHOICES)
    fingerprint_id = models.CharField(max_length=20, null=True, blank=True)
    backup_fingerprint_id = models.CharField(max_length=20, null=True, blank=True)
    password = models.CharField(max_length=128, default='')  # if not using Django auth

    contract_of_service = models.CharField(max_length=100, blank=True, null=True)
    rank = models.CharField(max_length=100, blank=True, null=True)
    month = models.CharField(max_length=20, blank=True, null=True)
    date = models.PositiveIntegerField(blank=True, null=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    teaching_workload = models.PositiveIntegerField(blank=True, null=True)

    # ---Contact info ---
    contact_no = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)

    # --- Education Fields ---
    bs_degree = models.CharField(max_length=150, blank=True, null=True)
    bs_school = models.CharField(max_length=150, blank=True, null=True)
    bs_units = models.CharField(max_length=50, blank=True, null=True)
    masters_degree = models.CharField(max_length=150, blank=True, null=True)
    masters_school = models.CharField(max_length=150, blank=True, null=True)
    doctorate_degree = models.CharField(max_length=150, blank=True, null=True)
    doctorate_school = models.CharField(max_length=150, blank=True, null=True)

    # --- Other Info ---
    field_specialization = models.CharField(max_length=10, blank=True, null=True)  # Yes/No
    eligibility_type = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class StatusofEmployment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class AcademicalRank(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Designation(models.Model):
    name = models.CharField(max_length=255)
    rank = models.PositiveIntegerField(default=999)  # smaller = higher priority

    def __str__(self):
        return f"{self.name} (rank {self.rank})"


     
class TimeRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)


class DailyTimeRecords(models.Model):
    image = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class OrgChartList(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=100, null=True, blank=True)
    title = models.TextField(blank=True)
    position_dcs = models.OneToOneField('PositionDCS', on_delete=models.CASCADE, blank=True, null=True)

    @property
    def name(self):
        if self.employee:
            return f"{self.employee.first_name} {self.employee.last_name}"
        return "No Employee Assigned"

    @property
    def profile(self):
        if self.employee:
            return self.employee.profile.url if self.employee.profile else None
        return None

    def __str__(self):
        return self.name


    
class PositionDCS(models.Model):
    positions = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.positions

class Post(models.Model):
    author = models.ForeignKey(Employee, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    file = models.FileField(upload_to='files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']  

    def __str__(self):
        if self.title:
            return f"{self.author.first_name} - {self.title}"
        return f"{self.author.first_name} - {self.body[:30]}"
    
class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='posts/')    


class SuperUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Equipment(models.Model):
    STATUS_CHOICES = [
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ]

    name = models.CharField(max_length=100)
    equipment = models.CharField(max_length=100)
    date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='borrowed')

    def __str__(self):
        return self.name

class Comlab(models.Model):
    cards = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    comlab = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.comlab
    
class Availability(models.Model):
    STATUS_CHOICES = (
        ('In', 'In'),
        ('Out', 'Out'),
        ('On Class', 'On Class'),
        ('On Break', 'On Break'),
        ('On Leave', 'On Leave'),
        ('Absent', 'Absent'),
    )
    name = models.CharField(max_length=50)
    status = models.CharField(max_length=20,  default='', choices=STATUS_CHOICES)

    def __str__(self):
        return self.name


class Instructor(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    profile = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class Subject_Code(models.Model):
    subjectcodes = models.CharField(max_length=50)
    def __str__(self):
        return f"{self.subjectcodes}"

class Subject_Title(models.Model):
    subjecttitles = models.CharField(max_length=50)
    def __str__(self):
        return f"{self.subjecttitles}"

class Course_Year_Section(models.Model):
    courseyearsections = models.CharField(max_length=50)
    def __str__(self):
        return f"{self.courseyearsections}"

class Ins_Schedule(models.Model):
    instructor = models.ForeignKey(Employee,on_delete=models.CASCADE,to_field='idNum',blank=True,null=True)
    subject_code = models.ForeignKey(Subject_Code,on_delete=models.CASCADE, blank=True,null=True)
    subject_title = models.ForeignKey(Subject_Title,on_delete=models.CASCADE, blank=True,null=True)
    course_year_section = models.ForeignKey(Course_Year_Section,on_delete=models.CASCADE, blank=True,null=True)
    lecture = models.CharField(max_length=100, default='N/A')
    laboratory = models.CharField(max_length=50, default='N/A')
    number_student = models.CharField(max_length=50, default='N/A')
    room = models.CharField(max_length=50, default='N/A')

    def __str__(self):
        return f"{self.subject_code} - {self.subject_title}"

    
        
class PersonalInfo(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE,null=True, blank=True)
    full_name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    position = models.CharField(max_length=100)
    experience = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)
    skills = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.full_name

class ComlabReport(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    report = models.TextField()
    attachment = models.FileField(upload_to='comlab_reports/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.date} {self.time}"