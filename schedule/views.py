from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from .models import Cart, Course, Schedule, ScheduleItem, User, CourseTime
import requests
from django.utils import timezone
from django.http import HttpResponse


# View for Home Page
@login_required
def home(request):
    color_dict = {"pending": "yellow", "approved": "green", "denied": "red"}

    # Checks to make sure that the user is logged in to assign the correct name
    if request.user.is_authenticated:
        user = request.user
        role = ""
        username = user.username
    # Not Logged In is a placeholder currently
    else:
        user = "Not Logged In"

    # Assigns role (either Student or Advisor) based off of the user permissions
    if user.has_perm('global_permissions.is_advisor'):
        role = "Advisor"
    else:
        role = "Student"

    schedules = Schedule.objects.filter(user=request.user).values()
    has_schedule = len(schedules) != 0

    schedule = {"exists": has_schedule, "color": None, "status": None}
    if has_schedule:
        schedule['status'] = schedules[0]['status']
        schedule['color'] = color_dict[schedule['status'].lower()]

    return render(request, 'schedule/home.html', {'role': role, 'username': username, 'schedule': schedule})


@login_required
def see_users(request):
    curr_user = request.user
    if curr_user.has_perm('global_permissions.is_advisor'):
        user_list = []
        count = 0
        users = User.objects.all()

        for user in users:
            user_info = {'id': user.id, 'username': user.username, 'email': user.email,
                         'is_advisor': user.has_perm('global_permissions.is_advisor'),
                         'is_superuser': user.is_superuser,
                         'is_active': user.is_active}
            user_list.append(user_info)
            count = count + 1
        return render(request, 'schedule/see_users.html', {'user_list': user_list})
    else:
        return HttpResponse("You are not authorized to view this page.")


@login_required
def add_admin(request, user_id):
    curr_user = User.objects.get(pk=user_id)
    curr_user.groups.clear()
    advisor_group = Group.objects.get(name='Advisor')
    curr_user.groups.add(advisor_group)
    curr_user.save()

    return redirect('schedule:see_users')


@login_required
def remove_admin(request, user_id):
    curr_user = User.objects.get(pk=user_id)
    curr_user.groups.clear()
    student_group = Group.objects.get(name='Student')
    curr_user.groups.add(student_group)
    curr_user.save()

    return redirect('schedule:see_users')


# View for Submitted Schedules Page (Advisor)
def submissions(request):
    user = request.user
    if user.has_perm('global_permissions.is_advisor'):
        count = 0
        schedules = Schedule.objects.filter(submitted=True).values()
        context = {'schedules': []}

        for schedule in schedules:
            users = User.objects.get(pk=schedule['user_id'])
            items = ScheduleItem.objects.filter(schedule=schedule['id']).values()
            context['schedules'].append({'id': schedule['id'],'user': users, 'courses':[], 'status': schedule['status'],
                                         'approved_date': schedule['approved_date'], 'denied_date': schedule['denied_date'],
                                         'comments': schedule['comments'], 'comment_date': schedule['comment_date'],
                                         'total_units':schedule['total_units']})

            for item in items:
                course = Course.objects.get(pk=item['course_id'])
                context['schedules'][count]['courses'].append(course)
            count = count + 1

        return render(request, 'schedule/schedule_submissions.html', context)
    else:
        return HttpResponse("You are not authorized to view this page.")


# Logouts user and redirects them to the home page
def logout_view(request):
    logout(request)
    return redirect('schedule:home')


# Provides user with filters to search for course by year, term, department, and instructor name
subjects = []  # save subjects between searches


def get_subjects():
    raw_subjects = requests.get(
        "https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearchOptions?institution=UVA01&term=1228").json()

    for subject_info in raw_subjects["subjects"]:
        subjects.append(subject_info["subject"])

    subjects.sort()
    return subjects


