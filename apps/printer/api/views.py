from rest_framework import views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from ..models import Pdf
from .renderer import PdfFileRenderer
from .serializers import PdfSerializer


class PrinterAppPermission(BasePermission):

    def has_permission(self, request, view):
        print("check perm for ", request.user)
        return bool(request.user and request.user.has_perm("tournament.app_printer"))


class PdfViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PdfSerializer

    permission_classes = (PrinterAppPermission,)

    def get_queryset(self):
        return Pdf.objects.filter(tournament=self.request.user.profile.tournament)

    @action(detail=True, renderer_classes=(PdfFileRenderer,))
    def download(self, request, pk=None):
        pdf = Pdf.objects.get(tournament=self.request.user.profile.tournament, pk=pk)
        return Response(
            pdf.file,
            headers={"Content-Disposition": 'filename="file.pdf"'},
            content_type="application/pdf",
        )
