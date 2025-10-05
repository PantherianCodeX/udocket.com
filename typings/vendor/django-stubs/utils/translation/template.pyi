# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

from re import Pattern

TRANSLATOR_COMMENT_MARK: str

dot_re: Pattern[str]

def blankout(src: str, char: str) -> str: ...

context_re: Pattern[str]
inline_re: Pattern[str]
block_re: Pattern[str]
endblock_re: Pattern[str]
plural_re: Pattern[str]
constant_re: Pattern[str]

def templatize(src: str, origin: str | None = None) -> str: ...
