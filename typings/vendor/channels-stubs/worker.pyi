# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from asgiref.server import StatelessServer
from channels.layers import BaseChannelLayer
from channels.utils import _ChannelApplication

class Worker(StatelessServer):
    channels: list[str]
    channel_layer: BaseChannelLayer

    def __init__(
        self, application: _ChannelApplication, channels: list[str], channel_layer: BaseChannelLayer, max_applications: int = ...
    ) -> None: ...
    async def handle(self) -> None: ...
    async def listener(self, channel: str) -> None: ...