@login_required
def course_search_view(request):
    base_url = "https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01"

    field_pattern = "&{}={}"

    courses = []

    # default field values
    fields = {'year': '2023', 'term': 'Fall', 'dept': '', 'instructor': '', 'course_name': '', 'course_nmbr': '',
              'only_open': False, 'start_time': '00:00', 'end_time': '23:59'}
    days = {'Mo': True, 'Tu': True, 'We': True, 'Th': True, 'Fr': True}
    active_class_messages = False
    no_classes_found = False
    class_messages = []

    # Initialize empty sets to store instructors
    instructors = set()

    if len(subjects) == 0:  # If mnemonics not retrieved
        raw_subjects = requests.get(
            "https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearchOptions?institution=UVA01&term=1228").json()

        for subject_info in raw_subjects["subjects"]:
            subjects.append(subject_info["subject"])

        subjects.sort()

    if request.method == "POST": # if search has been run
        fields = request.POST.copy() # save search fields

        year = fields.get('year')
        term = fields.get('term')
        subject = fields.get('subject')
        instructor = fields.get('instructor')
        course_name = fields.get('course_name')
        course_nmbr = fields.get('course_nmbr')
        catalog_nbr = fields.get('catalog_nbr')
        only_open = bool(fields.get('only_open'))
        start_time = fields.get('start_time')
        end_time = fields.get('end_time')

        if subject == "" and (start_time == "00:00" and end_time == "23:59"):
            messages.error(request, "Please enter a more specific search")
            active_class_messages = True
            class_messages.append("A Subject or Specific Time range is required")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages':active_class_messages,
                                                                   'class_messages': class_messages})

        if not catalog_nbr.isnumeric() and not catalog_nbr == "" :
            fields['catalog_nbr'] = ""
            catalog_nbr = ""
            active_class_messages = True
            class_messages.append("Catalog Number Field has been cleared due to an Invalid Value")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})
        if not course_nmbr.isnumeric() and not course_nmbr == "":
            course_nmbr = ""
            fields['course_nmbr'] = ""
            active_class_messages = True
            class_messages.append("Course Number Field has been cleared due to an Invalid Value")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})
        if " " in instructor:
            fields['instructor'] = instructor.split(" ")[0]
            active_class_messages = True
            class_messages.append("Instructor Field has been reverted to a Valid Value")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})

        if instructor and not instructor.isalnum() or instructor.isnumeric():
            del fields['instructor']
            active_class_messages = True
            class_messages.append("Instructor Field only accepts alphabetical characters")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})

        if " " in course_name:
            fields['course_name'] = course_name.split(" ")[0]
            active_class_messages = True
            class_messages.append("Course Name Field has been reverted to a Valid Value")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})

        if course_name and not course_name.isalnum():
            del fields['course_name']
            active_class_messages = True
            class_messages.append("Course Name Field only accepts alphabetical characters")
            no_classes_found = True
            return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields, 'days': days,
                                                                   'active_class_messages': active_class_messages,
                                                                   'class_messages': class_messages,
                                                                   'no_classes_found': no_classes_found})

        for day in days.keys():
            days[day] = bool(fields.get(day))

        if year == "":
            year = 2023

        num_term = 0
        if term == "Fall":
            num_term = 8
        elif term == "Spring":
            num_term = 2
        elif term == "Summer":
            num_term = 6

        search_url = base_url
        search_url += field_pattern.format("term", "1{}{}".format(int(year)%100, num_term))
        if subject:
            search_url += field_pattern.format("subject", subject)
        if instructor:
            search_url += field_pattern.format("instructor_name", instructor)
        if course_name:
            search_url += field_pattern.format("keyword", course_name)
        if course_nmbr:
            search_url += field_pattern.format("class_nbr", course_nmbr)
        if catalog_nbr:
            search_url += field_pattern.format("catalog_nbr", catalog_nbr)
        if only_open:
            search_url += field_pattern.format("enrl_stat", 'O')

        if list(days.values()).count(True) != len(days): # Filter by days checked in form
            filter_days = ""
            for day, checked in days.items():
                if checked:
                    filter_days += day

            search_url += field_pattern.format("days", filter_days)

        if start_time != "00:00" or end_time != "23:59":
            start_h, start_m = start_time.split(":") # convert to sis time range format (ex. 2:30 -> 2.5)
            start_m = round(int(start_m)/30)/2
            start_time = float(start_h) + float(start_m)

            end_h, end_m = end_time.split(":") # convert to sis time range format
            end_m = round(int(end_m)/30)/2
            end_time = float(end_h) + float(end_m)

            if start_time == 0.0:
                start_time = 0.5
            if end_time == 24.0:
                end_time = 23.5
            formatted_range = "{},{}".format(start_time, end_time)
            search_url += field_pattern.format("time_range", formatted_range)

        print(search_url)
        courses = requests.get(search_url).json()
        if len(courses) == 0:
            no_classes_found = True
    return render(request, 'schedule/course_search.html', {'courses': courses, 'fields': fields, 'subjects': subjects,
                                                           'days': days, 'active_class_messages' : active_class_messages,
                                                           'class_messages': class_messages,
                                                           'no_classes_found':no_classes_found})

