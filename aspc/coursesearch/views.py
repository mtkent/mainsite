from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from aspc.coursesearch.models import Course, Department, Meeting, Schedule
from aspc.coursesearch.forms import SearchForm
import re, json
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.generic import list_detail
from django.shortcuts import get_object_or_404, render
from django.conf import settings
import shlex, subprocess

def search(request):
    if request.method == "GET":
        if len(request.GET) > 0:
            form = SearchForm(request.GET)
            if form.is_valid():
                results_set = form.build_queryset()
                paginator = Paginator(results_set, per_page=20, orphans=10)
                GET_data = request.GET.copy()
                
                try:
                    page = int(request.GET.get('page', '1'))
                    if GET_data.get('page', False):
                        del GET_data['page']
                except ValueError:
                    page = 1
                
                try:
                    results = paginator.page(page)
                except (EmptyPage, InvalidPage):
                    results = paginator.page(paginator.num_pages)
                
                return render(request, 'coursesearch/search.html', {'form': form, 'results': results, 'path': ''.join([request.path, '?', GET_data.urlencode()]),})
            else:
                return render(request, 'coursesearch/search.html', {'form': form,})
        else:
            form = SearchForm()
            return render(request, 'coursesearch/search.html', {'form': form,})

def schedule(request):
    if request.method == "GET":
        if len(request.GET) > 0:
            form = SearchForm(request.GET)
            if form.is_valid():
                results_set = form.build_queryset()
                paginator = Paginator(results_set, per_page=10, orphans=5)
                GET_data = request.GET.copy()
                
                try:
                    page = int(request.GET.get('page', '1'))
                    if GET_data.get('page', False):
                        del GET_data['page']
                except ValueError:
                    page = 1
                
                try:
                    results = paginator.page(page)
                except (EmptyPage, InvalidPage):
                    results = paginator.page(paginator.num_pages)
                
                for course in results.object_list:
                    if course.id in request.session.get('schedule_courses', []):
                        course.added = True
                
                return render(request, 'coursesearch/schedule.html', {'form': form, 'results': results, 'path': ''.join([request.path, '?', GET_data.urlencode()]),})
            else:
                return render(request, 'coursesearch/schedule.html', {'form': form,})
        else:
            form = SearchForm()
            return render(request, 'coursesearch/schedule.html', {'form': form,})

def load_from_session(request):
    all_events = []
    valid_courses = set()
    schedule_courses = request.session.get('schedule_courses', set())
    for course in Course.objects.filter(id__in=schedule_courses):
        all_events.append(course.json())
        valid_courses.add(course.pk)
    if schedule_courses - valid_courses:
        for invalid in (schedule_courses - valid_courses):
            request.session['schedule_courses'].remove(invalid)
        request.session.modified = True
    return HttpResponse(content=json.dumps(all_events, cls=DjangoJSONEncoder), mimetype='application/json')

def clear_schedule(request):
    courses_info = []
    if request.session.get('schedule_courses', False):
        schedule_courses = request.session['schedule_courses']
        del request.session['schedule_courses']
        for course in Course.objects.filter(id__in=schedule_courses):
            courses_info.append(course.json())
    return HttpResponse(content=json.dumps(courses_info, cls=DjangoJSONEncoder), mimetype='application/json')

def share_schedule(request):
    schedule_courses = Course.objects.filter(id__in=request.session.get('schedule_courses',[]))
    if request.method == "POST":
        s = Schedule()
        s.save()
        for course in schedule_courses:
            s.courses.add(course)
        s.save()
        
        return render(request, 'coursesearch/share_schedule.html', {'saved': True, 'schedule': s, 'schedule_courses': s.courses.all(),})
    else:
        return render(request, 'coursesearch/share_schedule.html', {'schedule_courses': schedule_courses,})

def view_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id)
    if request.method == "POST":
        request.session['schedule_courses'] = set([c.id for c in schedule.courses.all()])
        return HttpResponseRedirect(reverse('aspc.coursesearch.views.schedule'))
    else:
        return render(request, 'coursesearch/schedule_frozen.html',{'schedule': schedule,})

def view_minimal_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id)
    return render(request, 'coursesearch/minimal_schedule_frozen.html', {'schedule': schedule,})

def course_detail(request, dept, course_code):
    department = get_object_or_404(Department, code=dept)
    kwargs = {'queryset': Course.objects.filter(primary_department=department),
             'slug': course_code,
             'slug_field': 'code_slug',}
    return list_detail.object_detail(request, **kwargs)


def schedule_course_add(request, course_code):
    course = get_object_or_404(Course, code_slug=course_code)
    if request.session.get('schedule_courses'):
        if not (course.id in request.session['schedule_courses']):
            request.session['schedule_courses'].add(course.id)
            request.session.modified = True
    else:
        request.session['schedule_courses'] = set([course.id,])
    return HttpResponse(content=json.dumps(course.json(), cls=DjangoJSONEncoder), mimetype='application/json')


def schedule_course_remove(request, course_code):
    removed_ids = []
    course = get_object_or_404(Course, code_slug=course_code)
    if request.session.get('schedule_courses'):
        if (course.id in request.session['schedule_courses']):
            request.session['schedule_courses'].remove(course.id)
            request.session.modified = True
            
            course_data = course.json()
            for e in course_data['events']:
                removed_ids.append(e['id'])
    
    return HttpResponse(content=json.dumps(removed_ids, cls=DjangoJSONEncoder), mimetype='application/json')