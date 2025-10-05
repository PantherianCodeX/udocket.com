# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

import itertools

flatten = itertools.chain.from_iterable

class Installer:
    nspkg_ext: str
    def install_namespaces(self) -> None: ...
    def uninstall_namespaces(self) -> None: ...

class DevelopInstaller(Installer): ...