#method is for testing purposes
def send_request(year, num_term, subject, instructor, url):
    field_pattern = "&{}={}"
    url += field_pattern.format("term", "1{}{}".format(int(year) % 100, num_term))
    if subject:
        url += field_pattern.format("subject", subject)
    if instructor:
        url += field_pattern.format("instructor_name", instructor)

    return requests.get(url).json()

def add_course_success(request):
    pass

# View to Add Course to Cart
@login_required
def add_course(request):
    days = {'Mo': True, 'Tu': True, 'We': True, 'Th': True, 'Fr': True}
    fields = {'start_time': "00:00", 'end_time': "23:59"}
    subjects = get_subjects()
    active_class_messages = False
    class_messages = []
    if request.method == 'POST':
        term = request.POST.get('term', '').strip()
        class_nbr = request.POST.get('class_nbr', '').strip()
        course_credits = request.POST.get('units_selector')

        # Validate input
        if not term:
            messages.error(request, 'Term is required. we got', term)
        elif not class_nbr:
            messages.error(request, 'Class Number is required.')
        else:
            # Build the SIS API URL
            url = f'https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term={term}&class_nbr={class_nbr}'

            # Make the request to the SIS API
            response = requests.get(url)

            if response.status_code == 200:

                # Parse the JSON response
                json_data = response.json()
                course_data = json_data[0]  # Assuming the course data is in the first element of the list

                # to isolate the last digit (2 or 8)
                # saves the term of the search when the add_course page is rerendered
                term = term[-1]
                if term == "8":
                    fields['term'] = "Fall"
                elif term == "2":
                    fields['term'] = "Spring"

                # Extract course information
                subject = course_data['subject']
                catalog_nbr = course_data['catalog_nbr']
                title = course_data['descr']
                instructor_name = course_data['instructors'][0]['name']
                term = int(term)
                units = 0
                if course_credits is None:
                    units = int(course_data['units'])
                else:
                    units = course_credits

                # Save the course to the user's cart
                cart, _ = Cart.objects.get_or_create(user=request.user)

                courses_in_cart = Course.objects.filter(cart=cart)
                if courses_in_cart:
                    for cart_course in courses_in_cart:
                        if cart_course.subject == subject and cart_course.catalog_nbr == catalog_nbr and cart_course.units == units:
                            messages.error(request, "Can not add identical course to Cart")
                            active_class_messages = True
                            class_messages.append("Can not add an identical course to Cart")
                            return render(request, 'schedule/course_search.html',
                                          {'subjects': subjects, 'fields': fields, 'days': days,
                                           'active_class_messages': active_class_messages,
                                           'class_messages': class_messages})

                course = Course(cart=cart, class_nbr=class_nbr, subject=subject, catalog_nbr=catalog_nbr, title=title,
                                instructor_name=instructor_name, units=units, term=term)
                course.save()

                for json_days in course_data['meetings']:
                    start_time = json_days['start_time'][0:5].replace(".", ":")
                    end_time = json_days['end_time'][0:5].replace(".", ":")
                    all_days = json_days['days']

                    time = CourseTime.objects.create(course=course, days=all_days, starting_time=start_time,
                                                     ending_time=end_time)
                    time.save()

                active_class_messages = True
                good_message = True
                class_messages.append("Course added successfully!")
                messages.success(request, 'Course added successfully!')
                return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields': fields,
                                                                       'days': days,
                                                                       'active_class_messages': active_class_messages,
                                                                       'good_message': good_message,
                                                                       'class_messages': class_messages})
            else:
                messages.error(request, 'Failed to fetch course data.')

    #resest all the filters so the website doesn't break on a following course search
    return render(request, 'schedule/course_search.html', {'subjects': subjects, 'fields':fields, 'days':days, 'active_class_messages':active_class_messages, 'class_messages':class_messages})


