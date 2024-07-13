from django import forms
from django.urls import path, re_path

from .forms import FileImportForm
from .list_views import feedback
from .preview import (
    ADImportPreview,
    AQImportPreview,
    OccupationImportPreview,
    OriginImportPreview,
    ProblemImportPreview,
)
from .views import fileserver, grading, prole, virtual
from .views.views import (
    ADChange,
    ADCreate,
    ADDelete,
    ADMove,
    ApiChange,
    ApiCreate,
    ApiDelete,
    ApiView,
    ApplicationQuestionView,
    AQChange,
    AQCreate,
    AQDelete,
    AQMove,
    AttendeeDataView,
    BankSettings,
    CachesView,
    DumpView,
    FeedbackSettings,
    GroupChange,
    GroupCreate,
    GroupsView,
    JOccupationChange,
    JOccupationCreate,
    JOccupationDelete,
    JOccupationMove,
    JOccupationView,
    JurySettings,
    MailTemplateSettings,
    OriginChange,
    OriginCreate,
    OriginDelete,
    OriginView,
    Overview,
    PhaseChange,
    PhaseCreate,
    PhaseDelete,
    PhaseMove,
    PhasesView,
    PIIDelete,
    ProblemChange,
    ProblemCreate,
    ProblemDelete,
    ProblemView,
    RegistrationSettings,
    TemplateSettings,
    TRoleChange,
    TRoleCreate,
    TRoleDelete,
    TRolesView,
    refreshtoken,
)

app_name = "tournament"

