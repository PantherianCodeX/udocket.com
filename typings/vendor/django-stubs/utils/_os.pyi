# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

import os
from pathlib import Path
from typing import TypeAlias

_PathCompatible: TypeAlias = str | os.PathLike[str]

def safe_join(base: _PathCompatible, *paths: _PathCompatible) -> str: ...
def symlinks_supported() -> bool: ...
def to_path(value: Path | str) -> Path: ...
