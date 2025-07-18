from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .tasks import sync_employee
import os
from logging import getLogger

logger = getLogger(__name__)


class SyncEmployeeHook(APIView):
    authentication_classes = []
    # TODO put an actual permission
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Odoo will post a JSON payload with the employee data
        on creation or update
        """
        logger.info(f"Received a payload: {request.data}")
        sync_employee.delay(request.data)
        return Response({"status":"queued"}, status=status.HTTP_200_OK)