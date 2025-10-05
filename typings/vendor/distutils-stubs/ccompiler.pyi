# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from setuptools._distutils.ccompiler import *
from setuptools._distutils.ccompiler import CCompiler as CCompiler

__all__ = [
    "CompileError",
    "LinkError",
    "gen_lib_options",
    "gen_preprocess_options",
    "get_default_compiler",
    "new_compiler",
    "show_compilers",
]