urlpatterns = [
    path("settings/", Overview.as_view(), name="overview"),
    path("settings/templates", TemplateSettings.as_view(), name="templates"),
    path(
        "settings/mailtemplates", MailTemplateSettings.as_view(), name="mailtemplates"
    ),
    re_path(
        r"^settings/registration", RegistrationSettings.as_view(), name="registration"
    ),
    re_path(r"^settings/feedback", FeedbackSettings.as_view(), name="feedback"),
    re_path(r"^settings/jury", JurySettings.as_view(), name="jury"),
    re_path(r"^settings/bank", BankSettings.as_view(), name="bank"),
    path("bbb/", virtual.ListServer.as_view(), name="bbbservers"),
    path("bbb/edit/<int:id>/", virtual.UpdateServer.as_view(), name="change_bbbserver"),
    path(
        "bbb/delete/<int:id>/", virtual.DeleteServer.as_view(), name="delete_bbbserver"
    ),
    path("bbb/create/", virtual.CreateServer.as_view(), name="create_bbbserver"),
    path("fileserver/", fileserver.ListServer.as_view(), name="fileservers"),
    path(
        "fileserver/edit/<int:id>/",
        fileserver.UpdateServer.as_view(),
        name="change_fileserver",
    ),
    path(
        "fileserver/delete/<int:id>/",
        fileserver.DeleteServer.as_view(),
        name="delete_fileserver",
    ),
    path(
        "fileserver/create/",
        fileserver.CreateServer.as_view(),
        name="create_fileserver",
    ),
    path("problems/", ProblemView.as_view(), name="problems"),
    path("problems/edit/<int:id>/", ProblemChange.as_view(), name="change_problem"),
    path("problems/delete/<int:id>/", ProblemDelete.as_view(), name="delete_problem"),
    path("problems/create/", ProblemCreate.as_view(), name="create_problem"),
    path(
        "problems/import/", ProblemImportPreview(FileImportForm), name="import_problems"
    ),
    path(
        "feedback/grades/", feedback.FeedbackGradeView.as_view(), name="feedbackgrades"
    ),
    path(
        "feedback/grades/edit/<int:id>/",
        feedback.FeedbackGradeChange.as_view(),
        name="change_feedbackgrade",
    ),
    path(
        "feedback/grades/delete/<int:id>/",
        feedback.FeedbackGradeDelete.as_view(),
        name="delete_feedbackgrade",
    ),
    path(
        "feedback/grades/create/",
        feedback.FeedbackGradeCreate.as_view(),
        name="create_feedbackgrade",
    ),
    path(
        "feedback/criteria/",
        feedback.ChairFeedbackCriterionView.as_view(),
        name="chairfeedbackcriteria",
    ),
    path(
        "feedback/criteria/edit/<int:id>/",
        feedback.ChairFeedbackCriterionChange.as_view(),
        name="change_chairfeedbackcriterion",
    ),
    path(
        "feedback/criteria/delete/<int:id>/",
        feedback.ChairFeedbackCriterionDelete.as_view(),
        name="delete_chairfeedbackcriterion",
    ),
    path(
        "feedback/criteria/create/",
        feedback.ChairFeedbackCriterionCreate.as_view(),
        name="create_chairfeedbackcriterion",
    ),
    path("origins/", OriginView.as_view(), name="origins"),
    path("origins/edit/<int:id>/", OriginChange.as_view(), name="change_origin"),
    path("origins/delete/<int:id>/", OriginDelete.as_view(), name="delete_origin"),
    path("origins/create/", OriginCreate.as_view(), name="create_origin"),
    path("origins/import/", OriginImportPreview(forms.Form), name="import_origins"),
    path("participation_data/scrub", PIIDelete.as_view(), name="properties_scrub"),
    path("participation_data/", AttendeeDataView.as_view(), name="properties"),
    path(
        "participation_data/edit/<int:id>/", ADChange.as_view(), name="change_property"
    ),
    path(
        "participation_data/delete/<int:id>/",
        ADDelete.as_view(),
        name="delete_property",
    ),
    path("participation_data/create/", ADCreate.as_view(), name="create_property"),
    re_path(
        r"^participation_data/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        ADMove.as_view(),
        name="move_property",
    ),
    path(
        "participation_data/import/",
        ADImportPreview(forms.Form),
        name="import_property",
    ),
    path("caches/", CachesView.as_view(), name="caches"),
    path("joccupations/", JOccupationView.as_view(), name="joccupations"),
    path(
        "joccupations/edit/<int:id>/",
        JOccupationChange.as_view(),
        name="change_joccupation",
    ),
    path(
        "joccupations/delete/<int:id>/",
        JOccupationDelete.as_view(),
        name="delete_joccupation",
    ),
    path(
        "joccupations/create/", JOccupationCreate.as_view(), name="create_joccupation"
    ),
    re_path(
        r"^joccupations/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        JOccupationMove.as_view(),
        name="move_joccupation",
    ),
    path(
        "joccupations/import/",
        OccupationImportPreview(forms.Form),
        name="import_joccupation",
    ),
    path("phases/", PhasesView.as_view(), name="phases"),
    path("phases/edit/<int:id>/", PhaseChange.as_view(), name="change_phase"),
    path("phases/delete/<int:id>/", PhaseDelete.as_view(), name="delete_phase"),
    path("phases/create/", PhaseCreate.as_view(), name="create_phase"),
    re_path(
        r"^phases/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        PhaseMove.as_view(),
        name="move_phase",
    ),
    path("rights/roles/", prole.RolesView.as_view(), name="proles"),
    path(
        "rights/roles/edit/<int:id>/", prole.RoleChange.as_view(), name="change_prole"
    ),
    path(
        "rights/roles/delete/<int:id>/", prole.RoleDelete.as_view(), name="delete_prole"
    ),
    path("rights/roles/create/", prole.RoleCreate.as_view(), name="create_prole"),
    path("rights/roles/import/", AQImportPreview(forms.Form), name="importaq_prole"),
    path("rights/api/", ApiView.as_view(), name="apiusers"),
    path("rights/api/create/", ApiCreate.as_view(), name="add_apiuser"),
    path("rights/api/<int:id>/delete/", ApiDelete.as_view(), name="delete_apiuser"),
    path("rights/api/<int:apiuser_id>/refresh/", refreshtoken, name="refresh_apiuser"),
    path("rights/api/<int:id>/change/", ApiChange.as_view(), name="change_apiuser"),
    path("grading/", grading.GradingImportPreview(FileImportForm), name="grading"),
    path("grading/delete/", grading.GradingDelete.as_view(), name="gradingdelete"),
    path("grading/json/", grading.GradingView.as_view(), name="gradingjson"),
    path(
        "application_query/<int:role_id>/",
        ApplicationQuestionView.as_view(),
        name="applicationqs",
    ),
    path(
        "application_query/<int:role_id>/edit/<int:id>/",
        AQChange.as_view(),
        name="change_applicationq",
    ),
    path(
        "application_query/<int:role_id>/delete/<int:id>/",
        AQDelete.as_view(),
        name="delete_applicationq",
    ),
    path(
        "application_query/<int:role_id>/create/",
        AQCreate.as_view(),
        name="create_applicationq",
    ),
    re_path(
        r"^application_query/(?P<role_id>\d+)/move/(?P<id>\d+)/(?P<direction>\w+)/$",
        AQMove.as_view(),
        name="move_applicationq",
    ),
    path("rights/team_roles/", TRolesView.as_view(), name="troles"),
    path(
        "rights/team_roles/edit/<int:id>/", TRoleChange.as_view(), name="change_trole"
    ),
    path(
        "rights/team_roles/delete/<int:id>/", TRoleDelete.as_view(), name="delete_trole"
    ),
    path("rights/team_roles/create/", TRoleCreate.as_view(), name="create_trole"),
    path("rights/groups/", GroupsView.as_view(), name="pgroups"),
    path("rights/groups/create/", GroupCreate.as_view(), name="create_pgroup"),
    path("rights/groups/edit/<int:id>/", GroupChange.as_view(), name="change_pgroup"),
    path("config/dump/", DumpView.as_view(), name="config_dump"),
]
