from django import forms
from django.conf.urls import include, url

from .preview import (ApplyPossibleJurorPreview, ApplyTeamManager, ApplyTeamMember, ApplyWtihRolePreview,
                      AttendeePreview, PayFeePreview)
from .views import (ApplicationsList, AssociateToTeam, DataOverview, EditAttendeeData, EditTeamMemberData,
                    FilePropertyView, ListManageableTeams, RoleApplicationsAccept, RoleApplicationsDecline,
                    RoleApplicationsList, TeamApplicationsAccept, TeamApplicationsDecline, TeamApplicationsList,
                    TeamMemberAccept, TeamMemberDecline, TeamMemberDelete, TeamMemberEdit, TeamOverview, TournamentLogo,
                    WithdrawApplication)

app_name='registration'

urlpatterns = [
#    url(r'^overview/$', Overview.as_view() ,name="overview" ),
    url(r'^list/$', ApplicationsList.as_view(), name="applications"),
    url(r'^withdraw/(?P<id>[0-9]+)/$', WithdrawApplication.as_view(), name="withdraw_application"),
    url(r'^accept/team/list$', TeamApplicationsList.as_view(), name="list_team_applications"),
    url(r'^accept/team/(?P<id>[0-9]+)/$', TeamApplicationsAccept.as_view(), name="accept_team_application"),
    url(r'^accept/team/(?P<id>[0-9]+)/decline/$', TeamApplicationsDecline.as_view(), name="decline_team_application"),
    url(r'^accept/role/list/$', RoleApplicationsList.as_view(), name="list_role_applications"),
    url(r'^accept/role/(?P<id>[0-9]+)/$', RoleApplicationsAccept.as_view(), name="accept_role_application"),
    url(r'^accept/role/(?P<id>[0-9]+)/decline/$', RoleApplicationsDecline.as_view(), name="decline_role_application"),
    url(r'^overview/$', AttendeePreview(forms.Form), name="overview"),
    url(r'^overview/edit/(?P<id>[0-9]+)/$', EditAttendeeData.as_view(), name="change_attendeeproperty"),
    url(r'^manage/list/$', ListManageableTeams.as_view(), name="manageable_teams"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/accept/(?P<id>[0-9]+)/$', TeamMemberAccept.as_view(), name="team_member_accept"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/decline/(?P<id>[0-9]+)/$', TeamMemberDecline.as_view(), name="team_member_decline"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/edit/(?P<id>[0-9]+)/$', TeamMemberEdit.as_view(), name="team_member_edit"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/data/(?P<id>[0-9]+)/$', EditTeamMemberData.as_view(), name="team_member_data"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/delete/(?P<id>[0-9]+)/$', TeamMemberDelete.as_view(), name="team_member_delete"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/invoice/$', PayFeePreview(forms.Form), name="team_payment"),
    url(r'^manage/team/(?P<s_team>[-\w]+)/$', TeamOverview.as_view(), name="team_overview"),
    url(r'^data/$', DataOverview.as_view(), name="attendeeproperty"),
    url(r'^data/file/(?P<typ>[au])/(?P<user>[0-9]+)/(?P<id>[0-9]+)/(?P<name>.*)$', FilePropertyView.as_view(), name="file_property"),
    url(r'^(?P<t_slug>[-\w]+)/role/$', ApplyWtihRolePreview(forms.Form), name="apply_participationrole"),
    url(r'^(?P<t_slug>[-\w]+)/role/(?P<role>[0-9]+)/$', ApplyWtihRolePreview(forms.Form), name="apply_preselected_participationrole"),
    url(r'^(?P<t_slug>[-\w]+)/team/$', ApplyTeamManager(forms.Form), name="apply_team"),
    url(r'^(?P<t_slug>[-\w]+)/member/$', ApplyTeamMember(forms.Form), name="apply_teammember"),
    url(r'^(?P<t_slug>[-\w]+)/member/(?P<role>[0-9]+)/$', ApplyTeamMember(forms.Form), name="apply_preselected_teammember"),
    url(r'^(?P<t_slug>[-\w]+)/member/(?P<visitor>[visitor]+)/$', ApplyTeamMember(forms.Form), name="apply_visitor_teammember"),
    url(r'^(?P<t_slug>[-\w]+)/associate/$', AssociateToTeam.as_view(), name="associate_to_team"),
    url(r'^(?P<t_slug>[-\w]+)/jurors/apply$', ApplyPossibleJurorPreview(forms.Form), name="apply_possiblejuror"),
    url(r'^(?P<t_slug>[-\w]+)/logo/$', TournamentLogo.as_view(), name="tournament_logo"),

]
