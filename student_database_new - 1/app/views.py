from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Details,Course
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import Q
from .models import Course, StudentCourse
from .models import Teacher, Course, StudentSection, Announcement
def index(request):
    return render(request,'index.html')

def signup(request):   #done
    if request.method == "POST":
        name = request.POST['name']
        regno = request.POST['regno']
        email = request.POST['email']
        gender = request.POST['gender']
        contact_number = request.POST['contact_number']
        branch = request.POST['branch']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        # Check if passwords match
        if password != confirm_password:
            messages.warning(request, "Passwords do not match.")
            return redirect('signup')  # Redirect to signup page if passwords don't match

        # Check if the username (regno) already exists in the database
        if User.objects.filter(username=regno).exists():
            messages.warning(request, "Username already exists.")
            return redirect('signup')  # Redirect to signup page if username exists
        
        try:
            # Create the user with username as email and password
            user = User.objects.create_user(username=regno, email=email, password=password)
            
            # Create the associated details record
            details = Details.objects.create(user=user, regno=regno, name=name, email=email, gender=gender,
                                             contact_number=contact_number, branch=branch)
            
            messages.success(request, "Account created successfully.")
            return redirect('signin_student')  # Redirect to login page after successful signup

        except Exception as e:
            messages.error(request, str(e))
            return redirect('signup') #redirecting url is passed 
        
    return render(request, 'signup.html')
         ################################STUDENTS################################

def signin_student(request):   #done
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('studentlanding_page')  # Redirect to home page after successful login
        else:
            messages.warning(request, "Invalid username or password")
            return render(request, 'signin_student.html')

    return render(request, 'signin_student.html')


# The @login_required decorator is used in Django to ensure that
# only authenticated users can access a particular view. 
@login_required
def studentlanding_page(request):   #done
    user = request.user
    try:
        details = Details.objects.get(user=user)
    except Details.DoesNotExist:
        return HttpResponse("Details record does not exist for this user.")

    # Get the student's sections
    student_section = StudentSection.objects.get(regno__user=user).section

    # Get the student's courses
    student_courses = StudentCourse.objects.filter(regno=details).values_list('course_code', flat=True)

    # Filter announcements
    announcements = Announcement.objects.filter(
        Q(section__in=student_section, regno__branch=details.branch,regno__teacher__course_code__in=student_courses) |  # Announcements for student's sections and branch
        Q(section__isnull=True) # Announcements without sections
        ).distinct()

    context = {
        'announcements': announcements,
        'username': details.name,
        'details': details
    }

    return render(request, 'student_landingpage.html', context)



# course_dashboard is for displaying all the course he can opt and the courses he opted
@login_required
def course_dashboard(request): #done
    if request.user.is_authenticated:
        student = request.user.details
        student_department = student.branch
    else:
        student_department = None

    if student_department:
        available_courses = Course.objects.filter(dept=student_department).exclude(studentcourse__regno=student)
    else:
        available_courses = None

    if student:
        opted_courses = StudentCourse.objects.filter(regno=student).select_related('course_code')
    else:
        opted_courses = None

    context = {
        'available_courses': available_courses,
        'opted_courses': opted_courses
    }
    return render(request, 'course_dashboard.html', context)
@login_required
def opt_course(request):  #done
    if request.method == 'POST':
        # Get the logged-in student
        student = request.user.details
        # Get the course IDs selected by the student
        selected_course_ids = request.POST.getlist('course_id')
        # Opt each selected course for the student
        for course_id in selected_course_ids:
            course = Course.objects.get(id=course_id)
            # Check if the student has already opted for the course
            if not StudentCourse.objects.filter(regno=student, course_code=course).exists():
                # Opt the course for the student
                StudentCourse.objects.create(regno=student, course_code=course)

    # Redirect to the course dashboard after opting courses
    return redirect('course_dashboard')

# to display the count of classes he attended in a course
@login_required
def student_attendance(request): #done
    user = request.user
    try:
        student_details = Details.objects.get(user=user)
    except Details.DoesNotExist:
        return HttpResponse("Details record does not exist for this user.")

    # Get all courses the student has opted for
    student_courses = StudentCourse.objects.filter(regno=student_details)
    student_section = StudentSection.objects.get(regno=student_details).section
    context = {
        'student_details': student_details,
        'student_courses': student_courses,
        'student_section': student_section,
    }

    return render(request, 'student_attendance.html', context)

