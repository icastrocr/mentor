from django.views.generic.simple import direct_to_template
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import json

from mentorships.models import \
        JoinRequest, Project, ProjectLog
from accounts.models import Skill
from mentorships.forms import ProjectForm, ProjectLogForm

@login_required
def project_form(request, project_id=None):
    if bool(project_id):
        project = get_object_or_404(Project, pk=project_id)
        if not project.added_by == request.user:
            return redirect('login')
        edit = True
    else:
        project = None
        edit = False
    form = ProjectForm(instance=project)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)
            project.added_by = request.user
            project.save()
            form.save_m2m()
            saved = True
            if not edit:
                return redirect('project_support', project.id)
    return direct_to_template(request, 'project_form.html', locals())

@login_required
@csrf_exempt
def projects(request, project_id=None, skill_id=None):
    '''View for handling mentorship request category and detail views'''
    if request.method == 'POST':
        note = request.POST['note']
        user = request.user
        project = Project.objects.get(pk=project_id)
        join, created = JoinRequest.objects.get_or_create(
                project = project,
                added_by = user,
                note = note)
        if created:
            join.send_notification()
        resp = {'message': 'created'}
        return HttpResponse(json.dumps(resp), mimetype='json')
    if bool(project_id):
        project = get_object_or_404(Project, pk=project_id)
        return direct_to_template(
                request, 'mentorship_detail.html', locals())
    projects = Project.objects.filter(
            closed=False).select_related(
                    'sponsor_set', 'added_by')
    params = request.GET
    if params.get('my_projects'):
        skill = {'name': 'My Projects'}
        projects = projects.filter(added_by=request.user)
    if params.get('mentor'):
        skill = {'name': 'Mentoring'}
        projects = projects.filter(project_type='m')
    if params.get('learner'):
        skill = {'name': 'Learning'}
        projects = projects.filter(project_type='l')
    if bool(skill_id):
        skill = Skill.objects.get(pk=skill_id)
        projects = projects.filter(skills=skill)
    skills = Skill.objects.all()
    return direct_to_template(request, 'mentorship_category.html', locals())

@login_required
def support(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return direct_to_template(request, 'get_supporters.html', locals())

@login_required
def project_log(request, project_id):
    '''Once a mentorship is established, periodic updates
    track the progress of the mentor -> student relationship'''
    mentorship = Project.objects.get(pk=project_id)
    # TODO handle callback from notifications API
    form = ProjectLogForm()
    if request.method == 'POST':
        form = ProjectLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.added_by = request.user
            log.project = mentorship
            log.save()
            saved = True
            form = ProjectLogForm()
    if request.user == mentorship.added_by:
        role = "learning"
    else:
        role = "mentoring %s on" % mentorship.added_by.first_name
    updates = ProjectLog.objects.filter(project=mentorship)
    return direct_to_template(request, 'mentorship_log.html', locals())
