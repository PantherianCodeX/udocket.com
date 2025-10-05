# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from django.db.migrations.operations.base import Operation

class MigrationOptimizer:
    def optimize(self, operations: list[Operation], app_label: str | None) -> list[Operation]: ...
    def optimize_inner(self, operations: list[Operation], app_label: str | None) -> list[Operation]: ...