# View for View Cart Page
@login_required
def view_cart(request):
    # Get the user's cart
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Get the user's schedule
    schedules = Schedule.objects.filter(user=request.user)

    if schedules.count() == 0:
        schedule = Schedule.objects.create(user=request.user)
        schedule.save()
        schedules = Schedule.objects.filter(user=request.user)

    context_courses = []
    courses = Course.objects.filter(cart=cart)
    for course in courses:
        times = CourseTime.objects.filter(course=course)
        all_times = []
        for time in times:
            all_times.append({'days': time.days, 'starting_time': time.starting_time, 'ending_time': time.ending_time})
        context_courses.append({'course': course, 'all_times': all_times})

    current_id = schedules.first().id
    if request.method == "POST":
        current_id = int(request.POST.get('schedule_id'))

    context_schedules = []
    for schedule in schedules:
        context_schedules.append({'id': schedule.id, 'title': schedule.title, 'submitted': schedule.submitted})

    # Render the view_cart template with the courses
    context = {'courses': context_courses, 'schedules': context_schedules, 'current_id': current_id}
    return render(request, 'schedule/view_cart.html', context)


# Removes a course from the user's cart
@login_required
def remove_course(request, course_id, schedule_id):
    course = get_object_or_404(Course, id=course_id, cart__user=request.user)
    course.delete()
    messages.success(request, 'Course removed from cart.')
    context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
               'schedules': get_context_schedules(request.user),
               'active_class_messages': True, 'good_message': True,
               'class_messages': "Course removed!"}
    return render(request, 'schedule/view_cart.html', context)


# Get schedules associated with the user for rerendering
def get_context_schedules(user):
    context_schedules = []
    for schedule in Schedule.objects.filter(user=user):
        context_schedules.append({'id': schedule.id, 'title': schedule.title, 'submitted': schedule.submitted})

    return context_schedules


def get_context_courses(user):
    # Get the user's cart
    cart, _ = Cart.objects.get_or_create(user=user)

    context_courses = []
    courses = Course.objects.filter(cart=cart)

    for course in courses:
        times = CourseTime.objects.filter(course=course)
        all_times = []

        for time in times:
            all_times.append({'days': time.days, 'starting_time': time.starting_time, 'ending_time': time.ending_time})
        context_courses.append({'course': course, 'all_times': all_times})

    return context_courses


# Adds a course to the user's schedule from their cart
@login_required
def add_to_schedule(request, schedule_id, course_id):
    course = get_object_or_404(Course, id=course_id, cart__user=request.user)
    schedule, _ = Schedule.objects.get_or_create(id=schedule_id, user=request.user)
    total_units = schedule.total_units

    times = CourseTime.objects.filter(course=course)  # get all meetings of course thats to be added
    items = ScheduleItem.objects.filter(schedule=schedule.id)
    for item in items:
        added_course = Course.objects.get(pk=item.course.id)  # get all courses already in schedule
        if added_course.subject == course.subject and added_course.catalog_nbr == course.catalog_nbr \
                and added_course.units == course.units:
            context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
                       'schedules': get_context_schedules(request.user),
                       'active_class_messages': True,
                       'class_messages': "Can not add this course, the same course is already added"}
            return render(request, 'schedule/view_cart.html', context)
        if added_course.term != course.term:
            messages.error(request, "Can not add course from a different Term to Cart")
            context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
                       'schedules': get_context_schedules(request.user),
                       'active_class_messages': True,
                       'class_messages': "Can't add a Course from a different term to this schedule. Use another schedule, or remove all courses from this schedule before adding this Course"}
            return render(request, 'schedule/view_cart.html', context)

        added_course_times = CourseTime.objects.filter(course=added_course)  # get these already-added course times
        for time in times:
            if not time:
                time_starting_hour = int(time.starting_time.split(":")[0])
                time_ending_hour = int(time.ending_time.split(":")[0])

                # splits each day string "MoWe" into tokens of 2 characters ["Mo", "We"]
                split_days = [time.days[i:i + 2] for i in range(0, len(time.days), 2)]

                for added_course_time in added_course_times:
                    for day in split_days:
                        # if the to-be-added course has any day in common with an existing class
                        if day in added_course_time.days:
                            added_course_starting_hour = int(added_course_time.starting_time.split(":")[0])
                            added_course_ending_time = int(added_course_time.ending_time.split(":")[0])

                            added_course_starting_minutes = int(added_course_time.starting_time.split(":")[1])
                            added_course_ending_minutes = int(added_course_time.ending_time.split(":")[1])
                            time_starting_minutes = int(time.starting_time.split(":")[1])
                            time_ending_minutes = int(time.ending_time.split(":")[1])
                            if (added_course_starting_hour <= time_starting_hour <= added_course_ending_time and
                                time_starting_minutes < added_course_ending_minutes) or \
                                    (time_starting_hour <= added_course_starting_hour <= time_ending_hour and
                                     time_ending_minutes > added_course_starting_minutes):
                                messages.error(request, 'Courses overlap!')
                                course.save()
                                # Get the user's cart
                                cart, _ = Cart.objects.get_or_create(user=request.user)

                                # Get the courses associated with the cart
                                courses = Course.objects.filter(cart=cart)

                                # Render the view_cart template with the courses
                                context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
                                           'schedules': get_context_schedules(request.user),
                                           'active_class_messages': True,
                                           'class_messages': "Can not add this course, it overlaps with a class already in your schedule."}
                                return render(request, 'schedule/view_cart.html', context)

    if schedule.total_units + course.units > 19:
        # Get the user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Get the courses associated with the cart and exclude those in the user's schedule
        courses = Course.objects.filter(cart=cart).exclude(scheduleitem__schedule=schedule)

        # Render the view_cart template with the courses
        context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
                   'schedules': get_context_schedules(request.user),
                   'active_class_messages': True,
                   'class_messages': "Can not add this course, it will surpass the 19 credit limit."}
        return render(request, 'schedule/view_cart.html', context)
    schedule.total_units = total_units + course.units
    if schedule.submitted:
        schedule.submitted = False
    schedule.save()

    schedule_item = ScheduleItem(schedule=schedule, course=course)
    schedule_item.save()

    course.cart = None
    course.save()

    context = {'courses': get_context_courses(request.user), 'current_id': schedule_id,
               'schedules': get_context_schedules(request.user),
               'active_class_messages': True, 'good_message': True,
               'class_messages': "Course added to Schedule successfully."}
    return render(request, 'schedule/view_cart.html', context)