@login_required
def student_marks(request): #done
    user = request.user
    try:
        student_details = Details.objects.get(user=user)
    except Details.DoesNotExist:
        return HttpResponse("Details record does not exist for this user.")

    # Get all courses the student has opted for along with their marks
    student_courses = StudentCourse.objects.filter(regno=student_details)
    student_section = StudentSection.objects.get(regno=student_details).section
    context = {
        'student_details': student_details,
        'student_courses': student_courses,
        'student_section': student_section,
    }

    return render(request, 'student_marks.html', context)

################################TEACHERS################################

#signin teacher
def signin_teacher(request): #done
        if request.method == "POST":
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username, password=password)
            if user is not None:
              login(request, user)
              return redirect('teacherlanding_page')  # Redirect to home page after successful login
            else:
             messages.warning(request, "Invalid username or password")
        return render(request, 'signin_teacher.html')
    
@login_required   #done
def teacherlanding_page(request):
        profile = Details.objects.get(user=request.user)
        context = {
            'username': profile.name,
        }
        return render(request, 'teacher_landingpage.html', context)


@login_required
def teacher_course_details(request): #done
    try:
        # Get the teacher associated with the current user
        teacher = Teacher.objects.get(user=request.user)
        profile = Details.objects.get(user=request.user)
        context = {
            'username': profile.name,
        }
        # Fetch courses assigned to the teacher
        courses = Course.objects.filter(course_code=teacher.course_code)

        course_details = []
        for course in courses:
            course_details.append({
                'course_name': course.course_name,
                'course_code': course.course_code,
                'dept': course.dept,
                'section':teacher.section,
            })
    except Teacher.DoesNotExist:
        # Handle the case where the teacher doesn't exist
        course_details = []

    return render(request, 'teacher_course_details.html', {'course_details': course_details, 'context': context})


# to show and update attedance and marks of students
@login_required
def student_detail(request):
    teacher = None
    course_codes = None
    sections = None
    
    if request.user.is_authenticated:
        teacher = Teacher.objects.get(user=request.user)
        profile = Details.objects.get(user=request.user)
        if teacher:
            course_codes = teacher.course_code
            sections = teacher.section
            student_courses = StudentCourse.objects.filter(course_code__course_code=course_codes, regno__studentsection__section=sections)
    context = {
        'student_courses': student_courses,
        'teacher': teacher,
        'course_codes': course_codes,
        'sections': sections,
        'profile': profile.name,
    }
    return render(request, 'student_detail.html', context)

@login_required
def update_attendance(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        attendance = request.POST.get('attendance')
        if course_id and attendance:
            # Validate attendance value
            try:
                attendance = float(attendance)
                if 0 <= attendance <= 100:  # Assuming attendance is a percentage
                    # Update attendance for the course
                    StudentCourse.objects.filter(id=course_id).update(attendance=attendance)
            except ValueError:
                pass  # Invalid attendance value

    return redirect('student_detail')
@login_required
def update_marks(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        marks = request.POST.get('marks')
        if course_id and marks:
            # Validate marks value
            try:
                marks = float(marks)
                # Assuming marks can be any numeric value
                # You can add your validation logic here
                # Update marks for the course
                StudentCourse.objects.filter(id=course_id).update(course_marks=marks)
            except ValueError:
                pass  # Invalid marks value

    return redirect('student_detail')


@login_required
# teacher creates announcement 
def create_announcement(request): #done
    profile = Details.objects.get(user=request.user)
    context = {
        'username': profile.name,
    }

    if request.method == 'POST':
        message = request.POST.get('message')
        global_announcement = request.POST.get('global_announcement')

        if global_announcement:
            # Create a global announcement
            Announcement.objects.create(regno=request.user.details, message=message)
        else:
            # Get teacher's section from the database
            teacher_sections = Teacher.objects.filter(user=request.user)
            if teacher_sections.exists():
                section = teacher_sections.first().section
                # Create an announcement for the teacher's section
                Announcement.objects.create(regno=request.user.details, message=message, section=section)

    return render(request, 'create_announcement.html', context)


################################LOGOUT################################


def about_us(request):
    return render(request, 'about_us.html')

@login_required
def logout_viewsstudent(request):
    logout(request)
    return redirect('signin_student')

@login_required
def logout_viewsteacher(request):
    logout(request)
    return redirect('signin_teacher')