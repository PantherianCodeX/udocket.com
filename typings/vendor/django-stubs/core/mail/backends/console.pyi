# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

import threading
from typing import TextIO

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

class EmailBackend(BaseEmailBackend):
    stream: TextIO
    _lock: threading.RLock
    def write_message(self, message: EmailMessage) -> None: ...