# View for View Schedule Page
@login_required
def view_schedule(request):
    schedules = Schedule.objects.filter(user=request.user)

    schedule = None
    if request.method == "POST":
        schedule = schedules.get(title=request.POST.get('title'))
    elif schedules.count() != 0:
        schedule = schedules.first()
    else:
        schedule = Schedule.objects.create(user=request.user)
        schedule.save()
    schedules = Schedule.objects.filter(user=request.user)

    titles = []
    for s in schedules:
        titles.append(s.title)

    context = {'schedule': {'id': schedule.id, 'title': schedule.title, 'total_units': schedule.total_units,
                            'submitted': schedule.submitted, 'status': schedule.status,
                            'approved_date': schedule.approved_date,
                            'denied_date': schedule.denied_date, 'comments': schedule.comments,
                            'comment_date': schedule.comment_date,
                            'courses': []}, 'titles': titles}
    schedule_items = ScheduleItem.objects.filter(schedule=schedule)

    for item in schedule_items:
        # course = Course.objects.get(course = item.course)
        course = item.course
        times = CourseTime.objects.filter(course=course)
        all_times = []
        for time in times:
            all_times.append({'days': time.days, 'starting_time': time.starting_time, 'ending_time': time.ending_time})
        context['schedule']['courses'].append({'course': course, 'all_times': all_times})
    return render(request, 'schedule/view_schedule.html', context)


def remove_course_from_schedule(request, schedule_id, course_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id, user=request.user)
    course = get_object_or_404(Course, pk=course_id)

    schedule.total_units = schedule.total_units - course.units
    course.delete()
    schedule.save()

    schedules = Schedule.objects.filter(user=request.user)

    titles = []
    for s in schedules:
        titles.append(s.title)

    context = {'schedule': {'id': schedule.id, 'title': schedule.title, 'total_units': schedule.total_units,
                            'submitted': schedule.submitted, 'status': schedule.status,
                            'approved_date': schedule.approved_date,
                            'denied_date': schedule.denied_date, 'comments': schedule.comments,
                            'comment_date': schedule.comment_date,
                            'courses': []}, 'titles': titles, 'class_messages': "Course Removed!",
               'active_class_messages': True}
    schedule_items = ScheduleItem.objects.filter(schedule=schedule)

    for item in schedule_items:
        # course = Course.objects.get(course = item.course)
        course = item.course
        times = CourseTime.objects.filter(course=course)
        all_times = []
        for time in times:
            all_times.append({'days': time.days, 'starting_time': time.starting_time, 'ending_time': time.ending_time})
        context['schedule']['courses'].append({'course': course, 'all_times': all_times})
    return render(request, 'schedule/view_schedule.html', context)


