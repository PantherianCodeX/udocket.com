# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from _typeshed import StrOrBytesPath
from typing import Any, Final

LIST_OF_FILE_NAMES: Final[list[str]]

def get_extension(srcfilename, modname, sources=(), **kwds): ...
def compile(tmpdir, ext, compiler_verbose: int = 0, debug=None): ...
def maybe_relative_path(path: StrOrBytesPath) -> StrOrBytesPath | str: ...

int_or_long = int

def flatten(x: int | str | list[Any] | tuple[Any] | dict[Any, Any]) -> str: ...
