import django.contrib.auth.apps
from django.contrib import admin
from .models import ClassSearch, Cart, Course, Schedule, ScheduleItem, CourseTime

admin.site.register(ClassSearch)
admin.site.register(Cart)
admin.site.register(Course)
admin.site.register(CourseTime)
admin.site.register(Schedule)
admin.site.register(ScheduleItem)