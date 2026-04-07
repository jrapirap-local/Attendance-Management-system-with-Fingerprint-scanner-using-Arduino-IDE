from django import forms
from .models import Post, Schedule
from django.utils import timezone

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['body', 'image', 'is_pinned', 'is_announcement']        

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = '__all__'


class UploadFileForm(forms.Form):
    file = forms.FileField()