def unsubmit_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    schedule.submitted = False
    schedule.save()
    return redirect('schedule:view_schedule')

# Submits schedule to advisor
@login_required
def submit_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)

    # Replace "advisor_username" with the username of the student's advisor username
    advisor = get_object_or_404(User, username="glendonchin")
    schedule.advisor = advisor
    schedule.submitted = True
    schedule.status = "Pending"
    schedule.comments = None
    schedule.approved_date = None
    schedule.denied_date = None
    schedule.comment_date = None
    schedule.save()
    messages.success(request, 'Schedule submitted to advisor.')
    return redirect('schedule:view_schedule')


from django.contrib.auth.decorators import user_passes_test

# Helper function to check if a user is an advisor
def is_advisor(user):
    #is_advisor = user.groups.filter(name='glendonchin').exists()
    user_is_advisor = False
    if user.has_perm('global_permissions.is_advisor'):
        user_is_advisor = True
    print(f"User {user.username} is advisor: {is_advisor}")
    return user_is_advisor

@login_required
@user_passes_test(is_advisor)
def approve_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    print(f"Before approval: {schedule.status}")  # Add this line
    schedule.status = 'Approved'
    schedule.approved = True
    schedule.approved_date = timezone.now()
    schedule.denied_date = None
    schedule.save()
    schedule.refresh_from_db()  # Add this line
    print(f"After approval: {schedule.status}")  # Add this line
    # Redirect to the submissions page
    return redirect('schedule:submissions')

@login_required
@user_passes_test(is_advisor)
def deny_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    schedule.status = 'Denied'
    schedule.approved = False
    schedule.denied_date = timezone.now()
    schedule.submitted = False
    schedule.approved_date = None
    schedule.total_units = 0
    schedule.save()
    schedule.schedule_items.all().delete()
    messages.success(request, 'Schedule denied and cleared.')
    return redirect('schedule:submissions')


@login_required
@user_passes_test(is_advisor)
def add_comments(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)

    if request.method == 'POST':
        comments = request.POST.get('comments')
        schedule.comments = comments
        schedule.comment_date = timezone.now()
        schedule.save()
        messages.success(request, 'Comments added to the schedule.')
        return redirect('schedule:submissions')

    return render(request, 'add_comments.html', {'schedule': schedule})


@login_required
def delete_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    schedule.delete()

    # ensure user always has one schedule
    if Schedule.objects.filter(user=request.user).count() == 0:
        Schedule.objects.create(user=request.user).save()

    return redirect('schedule:view_schedule')


@login_required
def create_schedule(request):
    context = {}
    if request.method == "POST":
        title = request.POST.get('title')

        if " " in title:
            context['is_error'] = True
            context['error_message'] = 'Can not have a space in your schedule title, please try again'
        elif title == "":
            context['is_error'] = True
            context['error_message'] = 'The Title box cannot be blank, please try again'
        elif Schedule.objects.filter(user=request.user, title=title).count() != 0:
            context['is_error'] = True
            context['error_message'] = 'A schedule with that name already exists, please choose another.'
        else:
            schedule = Schedule.objects.create(user=request.user, title=title)
            schedule.save()
            return redirect('schedule:view_schedule')

    return render(request, 'schedule/create_schedule.html', context)


@login_required
def rename_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    context = {'schedule': {'id': schedule_id, 'title': schedule.title}}

    if request.method == "POST":
        title = request.POST.get('title')

        if " " in title:
            context['is_error'] = True
            context['error_message'] = 'Can not have a space in your schedule title, please try again'
        elif title == "":
            context['is_error'] = True
            context['error_message'] = 'The New Title box cannot be blank, please try again'
        elif Schedule.objects.filter(user=request.user, title=title).count() != 0:
            context['is_error'] = True
            context['error_message'] = 'A schedule with that name already exists, please choose another.'
        else:
            schedule.title = title
            schedule.save()
            return redirect('schedule:view_schedule')

    return render(request, 'schedule/rename_schedule.html', context)
