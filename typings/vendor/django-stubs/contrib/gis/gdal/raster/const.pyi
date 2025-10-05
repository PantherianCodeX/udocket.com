# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportIncompatibleVariableOverride=false, reportUntypedClassDecorator=false, reportMissingTypeArgument=false, reportOverlappingOverload=false, reportInvalidTypeVarUse=false, reportIncompatibleMethodOverride=false, reportUntypedBaseClass=false, reportGeneralTypeIssues=false

GDAL_PIXEL_TYPES: dict[int, str]
GDAL_INTEGER_TYPES: list[int]
GDAL_TO_CTYPES: list[type | None]
GDAL_RESAMPLE_ALGORITHMS: dict[str, int]
GDAL_COLOR_TYPES: dict[int, str]
VSI_FILESYSTEM_PREFIX: str
VSI_MEM_FILESYSTEM_BASE_PATH: str
VSI_TAKE_BUFFER_OWNERSHIP: bool
VSI_DELETE_BUFFER_ON_READ: bool
