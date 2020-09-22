import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseRedirect
from django.template import TemplateSyntaxError
from django.views.generic import DetailView, UpdateView

from rdmo.core.utils import render_to_format
from rdmo.core.views import ObjectPermissionMixin, RedirectViewMixin

from ..forms import IssueMailForm, IssueSendForm
from ..models import Issue
from ..utils import get_answers_tree

logger = logging.getLogger(__name__)


class IssueDetailView(ObjectPermissionMixin, DetailView):
    model = Issue
    queryset = Issue.objects.all()
    permission_required = 'projects.view_issue_object'

    def get_context_data(self, **kwargs):
        project = self.get_object().project
        conditions = self.get_object().task.conditions.all()

        sources = []
        for condition in conditions:
            sources.append({
                'source': condition.source,
                'questions': condition.source.questions.filter(questionset__section__catalog=project.catalog),
                'values': condition.source.values.filter(project=project, snapshot=None)
            })

        kwargs['project'] = project
        kwargs['sources'] = sources
        return super().get_context_data(**kwargs)

    def get_permission_object(self):
        return self.get_object().project


class IssueUpdateView(ObjectPermissionMixin, RedirectViewMixin, UpdateView):
    model = Issue
    queryset = Issue.objects.all()
    fields = ('status', )
    permission_required = 'projects.change_issue_object'

    def get_permission_object(self):
        return self.get_object().project


class IssueSendView(ObjectPermissionMixin, RedirectViewMixin, DetailView):
    queryset = Issue.objects.all()
    permission_required = 'projects.change_issue_object'
    template_name = 'projects/issue_send.html'

    def get_permission_object(self):
        return self.get_object().project

    def get_success_url(self):
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        else:
            return self.get_object().project.get_absolute_url()

    def get_context_data(self, **kwargs):
        if 'form' not in kwargs:
            kwargs['form'] = IssueSendForm(initial={
                'subject': self.object.task.title,
                'message': self.object.task.text
            }, project=self.get_object().project)

        if 'mail_form' not in kwargs:
            kwargs['mail_form'] = IssueMailForm()

        context = super().get_context_data(**kwargs)
        context['views'] = self.get_object().project.views.all()
        context['integrations'] = self.get_object().project.integrations.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.status = Issue.ISSUE_STATUS_IN_PROGRESS
        self.object.save()

        form = IssueSendForm(request.POST, project=self.get_object().project)
        mail_form = IssueMailForm(request.POST)

        if form.is_valid():
            subject = form.cleaned_data.get('subject')
            message = form.cleaned_data.get('message')

            project = self.object.project
            snapshot = project.snapshots.filter(pk=form.cleaned_data.get('snapshot')).first()
            attachments_format = form.cleaned_data.get('attachments_format')

            attachments = []
            if form.cleaned_data.get('attachments_answers'):
                title = '{}.{}'.format(project.title, attachments_format)
                response = self.render_project_answers(project, snapshot, attachments_format)
                attachments.append((title, response.content, response['content-type']))

            for view in form.cleaned_data.get('attachments_views'):
                title = '{}.{}'.format(project.title, attachments_format)
                response = self.render_project_views(project, snapshot, view, attachments_format)
                attachments.append((title, response.content, response['content-type']))

            integration_id = request.POST.get('integration')
            if integration_id:
                # send via integration
                integration = self.get_object().project.integrations.get(pk=integration_id)
                return integration.provider.send(request, integration.options_dict, subject, message, attachments)
            else:
                if mail_form.is_valid():
                    from_email = settings.DEFAULT_FROM_EMAIL
                    to_emails = mail_form.cleaned_data.get('recipients', []) + mail_form.cleaned_data.get('recipients_input', [])
                    cc_emails = [request.user.email]
                    reply_to = [request.user.email]

                    EmailMessage(subject, message, from_email, to_emails,
                                 cc=cc_emails, reply_to=reply_to, attachments=attachments).send()
                    return HttpResponseRedirect(self.get_success_url())

        return self.render_to_response(self.get_context_data(form=form, mail_form=mail_form))

    def render_project_answers(self, project, snapshot, attachments_format):
        return render_to_format(self.request, attachments_format, project.title, 'projects/project_answers_export.html', {
            'project': project,
            'current_snapshot': snapshot,
            'format': attachments_format,
            'title': project.title,
            'answers_tree': get_answers_tree(project, snapshot)
        })

    def render_project_views(self, project, snapshot, view, attachments_format):
        try:
            rendered_view = view.render(project, snapshot)
        except TemplateSyntaxError:
            return HttpResponse()

        return render_to_format(self.request, attachments_format, project.title, 'projects/project_view_export.html', {
            'project': project,
            'current_snapshot': snapshot,
            'format': attachments_format,
            'title': project.title,
            'view': view,
            'rendered_view': rendered_view
        })
