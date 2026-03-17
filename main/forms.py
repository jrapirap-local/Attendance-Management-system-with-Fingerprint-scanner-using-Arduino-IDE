from django import forms # type: ignore
from .models import Employee, OrgChartList, Post, UserData, Equipment, Availability, Comlab, ComlabReport, StatusofEmployment,Ins_Schedule
from .models import  Employee, StatusofEmployment, AcademicalRank, Designation,Subject_Code, Subject_Title, Course_Year_Section
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import datetime  # Add this import


class SuperUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user

class Dtrc(forms.Form):
    image  = forms.ImageField(label='Profile Picture', required=False)
    name = forms.CharField()

class EditEmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'middle_name', 'last_name', 'birthday', 'age', 'status', 'position', 'organization', 'contract_of_service', 'rank', 'month', 'date', 'year', 'teaching_workload',
            'bs_degree', 'bs_school', 'bs_units',
            'masters_degree', 'masters_school',
            'doctorate_degree', 'doctorate_school',
            'field_specialization', 'eligibility_type', 'contact_no' , 'email'
        ]
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'contact_no': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),


        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure fresh queryset every time
        self.fields['status'].queryset = StatusofEmployment.objects.all()
        self.fields['position'].queryset = AcademicalRank.objects.all()
        self.fields['organization'].queryset = Designation.objects.all().order_by('rank')

class ListofstaffForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['idNum', 'first_name', 'last_name', 'middle_name', 'birthday', 'status', 'position', 'profile','age', 'gender','organization', 'fingerprint_id', 'backup_fingerprint_id','password']

class OrgChartListForm(forms.ModelForm):
    class Meta:
        model = OrgChartList
        fields = '__all__' 

class ListofstaffForms(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['idNum', 'first_name', 'last_name', 'middle_name', 'birthday', 'age', 'status', 'position', 'profile', 'gender', 'organization', 'fingerprint_id', 'backup_fingerprint_id', 'password']

class TimeRecordForm(forms.Form):
    idNum = forms.CharField(max_length=20)

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body', 'video', 'file']


class SuperUserLoginForm(forms.Form):
    username = forms.CharField(label='Username', max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    
class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'equipment', 'date', 'status']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['name', 'status']
        widgets = {
            'status': forms.Select(choices=Availability.STATUS_CHOICES)
        }

class AvailabilityEditForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['name', 'status']
        widgets = {
            'status': forms.Select(choices=Availability.STATUS_CHOICES)
        }

class UserDataForm(forms.ModelForm):
    class Meta:
        model = UserData
        fields = '__all__'  # List the fields you want to include in the form

class InsScheduleForm(forms.ModelForm):
    class Meta:
        model = Ins_Schedule
        fields = [
            'instructor',
            'subject_code',
            'subject_title',
            'course_year_section',
            'lecture',
            'laboratory',
            'room',
            'number_student'
        ]
        widgets = {
            'lecture': forms.TextInput(attrs={'placeholder': 'Lecture hours'}),
            'laboratory': forms.TextInput(attrs={'placeholder': 'Lab hours'}),
            'room': forms.TextInput(attrs={'placeholder': 'Room'}),
            'number_student': forms.TextInput(attrs={'placeholder': 'Number of students'}),
        }



class ComlabForm(forms.ModelForm):
    class Meta:
        model = Comlab
        fields = ['comlab', 'cards']

class ComlabReportForm(forms.ModelForm):
    class Meta:
        model = ComlabReport
        fields = ['name', 'date', 'time', 'report', 'attachment']

class SubjectCodeForm(forms.ModelForm):
    class Meta:
        model = Subject_Code
        fields = ['subjectcodes']
        widgets = {
            'subjectcodes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Subject Code'})
        }

class SubjectTitleForm(forms.ModelForm):
    class Meta:
        model = Subject_Title
        fields = ['subjecttitles']
        widgets = {
            'subjecttitles': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Subject Title'})
        }

class CourseYearSectionForm(forms.ModelForm):
    class Meta:
        model = Course_Year_Section
        fields = ['courseyearsections']
        widgets = {
            'courseyearsections': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Course Year & Section'})
        }