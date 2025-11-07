# Typing Automation Status

Last updated: 2025-10-05T15:52:04.935222+00:00

_Note_: Vendored third-party stubs are no longer tracked in git. Run `python scripts/typing/vendor_stubs.py` (or `--force` to regenerate populated directories) before capturing fresh snapshots so `typings/vendor/` exists locally.

## Pyright Snapshot

Command: `pyright --stats`

```
Loading configuration file at /home/user/Code/uDocket/udocket.com/pyrightconfig.json
No include entries specified; assuming /home/user/Code/uDocket/udocket.com
Found 1390 source files
pyright 1.1.392
/home/user/Code/uDocket/udocket.com/apps/platform/accounts/apps.py
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/apps.py:10:23 - error: Import "signals" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:3:25 - error: Import "Optional" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:8:6 - warning: Stub file not found for "mozilla_django_oidc.auth" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:30:9 - warning: Type of "sub" is partially unknown
    Type of "sub" is "LiteralString | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:30:15 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:30:16 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:31:9 - warning: Type of "email" is partially unknown
    Type of "email" is "LiteralString | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:31:17 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:31:18 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:32:9 - warning: Type of "preferred" is partially unknown
    Type of "preferred" is "LiteralString | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:32:21 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:32:22 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:43:9 - warning: Type of "email" is partially unknown
    Type of "email" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:43:17 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:43:18 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:44:9 - warning: Type of "preferred" is partially unknown
    Type of "preferred" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:44:21 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:44:22 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:46:20 - warning: Return type, "LiteralString | Unknown", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:48:20 - warning: Return type, "LiteralString | Unknown", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:49:9 - warning: Type of "sub" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:49:15 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:51:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:52:16 - warning: Type of "get_username" is partially unknown
    Type of "get_username" is "(claims: Unknown) -> (Any | str)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:52:37 - warning: Argument type is unknown
    Argument corresponds to parameter "claims" in function "get_username" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:55:9 - warning: Type of "issuer" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:55:18 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:57:36 - warning: Type of "rstrip" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:58:80 - warning: Argument type is unknown
    Argument corresponds to parameter "args" in function "warning" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:63:19 - warning: Type of "get_settings" is partially unknown
    Type of "get_settings" is "(attr: Unknown, *args: Unknown) -> Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:64:46 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:65:82 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:65:82 - warning: Argument type is unknown
    Argument corresponds to parameter "args" in function "warning" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:69:9 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:69:16 - warning: Type of "create_user" is partially unknown
    Type of "create_user" is "(claims: Unknown) -> Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:86:13 - warning: Type of "groups" is partially unknown
    Type of "groups" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:87:74 - warning: Type of "g" is partially unknown
    Type of "g" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:95:13 - warning: Type of "groups" is partially unknown
    Type of "groups" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:98:17 - warning: Type of "g" is partially unknown
    Type of "g" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:125:25 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:125:25 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:125:33 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:125:33 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:177:22 - warning: Type of "email" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:177:27 - warning: Cannot access attribute "email" for class "_UserModel"
    Attribute "email" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:178:18 - warning: Cannot assign to attribute "email" for class "_UserModel"
    Attribute "email" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/auth.py:182:18 - warning: Cannot assign to attribute "display_name" for class "_UserModel"
    Attribute "display_name" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:12:30 - error: Expected type arguments for generic class "UserCreationForm" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:17:16 - warning: Type of "Meta" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:17:16 - error: Base class type is unknown, obscuring type of derived class (reportUntypedBaseClass)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:17:33 - warning: Cannot access attribute "Meta" for class "type[UserCreationForm[_UserType@UserCreationForm]]"
    Attribute "Meta" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:23:37 - warning: Cannot assign to attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:31:9 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:42:13 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/forms.py:51:16 - warning: Return type is unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:11:35 - warning: Type of parameter "sender" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:11:35 - error: Type annotation is missing for parameter "sender" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:11:79 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:11:79 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:12:8 - warning: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:12:17 - warning: Cannot access attribute "user_id" for class "OrganizationMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:17:37 - warning: Type of parameter "sender" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:17:37 - error: Type annotation is missing for parameter "sender" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:17:81 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:17:81 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:18:8 - warning: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/accounts/signals.py:18:17 - warning: Cannot access attribute "user_id" for class "OrganizationMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:18:9 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:18:52 - warning: Type of parameter "queryset" is partially unknown
    Parameter type is "QuerySet[Unknown, Unknown]" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:18:62 - error: Expected type arguments for generic class "QuerySet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:18:75 - error: Expected type arguments for generic class "QuerySet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:20:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:24:9 - warning: Type of "scoped" is partially unknown
    Type of "scoped" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:24:18 - warning: Type of "scope_queryset" is partially unknown
    Type of "scope_queryset" is "(request: HttpRequest, queryset: QuerySet[Unknown, Unknown]) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:24:47 - warning: Argument type is unknown
    Argument corresponds to parameter "queryset" in function "scope_queryset" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:25:16 - warning: Type of "_filter_active_org" is partially unknown
    Type of "_filter_active_org" is "(request: HttpRequest, queryset: QuerySet[Unknown, Unknown]) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:25:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:28:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:28:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:33:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:33:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:37:16 - warning: Type of "_object_in_scope" is partially unknown
    Type of "_object_in_scope" is "(request: HttpRequest, obj: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:40:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:40:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:44:16 - warning: Type of "_object_in_scope" is partially unknown
    Type of "_object_in_scope" is "(request: HttpRequest, obj: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:44:47 - warning: Argument type is unknown
    Argument corresponds to parameter "obj" in function "_object_in_scope" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:47:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:47:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:51:16 - warning: Type of "_object_in_scope" is partially unknown
    Type of "_object_in_scope" is "(request: HttpRequest, obj: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:51:47 - warning: Argument type is unknown
    Argument corresponds to parameter "obj" in function "_object_in_scope" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:54:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:54:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:62:54 - warning: Type of parameter "obj" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:62:54 - error: Type annotation is missing for parameter "obj" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:9 - warning: Type of "queryset" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:20 - warning: Type of "model" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:20 - warning: Type of "_default_manager" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:20 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:25 - warning: Cannot access attribute "model" for class "TenantScopedAdminMixin*"
    Attribute "model" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:66 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:65:77 - warning: Argument type is unknown
    Argument corresponds to parameter "default" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:66:9 - warning: Type of "queryset" is partially unknown
    Type of "queryset" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:66:20 - warning: Type of "scope_queryset" is partially unknown
    Type of "scope_queryset" is "(request: HttpRequest, queryset: QuerySet[Unknown, Unknown]) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:66:49 - warning: Argument type is unknown
    Argument corresponds to parameter "queryset" in function "scope_queryset" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:67:9 - warning: Type of "queryset" is partially unknown
    Type of "queryset" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:67:20 - warning: Type of "_filter_active_org" is partially unknown
    Type of "_filter_active_org" is "(request: HttpRequest, queryset: QuerySet[Unknown, Unknown]) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:70:9 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:70:56 - warning: Type of parameter "queryset" is partially unknown
    Parameter type is "QuerySet[Unknown, Unknown]" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:70:66 - error: Expected type arguments for generic class "QuerySet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:70:79 - error: Expected type arguments for generic class "QuerySet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:73:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:75:24 - warning: Type of "model" is partially unknown
    Type of "model" is "type[Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:75:24 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "hasattr"
    Argument type is "type[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:76:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:79:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/admin/__init__.py:80:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/apps/platform/artifacts/admin.py
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/admin.py:2:6 - warning: Stub file not found for "simple_history.admin" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/admin.py:24:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/admin.py:24:32 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_artifacts"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/artifacts/apps.py
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/apps.py:11:27 - error: Import "signals" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/apps/platform/artifacts/serializers.py
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/serializers.py:8:30 - error: Expected type arguments for generic class "ModelSerializer" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/serializers.py:9:11 - error: "Meta" overrides symbol of same name in class "ModelSerializer"
    "apps.platform.artifacts.serializers.CaseArtifactSerializer.Meta" is not assignable to "rest_framework.serializers.ModelSerializer.Meta"
    Type "type[apps.platform.artifacts.serializers.CaseArtifactSerializer.Meta]" is not assignable to type "type[rest_framework.serializers.ModelSerializer.Meta]" (reportIncompatibleVariableOverride)
/home/user/Code/uDocket/udocket.com/apps/platform/artifacts/signals.py
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/signals.py:11:5 - error: Function "_queue_guardian_review" is not accessed (reportUnusedFunction)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/signals.py:11:28 - warning: Type of parameter "sender" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/signals.py:11:28 - error: Type annotation is missing for parameter "sender" (reportMissingParameterType)
/home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:18:23 - error: Expected type arguments for generic class "ReadOnlyModelViewSet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:19:5 - warning: Type of "queryset" is partially unknown
    Type of "queryset" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:24:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:27:13 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:29:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:29:32 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_artifacts"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:34:13 - warning: Type of "obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:35:41 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:35:41 - warning: Argument type is unknown
    Argument corresponds to parameter "case_id" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:35:86 - warning: Argument type is partially unknown
    Argument corresponds to parameter "data" in function "emit"
    Argument type is "dict[str, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:35:102 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:35:118 - warning: Type of "type" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:24 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:24 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:34 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:34 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:42 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:50:42 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:51:9 - warning: Type of "artifact" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:52:9 - warning: Type of "path_value" is partially unknown
    Type of "path_value" is "Unknown | Literal['']" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:52:22 - warning: Type of "path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:53:25 - warning: Argument type is partially unknown
    Argument corresponds to parameter "args" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:65:17 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:66:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:66:25 - warning: Argument type is unknown
    Argument corresponds to parameter "case_id" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:68:22 - warning: Argument type is partially unknown
    Argument corresponds to parameter "data" in function "emit"
    Argument type is "dict[str, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:68:38 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/artifacts/views.py:68:59 - warning: Type of "type" is unknown (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:9:9 - warning: Type of "statements" is partially unknown
    Type of "statements" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:9:21 - error: Expected type arguments for generic class "list" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:11:28 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:11:28 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:16:35 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:16:35 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:16:44 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:16:44 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:17:30 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:20:20 - warning: Type of "method" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:20:20 - warning: Type of "lower" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:20:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:22:47 - warning: Type of parameter "statement_actions" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:22:47 - error: Type annotation is missing for parameter "statement_actions" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:27:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:36 - warning: Type of parameter "condition" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:36 - error: Type annotation is missing for parameter "condition" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:47 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:47 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:56 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:56 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:62 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:29:62 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:32:36 - warning: Argument type is unknown
    Argument corresponds to parameter "name" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:37:29 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:37:29 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:37:38 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:37:38 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:39:17 - warning: Type of "stmt" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:39:25 - warning: Type of "statements" is partially unknown
    Type of "statements" is "list[Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:40:17 - warning: Type of "stmt_actions" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:40:32 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:43:24 - warning: Type of "_actions_match" is partially unknown
    Type of "_actions_match" is "(action: str, statement_actions: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:43:52 - warning: Argument type is unknown
    Argument corresponds to parameter "statement_actions" in function "_actions_match" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:45:24 - warning: Type of "_check_condition" is partially unknown
    Type of "_check_condition" is "(condition: Unknown, request: Unknown, view: Unknown, action: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:45:46 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:45:46 - warning: Argument type is unknown
    Argument corresponds to parameter "condition" in function "_check_condition" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:45:69 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_check_condition" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:45:78 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_check_condition" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:47:17 - warning: Type of "effect" is partially unknown
    Type of "effect" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:47:26 - warning: Type of "lower" is partially unknown
    Type of "lower" is "Unknown | Overload[() -> LiteralString, () -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:47:27 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:54:34 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:54:43 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:55:16 - warning: Type of "_is_open" is partially unknown
    Type of "_is_open" is "(request: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:57:22 - warning: Type of "_resolve_action" is partially unknown
    Type of "_resolve_action" is "(request: Unknown, view: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:58:20 - warning: Type of "_evaluate" is partially unknown
    Type of "_evaluate" is "(request: Unknown, view: Unknown, action: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:60:41 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:60:50 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:60:56 - error: Type annotation is missing for parameter "obj" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:61:16 - warning: Type of "_is_open" is partially unknown
    Type of "_is_open" is "(request: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:63:22 - warning: Type of "_resolve_action" is partially unknown
    Type of "_resolve_action" is "(request: Unknown, view: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:66:24 - warning: Type of "_evaluate" is partially unknown
    Type of "_evaluate" is "(request: Unknown, view: Unknown, action: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:80:32 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:80:32 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:80:41 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:80:41 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:81:23 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:97:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:104:26 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:111:26 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:117:19 - warning: Type of "__class__" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:117:19 - warning: Type of "__name__" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:117:19 - warning: Type of "lower" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:117:19 - warning: Type of "startswith" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:122:32 - warning: Type of parameter "user" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:122:32 - error: Type annotation is missing for parameter "user" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:131:24 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:131:24 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:131:33 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:131:33 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:132:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:135:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:135:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:135:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:30 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:30 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:39 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:39 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:45 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:143:45 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:144:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:147:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:147:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:147:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:31 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:31 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:40 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:40 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:46 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:152:46 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:153:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:156:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:156:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:156:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:159:12 - warning: Type of "_has_cap" is partially unknown
    Type of "_has_cap" is "(request: Unknown, view: Unknown, capability: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:159:26 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:159:35 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:161:16 - warning: Type of "_membership_role" is partially unknown
    Type of "_membership_role" is "(user: Unknown, case_id: str | None) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:31 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:31 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:40 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:40 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:46 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:168:46 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:169:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:172:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:172:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:172:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:175:12 - warning: Type of "_has_cap" is partially unknown
    Type of "_has_cap" is "(request: Unknown, view: Unknown, capability: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:175:26 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:175:35 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:177:16 - warning: Type of "_membership_role" is partially unknown
    Type of "_membership_role" is "(user: Unknown, case_id: str | None) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:30 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:30 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:39 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:39 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:45 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:185:45 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:186:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:189:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:189:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:189:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:193:12 - warning: Type of "_has_cap" is partially unknown
    Type of "_has_cap" is "(request: Unknown, view: Unknown, capability: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:193:26 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:193:35 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:199:16 - warning: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:199:21 - warning: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:199:41 - warning: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:199:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:199:46 - warning: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:38 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:38 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:47 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:47 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:53 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:205:53 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:206:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:209:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:209:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:209:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:212:16 - warning: Type of "_has_cap" is partially unknown
    Type of "_has_cap" is "(request: Unknown, view: Unknown, capability: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:212:30 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:212:39 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:34 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:34 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:43 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:43 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:49 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:214:49 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:215:19 - warning: Type of "_resolve_case_id" is partially unknown
    Type of "_resolve_case_id" is "(request: Unknown, view: Unknown) -> (str | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:215:41 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:215:50 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_resolve_case_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:217:20 - warning: Type of "is_case_member" is partially unknown
    Type of "is_case_member" is "(request: Unknown, view: Unknown, action: Unknown) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:217:40 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "is_case_member" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:217:49 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "is_case_member" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:217:55 - warning: Argument type is unknown
    Argument corresponds to parameter "action" in function "is_case_member" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:218:16 - warning: Type of "_has_cap" is partially unknown
    Type of "_has_cap" is "(request: Unknown, view: Unknown, capability: str) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:218:30 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:218:39 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "_has_cap" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:31 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:31 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:40 - warning: Type of parameter "view" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:40 - error: Type annotation is missing for parameter "view" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:46 - warning: Type of parameter "action" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:220:46 - error: Type annotation is missing for parameter "action" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:221:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:227:42 - warning: Argument to class must be a base class (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:227:42 - error: Base class type is unknown, obscuring type of derived class (reportUntypedBaseClass)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:236:41 - warning: Argument to class must be a base class (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:236:41 - error: Base class type is unknown, obscuring type of derived class (reportUntypedBaseClass)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:248:46 - warning: Argument to class must be a base class (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/access_policies.py:248:46 - error: Base class type is unknown, obscuring type of derived class (reportUntypedBaseClass)
/home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:8:57 - error: Import "OrganizationMembership" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:22:21 - error: Expected type arguments for generic class "ModelForm" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:27:25 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:27:25 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:27:33 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:27:33 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:9 - warning: Type of "__init__" is partially unknown
    Type of "__init__" is "(data: Mapping[str, Any] | None = None, files: MultiValueDict[str, UploadedFile] | None = None, auto_id: bool | str = "id_%s", prefix: str | None = None, initial: MutableMapping[str, Any] | None = None, error_class: type[ErrorList] = ..., label_suffix: str | None = None, empty_permitted: bool = False, instance: Unknown | None = None, use_required_attribute: bool | None = None, renderer: BaseRenderer | None = None) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "files" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "auto_id" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "prefix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "initial" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "error_class" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "label_suffix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "empty_permitted" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "use_required_attribute" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:28:27 - warning: Argument type is unknown
    Argument corresponds to parameter "renderer" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:30:12 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:30:30 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:30:30 - warning: Type of "pk" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:31:13 - warning: Type of "org" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:31:19 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:31:19 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:42:32 - warning: Cannot assign to attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:45:33 - error: Expected type arguments for generic class "ModelForm" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:69:25 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:69:25 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:69:33 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:69:33 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:9 - warning: Type of "__init__" is partially unknown
    Type of "__init__" is "(data: Mapping[str, Any] | None = None, files: MultiValueDict[str, UploadedFile] | None = None, auto_id: bool | str = "id_%s", prefix: str | None = None, initial: MutableMapping[str, Any] | None = None, error_class: type[ErrorList] = ..., label_suffix: str | None = None, empty_permitted: bool = False, instance: Unknown | None = None, use_required_attribute: bool | None = None, renderer: BaseRenderer | None = None) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "files" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "auto_id" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "prefix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "initial" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "error_class" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "label_suffix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "empty_permitted" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "use_required_attribute" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:70:27 - warning: Argument type is unknown
    Argument corresponds to parameter "renderer" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:71:37 - warning: Cannot assign to attribute "choices" for class "Field"
    Attribute "choices" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:72:12 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:72:30 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:72:30 - warning: Type of "pk" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:73:13 - warning: Type of "existing" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:73:24 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:73:24 - warning: Type of "capabilities" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:73:24 - warning: Type of "values_list" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:74:56 - warning: Argument type is unknown
    Argument corresponds to parameter "iterable" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:77:9 - warning: Type of "preset" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:84:36 - warning: Argument type is unknown
    Argument corresponds to parameter "preset" in function "sync_capabilities" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:85:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:88:9 - warning: Type of "selected" is partially unknown
    Type of "selected" is "Any | set[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:88:60 - warning: Argument type is partially unknown
    Argument corresponds to parameter "default" in function "getattr"
    Argument type is "set[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:89:9 - warning: Type of "current" is partially unknown
    Type of "current" is "set[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:89:23 - warning: Type of "capabilities" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:89:23 - warning: Type of "values_list" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:89:23 - warning: Argument type is unknown
    Argument corresponds to parameter "iterable" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:89:30 - warning: Cannot access attribute "capabilities" for class "PermissionPreset"
    Attribute "capabilities" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:90:13 - warning: Type of "cap" is partially unknown
    Type of "cap" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:91:13 - warning: Type of "capabilities" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:91:13 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:91:13 - warning: Type of "delete" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:91:20 - warning: Cannot access attribute "capabilities" for class "PermissionPreset"
    Attribute "capabilities" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:92:13 - warning: Type of "cap" is partially unknown
    Type of "cap" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:103:32 - warning: Type of "instance" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:103:32 - warning: Argument type is unknown
    Argument corresponds to parameter "preset" in function "sync_capabilities" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:106:26 - error: Expected type arguments for generic class "ModelForm" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:113:25 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:113:25 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:113:33 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:113:33 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:9 - warning: Type of "__init__" is partially unknown
    Type of "__init__" is "(data: Mapping[str, Any] | None = None, files: MultiValueDict[str, UploadedFile] | None = None, auto_id: bool | str = "id_%s", prefix: str | None = None, initial: MutableMapping[str, Any] | None = None, error_class: type[ErrorList] = ..., label_suffix: str | None = None, empty_permitted: bool = False, instance: Unknown | None = None, use_required_attribute: bool | None = None, renderer: BaseRenderer | None = None) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "files" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "auto_id" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "prefix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "initial" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "error_class" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "label_suffix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "empty_permitted" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "use_required_attribute" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:114:27 - warning: Argument type is unknown
    Argument corresponds to parameter "renderer" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:115:35 - warning: Cannot assign to attribute "choices" for class "Field"
    Attribute "choices" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:118:28 - error: Expected type arguments for generic class "TabularInline" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:125:17 - error: Expected type arguments for generic class "ModelAdmin" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:133:5 - warning: Type of "inlines" is partially unknown
    Type of "inlines" is "list[type[InlineModelAdmin[Unknown, Unknown]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:147:13 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:149:62 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:149:62 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "role_capabilities" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:149:64 - warning: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:150:13 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:157:9 - warning: Type of "ctx" is partially unknown
    Type of "ctx" is "dict[str, Any | str | list[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:158:91 - warning: Argument type is partially unknown
    Argument corresponds to parameter "context" in function "__init__"
    Argument type is "dict[str, Any | str | list[Unknown]]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:161:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:164:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:165:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:165:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:166:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:168:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:171:52 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:171:65 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:173:16 - warning: Type of "formfield_for_foreignkey" is partially unknown
    Type of "formfield_for_foreignkey" is "(db_field: ForeignKey[Unknown, Unknown], request: HttpRequest, **kwargs: Any) -> (ModelChoiceField[Unknown] | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:173:16 - warning: Return type, "ModelChoiceField[Unknown] | None", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:176:9 - warning: Type of "form_class" is partially unknown
    Type of "form_class" is "type[ModelForm[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:176:22 - warning: Type of "get_form" is partially unknown
    Type of "get_form" is "(request: HttpRequest, obj: Unknown | None = ..., change: bool = ..., **kwargs: Any) -> type[ModelForm[Unknown]]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:176:39 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "get_form" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:176:55 - warning: Argument type is unknown
    Argument corresponds to parameter "change" in function "get_form" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:177:49 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "get_active_admin_org_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:178:55 - warning: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:181:26 - error: Instance methods should take a "self" parameter (reportSelfClsParameterName)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:181:39 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:181:39 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:181:47 - warning: Type of parameter "inner_kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:181:47 - error: Type annotation is missing for parameter "inner_kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:182:17 - warning: Type of "initial" is partially unknown
    Type of "initial" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:182:32 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: str, /) -> (Unknown | None), (key: str, default: Unknown, /) -> Unknown, (key: str, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:182:32 - warning: Argument type is unknown
    Argument corresponds to parameter "map" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:184:21 - warning: Type of "setdefault" is partially unknown
    Type of "setdefault" is "Overload[(key: Unknown, default: None = None, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:17 - warning: Type of "__init__" is partially unknown
    Type of "__init__" is "(data: Mapping[str, Any] | None = None, files: MultiValueDict[str, UploadedFile] | None = None, auto_id: bool | str = "id_%s", prefix: str | None = None, initial: MutableMapping[str, Any] | None = None, error_class: type[ErrorList] = ..., label_suffix: str | None = None, empty_permitted: bool = False, instance: Unknown | None = None, use_required_attribute: bool | None = None, renderer: BaseRenderer | None = None) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "files" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "auto_id" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "prefix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "initial" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "error_class" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "label_suffix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "empty_permitted" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "use_required_attribute" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:186:35 - warning: Argument type is unknown
    Argument corresponds to parameter "renderer" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:187:24 - warning: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:187:24 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:188:55 - warning: Cannot assign to attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:189:17 - warning: Type of "presets_qs" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:189:30 - warning: Type of "queryset" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:189:59 - warning: Cannot access attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:191:21 - warning: Type of "presets_qs" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:191:34 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:194:26 - warning: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:194:26 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:196:21 - warning: Type of "presets_qs" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:196:34 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:199:46 - warning: Cannot assign to attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:199:57 - warning: Type of "order_by" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:205:29 - error: Expected type arguments for generic class "ModelAdmin" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:213:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:216:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:217:12 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:217:25 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:218:20 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:220:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:223:52 - warning: Type of "is_superuser" is partially unknown
    Type of "is_superuser" is "Unknown | Literal[False]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:223:65 - warning: Cannot access attribute "is_superuser" for class "_User"
    Attribute "is_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:225:16 - warning: Type of "formfield_for_foreignkey" is partially unknown
    Type of "formfield_for_foreignkey" is "(db_field: ForeignKey[Unknown, Unknown], request: HttpRequest, **kwargs: Any) -> (ModelChoiceField[Unknown] | None)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:225:16 - warning: Return type, "ModelChoiceField[Unknown] | None", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:228:9 - warning: Type of "save_model" is partially unknown
    Type of "save_model" is "(request: HttpRequest, obj: Unknown, form: Any, change: Any) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:228:37 - warning: Argument type is unknown
    Argument corresponds to parameter "obj" in function "save_model" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:230:36 - warning: Argument type is unknown
    Argument corresponds to parameter "preset" in function "sync_capabilities" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:233:9 - warning: Type of "form_class" is partially unknown
    Type of "form_class" is "type[ModelForm[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:233:22 - warning: Type of "get_form" is partially unknown
    Type of "get_form" is "(request: HttpRequest, obj: Unknown | None = ..., change: bool = ..., **kwargs: Any) -> type[ModelForm[Unknown]]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:233:39 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "get_form" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:233:55 - warning: Argument type is unknown
    Argument corresponds to parameter "change" in function "get_form" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:234:49 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "get_active_admin_org_id" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:235:55 - warning: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:238:26 - error: Instance methods should take a "self" parameter (reportSelfClsParameterName)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:238:39 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:238:39 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:238:47 - warning: Type of parameter "inner_kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:238:47 - error: Type annotation is missing for parameter "inner_kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:239:17 - warning: Type of "initial" is partially unknown
    Type of "initial" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:239:32 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: str, /) -> (Unknown | None), (key: str, default: Unknown, /) -> Unknown, (key: str, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:239:32 - warning: Argument type is unknown
    Argument corresponds to parameter "map" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:241:21 - warning: Type of "setdefault" is partially unknown
    Type of "setdefault" is "Overload[(key: Unknown, default: None = None, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:17 - warning: Type of "__init__" is partially unknown
    Type of "__init__" is "(data: Mapping[str, Any] | None = None, files: MultiValueDict[str, UploadedFile] | None = None, auto_id: bool | str = "id_%s", prefix: str | None = None, initial: MutableMapping[str, Any] | None = None, error_class: type[ErrorList] = ..., label_suffix: str | None = None, empty_permitted: bool = False, instance: Unknown | None = None, use_required_attribute: bool | None = None, renderer: BaseRenderer | None = None) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "files" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "auto_id" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "prefix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "initial" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "error_class" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "label_suffix" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "empty_permitted" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "use_required_attribute" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:243:35 - warning: Argument type is unknown
    Argument corresponds to parameter "renderer" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:244:24 - warning: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:244:24 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/admin.py:245:55 - warning: Cannot assign to attribute "queryset" for class "Field"
    Attribute "queryset" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:16:17 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:16:17 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:17:20 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:25:5 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:25:20 - warning: Type of parameter "queryset" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:25:20 - error: Type annotation is missing for parameter "queryset" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:25:30 - warning: Type of parameter "user" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:25:30 - error: Type annotation is missing for parameter "user" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:27:46 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:28:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:31:16 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:31:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:34:12 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:34:12 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:39:21 - warning: Type of parameter "_request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:39:21 - error: Type annotation is missing for parameter "_request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:53:18 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:53:18 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:54:25 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_auth_guard" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:58:20 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:9 - warning: Type of "caps" is partially unknown
    Type of "caps" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:23 - warning: Type of "capability" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:23 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "sorted"
    Argument type is "Generator[Unknown, None, None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:41 - warning: Type of "pc" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:47 - warning: Type of "capabilities" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:47 - warning: Type of "all" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:68:54 - warning: Cannot access attribute "capabilities" for class "PermissionPreset"
    Attribute "capabilities" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:69:9 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:75:33 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:75:40 - warning: Cannot access attribute "organization_id" for class "PermissionPreset"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:85:16 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:85:16 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:86:25 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_auth_guard" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:90:20 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:96:61 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:96:61 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "role_capabilities" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:96:66 - warning: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:97:9 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:102:33 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/api.py:102:38 - warning: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:9:5 - error: Import "PermissionPreset" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:146:32 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:146:48 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:147:13 - warning: Type of "org_id" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:147:22 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:147:38 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/capabilities.py:148:81 - warning: Argument type is partially unknown
    Argument corresponds to parameter "organization_id" in function "role_capabilities"
    Argument type is "Unknown | None" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:4:20 - error: Import "Any" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:32:9 - warning: Type of "data" is partially unknown
    Type of "data" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:33:9 - warning: Type of "presets" is partially unknown
    Type of "presets" is "Unknown | Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:33:19 - warning: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:34:9 - warning: Type of "bindings" is partially unknown
    Type of "bindings" is "Unknown | Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:34:20 - warning: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:37:17 - warning: Type of "p" is partially unknown
    Type of "p" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:39:17 - warning: Type of "org_slug" is partially unknown
    Type of "org_slug" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:39:28 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:44:67 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:44:84 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:46:17 - warning: Type of "preset_name" is partially unknown
    Type of "preset_name" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:46:31 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:46:48 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:53:40 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:58:42 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:60:43 - warning: Cannot assign to attribute "organization" for class "PermissionPreset"
    Type "Organization | None" is not assignable to type "Organization"
      "None" is not assignable to "Organization" (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:63:33 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:63:33 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "Unknown | list[_T@set] | Any" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:68:20 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:76:17 - warning: Type of "role_name" is partially unknown
    Type of "role_name" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:76:28 - warning: Type of "preset_names" is partially unknown
    Type of "preset_names" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:76:44 - warning: Type of "items" is partially unknown
    Type of "items" is "Unknown | Any | (() -> dict_items[Unknown, Unknown])" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:83:24 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/authorization/management/commands/import_presets.py:83:29 - warning: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py:2:6 - warning: Stub file not found for "simple_history.admin" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py:8:28 - error: Expected type arguments for generic class "TabularInline" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py:23:5 - warning: Type of "inlines" is partially unknown
    Type of "inlines" is "list[type[InlineModelAdmin[Unknown, Unknown]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py:26:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/admin.py:26:28 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_cases"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/cases/apps.py
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/apps.py:10:23 - error: Import "signals" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/apps/platform/cases/serializers.py
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/serializers.py:8:22 - error: Expected type arguments for generic class "ModelSerializer" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/serializers.py:9:5 - warning: Type of "organization" is partially unknown
    Type of "organization" is "RelatedField[Unknown, Unknown, Any] | ManyRelatedField" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/serializers.py:11:11 - error: "Meta" overrides symbol of same name in class "ModelSerializer"
    "apps.platform.cases.serializers.CaseSerializer.Meta" is not assignable to "rest_framework.serializers.ModelSerializer.Meta"
    Type "type[apps.platform.cases.serializers.CaseSerializer.Meta]" is not assignable to type "type[rest_framework.serializers.ModelSerializer.Meta]" (reportIncompatibleVariableOverride)
/home/user/Code/uDocket/udocket.com/apps/platform/cases/signals.py
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/signals.py:30:22 - warning: Type of parameter "sender" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/signals.py:30:22 - error: Type annotation is missing for parameter "sender" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/signals.py:30:73 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/signals.py:30:73 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
/home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:6:40 - error: Import "AllowAny" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:24:19 - error: Expected type arguments for generic class "ModelViewSet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:25:5 - warning: Type of "queryset" is partially unknown
    Type of "queryset" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:30:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:32:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:32:28 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_cases"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:35:28 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:35:28 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:35:37 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:35:37 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:40:9 - warning: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:41:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:46:13 - warning: Type of "org_id" is partially unknown
    Type of "org_id" is "Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:46:22 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:46:29 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:46:54 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:46:56 - warning: Cannot access attribute "case_id" for class "CaseMembership"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:50:68 - warning: Argument type is partially unknown
    Argument corresponds to parameter "organization_id" in function "role_capabilities"
    Argument type is "Unknown | None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:51:38 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:51:38 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:56:13 - warning: Type of "obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:57:45 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:57:45 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:86:28 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:86:28 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:86:37 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:86:37 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:87:9 - warning: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:90:21 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:98:27 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:98:27 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:98:36 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:98:36 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:99:9 - warning: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:102:21 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/cases/views.py:105:34 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/config/__init__.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/__init__.py:1:28 - error: Import "celery_app" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/apps/platform/config/asgi.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/asgi.py:14:46 - warning: Type of "websocket_urlpatterns" is partially unknown
    Type of "websocket_urlpatterns" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/asgi.py:27:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "routes" in function "__init__"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:12:14 - error: Expected 0 positional arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:13:1 - warning: Type of "config_from_object" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:13:5 - warning: Cannot access attribute "config_from_object" for class "Celery"
    Attribute "config_from_object" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:14:1 - warning: Type of "autodiscover_tasks" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:14:5 - warning: Cannot access attribute "autodiscover_tasks" for class "Celery"
    Attribute "autodiscover_tasks" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:19:1 - warning: Type of "conf" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:19:5 - warning: Cannot access attribute "conf" for class "Celery"
    Attribute "conf" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:20:1 - warning: Type of "conf" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:20:5 - warning: Cannot access attribute "conf" for class "Celery"
    Attribute "conf" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:21:1 - warning: Type of "conf" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:21:5 - warning: Cannot access attribute "conf" for class "Celery"
    Attribute "conf" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:24:2 - warning: Type of "task" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:24:2 - error: Untyped function decorator obscures type of function; ignoring decorator (reportUntypedFunctionDecorator)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:24:6 - warning: Cannot access attribute "task" for class "Celery"
    Attribute "task" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:25:10 - warning: Type of parameter "self" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/celery.py:25:10 - error: Type annotation is missing for parameter "self" (reportMissingParameterType)
/home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:5:1 - warning: Type of "websocket_urlpatterns" is partially unknown
    Type of "websocket_urlpatterns" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:6:29 - warning: Type of "as_asgi" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:6:29 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "path" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:6:57 - warning: Cannot access attribute "as_asgi" for class "type[JobStreamConsumer]"
    Attribute "as_asgi" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:7:35 - warning: Type of "as_asgi" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:7:35 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "path" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:7:57 - warning: Cannot access attribute "as_asgi" for class "type[JobConsumer]"
    Attribute "as_asgi" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:8:37 - warning: Type of "as_asgi" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:8:37 - warning: Argument type is unknown
    Argument corresponds to parameter "view" in function "path" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/routing.py:8:60 - warning: Cannot access attribute "as_asgi" for class "type[CaseConsumer]"
    Attribute "as_asgi" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/config/settings/base.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/base.py:6:8 - warning: Stub file not found for "environ" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/base.py:154:5 - error: "CHANNEL_LAYERS" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/base.py:178:1 - warning: Type of "AUTHENTICATION_BACKENDS" is partially unknown
    Type of "AUTHENTICATION_BACKENDS" is "tuple[Literal['django.contrib.auth.backends.ModelBackend'], Literal['guardian.backends.ObjectPermissionBackend'], Literal['apps.platform.accounts.auth.KeycloakOIDCBackend']] | tuple[Literal['django.contrib.auth.backends.ModelBackend'], Literal['guardian.backends.ObjectPermissionBackend'], *tuple[Unknown, ...]]" (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/apps/platform/config/settings/dev.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/dev.py:3:1 - error: "DEBUG" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
/home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:3:1 - error: "DEBUG" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:5:1 - error: "SECURE_SSL_REDIRECT" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:6:1 - error: "SESSION_COOKIE_SECURE" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:7:1 - error: "CSRF_COOKIE_SECURE" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:8:1 - error: "SECURE_HSTS_SECONDS" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:11:1 - error: "CHANNEL_LAYERS" is constant (because it is uppercase) and cannot be redefined (reportConstantRedefinition)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:11:1 - warning: Type of "CHANNEL_LAYERS" is partially unknown
    Type of "CHANNEL_LAYERS" is "dict[str, dict[str, str | dict[str, list[Unknown]]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:15:23 - warning: Type of "url" is partially unknown
    Type of "url" is "(var: Unknown, default: NoValue = NOTSET) -> Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/config/settings/prod.py:15:52 - warning: Argument of type "Literal['redis://localhost:6379/0']" cannot be assigned to parameter "default" of type "NoValue" in function "url"
    "Literal['redis://localhost:6379/0']" is not assignable to "NoValue" (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/admin.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/admin.py:9:40 - error: Expected type arguments for generic class "ModelAdmin" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/admin.py:18:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/admin.py:18:27 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_jobs"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:3:22 - error: Import "datetime" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:9:22 - warning: Type of parameter "dt" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:9:22 - error: Type annotation is missing for parameter "dt" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:13:16 - warning: Type of "isoformat" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:13:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:15:16 - warning: Type of "isoformat" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:15:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:23:27 - warning: Type of "created_by_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:23:27 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:23:32 - warning: Cannot access attribute "created_by_id" for class "JobNote"
    Attribute "created_by_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:23:50 - warning: Type of "created_by_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/notes.py:23:55 - warning: Cannot access attribute "created_by_id" for class "JobNote"
    Attribute "created_by_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:28:30 - error: Expected type arguments for generic class "Serializer" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:39 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:55 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:55 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:73:64 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:141:28 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:141:28 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:141:37 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:212:27 - error: Expected type arguments for generic class "ModelSerializer" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:213:11 - error: "Meta" overrides symbol of same name in class "ModelSerializer"
    "apps.platform.jobs.serializers.JobCreateSerializer.Meta" is not assignable to "rest_framework.serializers.ModelSerializer.Meta"
    Type "type[apps.platform.jobs.serializers.JobCreateSerializer.Meta]" is not assignable to type "type[rest_framework.serializers.ModelSerializer.Meta]" (reportIncompatibleVariableOverride)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:224:21 - error: Expected type arguments for generic class "ModelSerializer" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:227:11 - error: "Meta" overrides symbol of same name in class "ModelSerializer"
    "apps.platform.jobs.serializers.JobSerializer.Meta" is not assignable to "rest_framework.serializers.ModelSerializer.Meta"
    Type "type[apps.platform.jobs.serializers.JobSerializer.Meta]" is not assignable to type "type[rest_framework.serializers.ModelSerializer.Meta]" (reportIncompatibleVariableOverride)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:258:16 - warning: Type of "to_representation" is partially unknown
    Type of "to_representation" is "(instance: Unknown) -> dict[str, Any]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:258:42 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "to_representation" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/serializers.py:269:31 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:18:32 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:18:32 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:18:36 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:22:32 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:22:32 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:22:36 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:74:46 - error: Unnecessary isinstance call; "str" is always an instance of "str" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:87:20 - error: Unnecessary isinstance call; "AudioMetadata | dict[Unknown, Unknown]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:88:35 - error: Type "AudioMetadata | dict[Unknown, Unknown]" is not assignable to declared type "Dict[str, Any]"
    Type "AudioMetadata | dict[Unknown, Unknown]" is not assignable to type "Dict[str, Any]"
      "AudioMetadata" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:178:9 - error: Operator "+=" not supported for types "int | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:181:13 - error: Operator "+=" not supported for types "int | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:183:13 - error: Operator "+=" not supported for types "int | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:185:13 - error: Operator "+=" not supported for types "int | Unknown | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:187:13 - error: Operator "+=" not supported for types "int | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:189:13 - error: Operator "+=" not supported for types "int | None" and "Literal[1]"
    Operator "+" not supported for types "None" and "Literal[1]" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:193:36 - error: Operator ">" not supported for types "datetime" and "int | datetime"
    Operator ">" not supported for types "datetime" and "int" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/telemetry.py:194:17 - warning: Argument of type "datetime" cannot be assigned to parameter "value" of type "int | None" in function "__setitem__"
    Type "datetime" is not assignable to type "int | None"
      "datetime" is not assignable to "int"
      "datetime" is not assignable to "None" (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/utils.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/utils.py:19:50 - error: Unnecessary isinstance call; "str" is always an instance of "str" (reportUnnecessaryIsInstance)
/home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:4:8 - error: Import "hashlib" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:13:40 - error: Import "AllowAny" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:44:40 - error: Import "Case" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:122:18 - error: Expected type arguments for generic class "ModelViewSet" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:123:5 - warning: Type of "queryset" is partially unknown
    Type of "queryset" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:133:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:135:16 - warning: Return type, "QuerySet[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:135:27 - warning: Argument type is partially unknown
    Argument corresponds to parameter "qs" in function "scope_jobs"
    Argument type is "QuerySet[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:145:9 - error: Variable "audio_input_value" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:148:24 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:149:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:149:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:149:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:161:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:161:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:161:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:165:25 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:168:22 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:168:22 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:168:31 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:168:31 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:174:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:175:9 - warning: Type of "payload" is partially unknown
    Type of "payload" is "dict[str, str | Unknown | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:176:23 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:176:23 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:177:23 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:178:32 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:179:33 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:180:32 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:181:28 - warning: Type of "finished_at" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:182:30 - warning: Type of "review_status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:183:31 - warning: Type of "review_comment" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:184:28 - warning: Type of "reviewed_at" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:185:28 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:185:45 - warning: Type of "reviewed_by" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:185:45 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_user_label" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:186:39 - warning: Type of "review_activity_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:186:39 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:186:66 - warning: Type of "review_activity_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:191:21 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:191:21 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:191:30 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:191:30 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:192:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:193:16 - warning: Type of "_can_review" is partially unknown
    Type of "_can_review" is "(request: Unknown, job: Job) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:193:33 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:193:42 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:196:9 - warning: Type of "incoming" is partially unknown
    Type of "incoming" is "Unknown | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:196:20 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:197:9 - warning: Type of "notes_value" is partially unknown
    Type of "notes_value" is "Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:197:23 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:209:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:211:27 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:212:9 - error: Variable "note" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:236:21 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:236:21 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:237:17 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:237:17 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "append_job_log" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:238:21 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:238:21 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:245:17 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:245:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:247:20 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:248:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:248:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:255:27 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:255:27 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:262:9 - warning: Type of "ids_param" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:262:21 - warning: Type of "query_params" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:262:21 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:267:13 - warning: Type of "raw_part" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:267:25 - warning: Type of "split" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:268:13 - warning: Type of "part" is partially unknown
    Type of "part" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:268:20 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:272:42 - warning: Argument type is partially unknown
    Argument corresponds to parameter "hex" in function "__init__"
    Argument type is "LiteralString | Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:279:9 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:280:9 - warning: Type of "case_id_param" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:280:25 - warning: Type of "query_params" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:280:25 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:283:27 - warning: Argument type is unknown
    Argument corresponds to parameter "hex" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:286:13 - warning: Type of "qs" is partially unknown
    Type of "qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:289:13 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:292:31 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:292:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:293:31 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:294:40 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:295:41 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:296:40 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:297:36 - warning: Type of "finished_at" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:298:38 - warning: Type of "review_status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:299:39 - warning: Type of "review_comment" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:300:36 - warning: Type of "reviewed_at" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:301:36 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:301:53 - warning: Type of "reviewed_by" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:301:53 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_user_label" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:302:47 - warning: Type of "review_activity_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:302:47 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:302:74 - warning: Type of "review_activity_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:308:27 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:308:27 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:309:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:314:12 - warning: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:314:21 - warning: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:314:57 - warning: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:314:57 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:314:66 - warning: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:316:41 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:316:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:316:45 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:319:21 - warning: Type of parameter "user" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:319:21 - error: Type annotation is missing for parameter "user" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:322:16 - warning: Return type, "Any | str | Unknown", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:323:21 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:324:16 - warning: Type of "get_full_name" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:325:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:326:24 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:327:20 - warning: Type of "pk" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:327:20 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:330:9 - warning: Return type, "dict[Unknown, Unknown]", is partially unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:330:83 - warning: Type of parameter "reviewer" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:330:83 - error: Type annotation is missing for parameter "reviewer" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:330:96 - error: Expected type arguments for generic class "dict" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:331:16 - warning: Return type, "dict[Unknown, Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:340:32 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:340:49 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_user_label" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:345:51 - warning: Type of parameter "reviewer" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:345:51 - error: Type annotation is missing for parameter "reviewer" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:349:53 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:349:53 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:349:57 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:367:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:367:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:367:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:370:22 - warning: Type of "_artifact_defaults" is partially unknown
    Type of "_artifact_defaults" is "(job: Job, checksum: str, activity_id: UUID, reviewer: Unknown) -> dict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:370:22 - warning: Argument type is partially unknown
    Argument corresponds to parameter "defaults" in function "update_or_create"
    Argument type is "dict[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:370:61 - warning: Argument of type "UUID | None" cannot be assigned to parameter "activity_id" of type "UUID" in function "_artifact_defaults"
    Type "UUID | None" is not assignable to type "UUID"
      "None" is not assignable to "UUID" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:370:85 - warning: Argument type is unknown
    Argument corresponds to parameter "reviewer" in function "_artifact_defaults" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:374:23 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:374:23 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:374:32 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:374:32 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:375:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:376:16 - warning: Type of "_can_review" is partially unknown
    Type of "_can_review" is "(request: Unknown, job: Job) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:376:33 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:376:42 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:378:12 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:380:16 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:383:9 - warning: Type of "comment" is partially unknown
    Type of "comment" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:383:19 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:383:20 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:383:20 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:384:9 - warning: Type of "activity_id" is partially unknown
    Type of "activity_id" is "Unknown | UUID" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:384:23 - warning: Type of "review_activity_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:385:28 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:391:9 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:394:13 - warning: Type of "_ensure_approval_artifact" is partially unknown
    Type of "_ensure_approval_artifact" is "(job: Job, reviewer: Unknown) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:394:44 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_ensure_approval_artifact" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:20 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:41 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:97 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:97 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:398:127 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | UUID" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:399:9 - warning: Type of "response_payload" is partially unknown
    Type of "response_payload" is "dict[str, str | Status | ReviewStatus | datetime | Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:400:27 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:400:27 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:404:28 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:405:31 - warning: Type of "review_comment" is partially unknown
    Type of "review_comment" is "LiteralString | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:406:39 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | UUID" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:409:17 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:409:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:412:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:412:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:416:28 - warning: Type of "review_comment" is partially unknown
    Type of "review_comment" is "LiteralString | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:417:36 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | UUID" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:422:22 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:422:22 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:422:31 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:422:31 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:423:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:424:16 - warning: Type of "_can_review" is partially unknown
    Type of "_can_review" is "(request: Unknown, job: Job) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:424:33 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:424:42 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_can_review" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:427:9 - warning: Type of "comment" is partially unknown
    Type of "comment" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:427:19 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:427:20 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:427:20 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:429:28 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:435:9 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:438:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:438:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:439:24 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:439:24 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:443:20 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:443:41 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:443:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:443:97 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:443:97 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:444:9 - warning: Type of "response_payload" is partially unknown
    Type of "response_payload" is "dict[str, str | Unknown | ReviewStatus | datetime]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:445:27 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:445:27 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:446:23 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:449:28 - warning: Type of "_user_label" is partially unknown
    Type of "_user_label" is "(user: Unknown) -> str" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:450:31 - warning: Type of "review_comment" is partially unknown
    Type of "review_comment" is "LiteralString | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:454:17 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:454:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:456:20 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:457:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:457:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:461:28 - warning: Type of "review_comment" is partially unknown
    Type of "review_comment" is "LiteralString | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:467:25 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:467:25 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:467:34 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:467:34 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:470:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:471:45 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:472:25 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:475:24 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:475:24 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:475:33 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:475:33 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:476:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:477:16 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:479:20 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:479:41 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:479:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:479:108 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:479:108 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:480:34 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:480:34 - warning: Argument type is unknown
    Argument corresponds to parameter "file" in function "open" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:480:74 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:483:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:483:30 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:483:30 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:483:39 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:483:39 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:484:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:485:25 - warning: Type of "query_params" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:485:25 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:485:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:486:34 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:486:90 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:489:49 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:489:49 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:489:76 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:499:45 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:501:46 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:509:28 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:509:28 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:509:42 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:509:58 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:509:58 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:514:67 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:514:67 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:526:34 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:546:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:547:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:547:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:549:33 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:549:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:551:86 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:555:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:555:27 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:555:27 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:555:36 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:555:36 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:556:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:558:22 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:558:22 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:558:22 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:559:21 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:559:21 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:559:21 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['current']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:565:35 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "job_telemetry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:566:34 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:600:32 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:605:84 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:608:50 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:611:46 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:644:29 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:644:29 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:644:38 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:644:38 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:645:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:646:31 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:674:29 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:674:29 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:674:51 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:674:86 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:674:86 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:708:17 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:710:17 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:712:43 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "job_telemetry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:716:30 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:716:30 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:716:39 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:716:39 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:717:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:719:12 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:721:31 - warning: Type of "finished_at" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:722:33 - warning: Type of "error_message" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:723:13 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:725:21 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:725:21 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:726:25 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:727:21 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:727:21 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:733:25 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:733:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:736:33 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:736:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:739:73 - warning: Argument type is partially unknown
    Argument corresponds to parameter "extra" in function "exception"
    Argument type is "dict[str, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:739:84 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:741:45 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:742:25 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:745:22 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:745:22 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:745:31 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:745:31 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:746:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:747:12 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:749:23 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:749:23 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:750:22 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:750:22 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:750:54 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:751:26 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:751:26 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:760:17 - warning: Type of "value" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:778:13 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:780:50 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_cancel_azure_transcription" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:795:17 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:813:17 - warning: Type of "control" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:813:17 - warning: Type of "revoke" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:813:28 - warning: Cannot access attribute "control" for class "Celery"
    Attribute "control" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:822:9 - warning: Type of "save" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:824:46 - warning: Argument type is unknown
    Argument corresponds to parameter "job" in function "_cancel_azure_transcription" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:838:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:848:30 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:849:29 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:851:78 - warning: Type of "upload_progress" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:854:23 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:854:23 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:854:32 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:854:32 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:855:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:856:12 - warning: Type of "status" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:858:16 - warning: Type of "audio_input" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:862:22 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:863:30 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:864:29 - warning: Type of "audio_input" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:865:22 - warning: Type of "mode" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:866:29 - warning: Type of "diarization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:867:26 - warning: Type of "language" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:870:24 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:871:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:871:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:871:33 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:877:35 - warning: Type of "query_params" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:877:35 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:880:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:881:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:881:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:883:33 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:883:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:885:102 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:885:102 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:885:110 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:896:13 - warning: Type of "inspect_obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:896:27 - warning: Type of "control" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:896:27 - warning: Type of "inspect" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:896:38 - warning: Cannot access attribute "control" for class "Celery"
    Attribute "control" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:902:36 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:918:17 - warning: Type of "result" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:918:26 - warning: Type of "AsyncResult" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:918:37 - warning: Cannot access attribute "AsyncResult" for class "Celery"
    Attribute "AsyncResult" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:919:20 - warning: Type of "state" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:926:20 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:926:20 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:926:29 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:926:29 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:927:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:928:23 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:928:23 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:929:40 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:929:40 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:929:40 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:929:71 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:932:20 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:932:93 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:932:93 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:933:58 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:40 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:40 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:44 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:54 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:54 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:941:63 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:953:36 - warning: Argument of type "int | float | str | dict[str, JSONValue] | list[JSONValue] | Literal[True]" cannot be assigned to parameter "url" of type "str | bytes" in function "delete"
    Type "int | float | str | dict[str, JSONValue] | list[JSONValue] | Literal[True]" is not assignable to type "str | bytes"
      Type "float" is not assignable to type "str | bytes"
        "float" is not assignable to "str"
        "float" is not assignable to "bytes" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:960:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:960:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:960:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:975:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:975:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:975:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:984:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:984:31 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:984:31 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:984:40 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:984:40 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:985:9 - warning: Type of "source_job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:986:9 - warning: Type of "payload" is partially unknown
    Type of "payload" is "Unknown | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:986:19 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:986:43 - warning: Argument type is unknown
    Argument corresponds to parameter "obj" in function "hasattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:989:13 - warning: Type of "config_value" is partially unknown
    Type of "config_value" is "Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:989:28 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:993:9 - warning: Type of "transcript_path" is partially unknown
    Type of "transcript_path" is "Unknown | Literal['']" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:993:27 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:996:29 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:996:29 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:997:28 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:997:28 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1003:74 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1003:74 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1006:29 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1006:29 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1013:9 - warning: Type of "organization_obj" is partially unknown
    Type of "organization_obj" is "Unknown | Any | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1013:28 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1013:63 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1013:63 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1016:17 - warning: Type of "organization_obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1016:36 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1016:36 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1024:26 - warning: Type of "id" is partially unknown
    Type of "id" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1024:26 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Any" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1036:30 - error: Type "LLMConfigurationPayload | None" is not assignable to declared type "Dict[str, Any] | None"
    Type "LLMConfigurationPayload | None" is not assignable to type "Dict[str, Any] | None"
      Type "LLMConfigurationPayload" is not assignable to type "Dict[str, Any] | None"
        "LLMConfigurationPayload" is not assignable to "Dict[str, Any]"
        "LLMConfigurationPayload" is not assignable to "None" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1042:30 - error: Type "LLMConfigurationPayload | None" is not assignable to declared type "Dict[str, Any] | None"
    Type "LLMConfigurationPayload | None" is not assignable to type "Dict[str, Any] | None"
      Type "LLMConfigurationPayload" is not assignable to type "Dict[str, Any] | None"
        "LLMConfigurationPayload" is not assignable to "Dict[str, Any]"
        "LLMConfigurationPayload" is not assignable to "None" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1083:17 - warning: Type of "merged_metadata" is partially unknown
    Type of "merged_metadata" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1083:55 - warning: Expected mapping for dictionary unpack operator (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1089:30 - warning: Argument type is partially unknown
    Argument corresponds to parameter "metadata" in function "evaluate_provider_setup"
    Argument type is "dict[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1110:22 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1112:29 - warning: Type of "audio_input" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1113:22 - warning: Type of "mode" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1115:26 - warning: Type of "language" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1117:28 - warning: Type of "duration_s" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1120:30 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1120:30 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1120:51 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1120:51 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1126:34 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1126:34 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1134:17 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1134:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1135:13 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1135:13 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1140:17 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1140:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1141:13 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1141:13 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "append_job_log" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1143:54 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1150:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1150:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1150:37 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1153:21 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1154:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1154:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1154:37 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1157:31 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1157:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1160:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1161:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1161:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1165:38 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1165:38 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1175:31 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1175:31 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1175:40 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1175:40 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1176:9 - warning: Type of "summary_job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1177:9 - warning: Type of "payload" is partially unknown
    Type of "payload" is "Unknown | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1177:19 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1177:43 - warning: Argument type is unknown
    Argument corresponds to parameter "obj" in function "hasattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1180:13 - warning: Type of "config_value" is partially unknown
    Type of "config_value" is "Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1180:28 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1184:9 - warning: Type of "organization_obj" is partially unknown
    Type of "organization_obj" is "Unknown | Any | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1184:28 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1184:64 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1184:64 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1187:17 - warning: Type of "organization_obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1187:36 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1187:36 - warning: Type of "organization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1195:22 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1197:29 - warning: Type of "audio_input" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1198:22 - warning: Type of "mode" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1199:29 - warning: Type of "diarization" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1200:26 - warning: Type of "language" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1201:33 - warning: Type of "transcript_path" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1202:28 - warning: Type of "duration_s" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1205:30 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1205:30 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1205:52 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1205:52 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1209:90 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1209:90 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1210:35 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1210:35 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1216:17 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1216:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1217:13 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1217:13 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1222:17 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1222:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1223:13 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1223:13 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "append_job_log" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1225:48 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1232:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1232:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1232:33 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1235:21 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1236:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1236:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1236:33 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1238:32 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1238:32 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1242:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1243:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1243:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1247:39 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1247:39 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1255:33 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1255:33 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1255:42 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1255:42 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1256:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1257:9 - warning: Type of "kind" is partially unknown
    Type of "kind" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1257:16 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1257:17 - warning: Type of "query_params" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1257:17 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1261:50 - warning: Argument type is partially unknown
    Argument corresponds to parameter "key" in function "get"
    Argument type is "LiteralString | Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1265:23 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1265:23 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1266:9 - warning: Type of "org_id" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1266:18 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1266:41 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1266:41 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1267:39 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "read_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1267:51 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1267:51 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1272:46 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "case_paths" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1278:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1281:18 - warning: Argument type is partially unknown
    Argument corresponds to parameter "data" in function "emit"
    Argument type is "dict[str, str | Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1281:33 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1281:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1287:9 - warning: Return type, "Response | Unknown", is partially unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1287:28 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1287:28 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1287:37 - warning: Type of parameter "pk" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1287:37 - error: Type annotation is missing for parameter "pk" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1288:9 - warning: Type of "job" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1290:53 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1290:53 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1290:78 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1290:78 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1296:9 - warning: Type of "new_title" is partially unknown
    Type of "new_title" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1296:21 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1296:22 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1296:22 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1302:29 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1302:29 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1307:13 - warning: Type of "telemetry" is partially unknown
    Type of "telemetry" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1307:25 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1307:48 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1308:13 - warning: Type of "context" is partially unknown
    Type of "context" is "dict[str, Unknown | ReturnDict[Unknown, Unknown] | dict[str, str] | str | bool | list[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1309:25 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1313:52 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1313:52 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1319:20 - error: "render" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1319:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:28 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:28 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:42 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:42 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "append_job_log" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:67 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1323:67 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1324:82 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1324:82 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1325:9 - warning: Type of "telemetry" is partially unknown
    Type of "telemetry" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1325:21 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1325:44 - warning: Argument type is unknown
    Argument corresponds to parameter "instance" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1326:9 - warning: Type of "context" is partially unknown
    Type of "context" is "dict[str, Unknown | ReturnDict[Unknown, Unknown] | dict[str, str | Unknown] | str | bool | list[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1327:21 - warning: Type of "case" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1335:16 - error: "render" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1335:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1338:22 - warning: Type of parameter "request" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1338:22 - error: Type annotation is missing for parameter "request" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1349:44 - error: Import "ValidationError" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1350:49 - error: Import "MultiValueDictKeyError" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1354:9 - warning: Type of "case_id" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1354:19 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1354:19 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1358:9 - warning: Type of "mode" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1358:16 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1358:16 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1359:27 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1359:27 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1359:27 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1360:9 - warning: Type of "language" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1360:20 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1360:20 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1364:9 - warning: Type of "file_obj" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1364:20 - warning: Type of "FILES" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1364:20 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1365:9 - warning: Type of "audio_url" is partially unknown
    Type of "audio_url" is "LiteralString | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1365:21 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Overload[(chars: LiteralString | None = None, /) -> LiteralString, (chars: str | None = None, /) -> str]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1365:22 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1365:22 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1373:45 - warning: Argument type is unknown
    Argument corresponds to parameter "case_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1375:49 - warning: Type of "name" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1378:25 - warning: Type of "chunk" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1378:34 - warning: Type of "chunks" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1379:35 - warning: Argument type is unknown
    Argument corresponds to parameter "buffer" in function "write" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1385:35 - warning: Type of "data" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1385:35 - warning: Type of "get" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1385:35 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1388:24 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1389:25 - warning: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1389:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1389:29 - warning: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1400:13 - warning: Argument type is unknown
    Argument corresponds to parameter "request" in function "emit" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1401:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1403:18 - warning: Argument type is partially unknown
    Argument corresponds to parameter "data" in function "emit"
    Argument type is "dict[str, str | Unknown | Mode | bool]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1403:69 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/jobs/views.py:1405:25 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:38:5 - error: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:38:14 - error: Type of parameter "mapping" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:38:23 - error: "Any" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:38:41 - error: "Any" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:40:16 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:40:16 - error: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:41:22 - error: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/templatetags/ui_display.py:48:24 - error: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:117:5 - error: Type of "artifacts_list" is partially unknown
    Type of "artifacts_list" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:118:27 - error: Argument type is partially unknown
    Argument corresponds to parameter "artifacts" in function "_artifact_rows"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:136:5 - error: Type of "type_counts" is partially unknown
    Type of "type_counts" is "Counter[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:136:27 - error: Type of "type" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:136:27 - error: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "Generator[Unknown, None, None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:136:45 - error: Type of "artifact" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:176:49 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:187:26 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:192:26 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:197:26 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:204:5 - error: Type of "context" is partially unknown
    Type of "context" is "dict[str, dict[str, str | list[dict[str, str | int]] | list[dict[str, str | List[Dict[str, Any]] | Tuple[Dict[str, Any], ...] | list[Any] | tuple[dict[str, str]] | bool | dict[str, int | bool] | int | list[int] | list[str]]]] | List[Dict[str, Any]] | Counter[Unknown] | dict[str, int | bool]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/artifacts.py:211:64 - error: Argument type is partially unknown
    Argument corresponds to parameter "context" in function "render"
    Argument type is "dict[str, dict[str, str | list[dict[str, str | int]] | list[dict[str, str | List[Dict[str, Any]] | Tuple[Dict[str, Any], ...] | list[Any] | tuple[dict[str, str]] | bool | dict[str, int | bool] | int | list[int] | list[str]]]] | List[Dict[str, Any]] | Counter[Unknown] | dict[str, int | bool]]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:32:51 - error: Type of parameter "organization" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:32:51 - error: Type annotation is missing for parameter "organization" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:54:45 - error: Type of parameter "organization" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:54:45 - error: Type annotation is missing for parameter "organization" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:55:50 - error: Argument type is unknown
    Argument corresponds to parameter "organization" in function "_organization_artifacts" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:64:5 - error: Type of parameter "organization" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:64:5 - error: Type annotation is missing for parameter "organization" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:103:9 - error: Type of "metadata_payload" is partially unknown
    Type of "metadata_payload" is "Unknown | Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:103:28 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:104:12 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:134:17 - error: Argument of type "None" cannot be assigned to parameter "case_id" of type "str" in function "table_config"
    "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:140:48 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:213:49 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/audit.py:213:75 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/contexts.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/contexts.py:188:23 - error: Argument of type "object" cannot be assigned to parameter "job_row_total" of type "int" in function "build_tool_panels"
    "object" is not assignable to "int" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/contexts.py:422:59 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:25:5 - error: Type of "cases" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:25:13 - error: Type of "for_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:25:13 - error: Type of "order_by" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:25:22 - error: Cannot access attribute "for_user" for class "QuerySet[Case, Case]"
    Attribute "for_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:27:9 - error: Type of "cases" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:27:17 - error: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:29:9 - error: Type of "cases" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:29:17 - error: Type of "none" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:33:13 - error: Type of "context" is partially unknown
    Type of "context" is "dict[str, Unknown | str | list[tuple[str, str | _StrPromise]] | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:42:72 - error: Argument type is partially unknown
    Argument corresponds to parameter "context" in function "render"
    Argument type is "dict[str, Unknown | str | list[tuple[str, str | _StrPromise]] | None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:101:5 - error: Type of "context" is partially unknown
    Type of "context" is "dict[str, Unknown | Organization | list[tuple[str, str | _StrPromise]] | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/dashboard.py:109:64 - error: Argument type is partially unknown
    Argument corresponds to parameter "context" in function "render"
    Argument type is "dict[str, Unknown | Organization | list[tuple[str, str | _StrPromise]] | None]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:158:5 - error: Type of "case_values" is partially unknown
    Type of "case_values" is "set[str] | set[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:203:5 - error: Type of "rows" is partially unknown
    Type of "rows" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:216:30 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:323:36 - error: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "sorted"
    Argument type is "set[str] | set[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:384:35 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:384:46 - error: Type of "value" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:391:14 - error: Argument type is partially unknown
    Argument corresponds to parameter "rows" in function "__init__"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/job_tables.py:393:20 - error: Argument of type "dict[str, int | bool]" cannot be assigned to parameter "pagination" of type "Dict[str, object]" in function "__init__"
    "dict[str, int | bool]" is not assignable to "Dict[str, object]"
      Type parameter "_VT@dict" is invariant, but "int | bool" is not the same as "object"
      Consider switching from "dict" to "Mapping" which is covariant in the value type (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:124:32 - error: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:124:32 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:124:40 - error: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:135:21 - error: Argument of type "None" cannot be assigned to parameter "case_id" of type "str" in function "table_config"
    "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:138:25 - error: Argument of type "object" cannot be assigned to parameter "total_count" of type "int | None" in function "table_config"
    Type "object" is not assignable to type "int | None"
      "object" is not assignable to "int"
      "object" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs.py:160:48 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:103:33 - error: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:103:33 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:103:37 - error: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:169:5 - error: Type of "notes_entries" is partially unknown
    Type of "notes_entries" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:172:18 - error: Type of "note" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:172:36 - error: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__new__"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:175:13 - error: Type of "raw_label" is partially unknown
    Type of "raw_label" is "Unknown | str" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:175:25 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:175:57 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:176:13 - error: Type of "timestamp" is partially unknown
    Type of "timestamp" is "Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:176:25 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:177:13 - error: Type of "label" is partially unknown
    Type of "label" is "str | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:178:25 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:178:25 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_modals.py:181:28 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/permissions.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/permissions.py:64:54 - error: Cannot access attribute "capabilities" for class "PermissionPreset"
    Attribute "capabilities" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/permissions.py:71:40 - error: Cannot access attribute "organization_id" for class "PermissionPreset"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/permissions.py:80:66 - error: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/permissions.py:86:38 - error: Cannot access attribute "organization_id" for class "Role"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:20:5 - error: Import "delete_org_provider_credential" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:81:5 - error: Return type, "List[dict[Unknown, Unknown]]", is partially unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:81:62 - error: Expected type arguments for generic class "dict" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:96:5 - error: Type of "models" is partially unknown
    Type of "models" is "list[dict[Unknown, Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:96:18 - error: Expected type arguments for generic class "dict" (reportMissingTypeArgument)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:163:9 - error: Type of "append" is partially unknown
    Type of "append" is "(object: dict[Unknown, Unknown], /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:164:12 - error: Return type, "list[dict[Unknown, Unknown]]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:212:9 - error: Type of "models_payload" is partially unknown
    Type of "models_payload" is "List[dict[Unknown, Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:221:5 - error: Type of "data" is partially unknown
    Type of "data" is "dict[str, str | Any | List[dict[Unknown, Unknown]] | bool]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:234:12 - error: Return type, "tuple[dict[str, str | Any | List[dict[Unknown, Unknown]] | bool], list[str]]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:292:42 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:299:74 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:303:13 - error: Type "ProviderCredentialDetails" is not assignable to declared type "Dict[str, Any]"
    "ProviderCredentialDetails" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:310:42 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:345:107 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:412:75 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:438:80 - error: "name" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:452:30 - error: "full_clean" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:459:30 - error: "save" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:532:40 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:533:44 - error: "created_at" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:534:44 - error: "updated_at" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:552:22 - error: Argument of type "ProviderCredentialDetails | None" cannot be assigned to parameter "existing" of type "Dict[str, Any] | None" in function "_extract_provider_form_data"
    Type "ProviderCredentialDetails | None" is not assignable to type "Dict[str, Any] | None"
      Type "ProviderCredentialDetails" is not assignable to type "Dict[str, Any] | None"
        "ProviderCredentialDetails" is not assignable to "Dict[str, Any]"
        "ProviderCredentialDetails" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:575:62 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:587:62 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:602:73 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:613:25 - error: Type "JSONDict | None" is not assignable to declared type "Dict[str, Any]"
    Type "JSONDict | None" is not assignable to type "Dict[str, Any]"
      "None" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:641:66 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:663:38 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:668:17 - error: Type of "stored_metadata" is partially unknown
    Type of "stored_metadata" is "Any | dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:677:17 - error: Type of "metadata_override" is partially unknown
    Type of "metadata_override" is "dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:683:21 - error: Type of "effective_metadata" is partially unknown
    Type of "effective_metadata" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:689:25 - error: Type of "effective_metadata" is partially unknown
    Type of "effective_metadata" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:692:17 - error: Type of "supplied_models" is partially unknown
    Type of "supplied_models" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:708:30 - error: Argument type is partially unknown
    Argument corresponds to parameter "metadata" in function "evaluate_provider_setup"
    Argument type is "dict[Unknown, Unknown] | dict[str, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:716:37 - error: Argument of type "Any | Literal[''] | None" cannot be assigned to parameter "api_key" of type "str" in function "run_provider_live_test"
    Type "Any | Literal[''] | None" is not assignable to type "str"
      "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:717:38 - error: Argument type is partially unknown
    Argument corresponds to parameter "metadata" in function "run_provider_live_test"
    Argument type is "dict[Unknown, Unknown] | dict[str, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:761:42 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:766:21 - error: Type of "stored_metadata" is partially unknown
    Type of "stored_metadata" is "Any | dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:775:21 - error: Type of "metadata_override" is partially unknown
    Type of "metadata_override" is "dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:781:25 - error: Type of "effective_metadata" is partially unknown
    Type of "effective_metadata" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:787:29 - error: Type of "effective_metadata" is partially unknown
    Type of "effective_metadata" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:790:21 - error: Type of "supplied_models" is partially unknown
    Type of "supplied_models" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:806:34 - error: Argument type is partially unknown
    Argument corresponds to parameter "metadata" in function "evaluate_provider_setup"
    Argument type is "dict[Unknown, Unknown] | dict[str, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:814:41 - error: Argument of type "Any | Literal[''] | None" cannot be assigned to parameter "api_key" of type "str" in function "run_live_model_probe"
    Type "Any | Literal[''] | None" is not assignable to type "str"
      "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:815:42 - error: Argument type is partially unknown
    Argument corresponds to parameter "metadata" in function "run_live_model_probe"
    Argument type is "dict[Unknown, Unknown] | dict[str, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:816:47 - error: Argument of type "dict[str, JSONValue]" cannot be assigned to parameter "model_payload" of type "SanitizedModel" in function "run_live_model_probe"
    "dict[str, JSONValue]" is not assignable to "SanitizedModel" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:840:82 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:841:21 - error: Type "ProviderCredentialDetails | None" is not assignable to declared type "Dict[str, Any]"
    Type "ProviderCredentialDetails | None" is not assignable to type "Dict[str, Any]"
      "ProviderCredentialDetails" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:862:43 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:935:54 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1037:72 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1040:54 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1067:74 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1069:42 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1089:13 - error: Type of "model_meta" is partially unknown
    Type of "model_meta" is "Unknown | Any" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1090:22 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1093:13 - error: Type of "label" is partially unknown
    Type of "label" is "Unknown | Any | str" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1094:17 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1095:41 - error: Argument type is partially unknown
    Argument corresponds to parameter "key" in function "get"
    Argument type is "Unknown | Any" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1096:20 - error: Type of "replace" is partially unknown
    Type of "replace" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1096:20 - error: Type of "title" is partially unknown
    Type of "title" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1098:39 - error: Argument type is partially unknown
    Argument corresponds to parameter "key" in function "setdefault"
    Argument type is "Unknown | Any" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1098:47 - error: Argument type is partially unknown
    Argument corresponds to parameter "default" in function "setdefault"
    Argument type is "Unknown | Any | str" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1111:13 - error: Type of "models_payload" is partially unknown
    Type of "models_payload" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1113:17 - error: Type of "model_meta" is partially unknown
    Type of "model_meta" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1116:17 - error: Type of "options_meta" is partially unknown
    Type of "options_meta" is "Unknown | dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1116:32 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1116:72 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1117:17 - error: Type of "combined" is partially unknown
    Type of "combined" is "dict[Unknown | str, Unknown | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1119:49 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1120:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1120:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1121:48 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1122:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1122:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1123:53 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1124:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1124:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1125:49 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1126:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1126:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1127:52 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1128:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1128:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1129:47 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1130:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1130:37 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1132:42 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "append"
    Argument type is "dict[Unknown | str, Unknown | None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1135:17 - error: Type of "creator" is partially unknown
    Type of "creator" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1136:46 - error: Argument type is partially unknown
    Argument corresponds to parameter "key" in function "get"
    Argument type is "Any | Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1136:77 - error: Argument type is partially unknown
    Argument corresponds to parameter "key" in function "get"
    Argument type is "Any | Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1138:21 - error: Type of "label" is partially unknown
    Type of "label" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1138:29 - error: Type of "replace" is partially unknown
    Type of "replace" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1138:29 - error: Type of "title" is partially unknown
    Type of "title" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1139:17 - error: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1195:66 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1200:46 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1206:46 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1212:50 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1233:9 - error: Type of "selected_options" is partially unknown
    Type of "selected_options" is "Any | dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1253:41 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1253:58 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1276:13 - error: Type of "model" is partially unknown
    Type of "model" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1277:16 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1281:30 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1282:30 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1282:52 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1285:46 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1286:42 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1287:31 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/settings.py:1309:87 - error: "id" is not a known attribute of "None" (reportOptionalMemberAccess)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py:58:5 - error: Variable "artifacts" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py:108:5 - error: Type of "tool_panels" is partially unknown
    Type of "tool_panels" is "object | dict[Unknown, Unknown] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py:108:47 - error: Unnecessary isinstance call; "Mapping[str, object]" is always an instance of "Mapping[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py:111:9 - error: Type of "active_panel" is partially unknown
    Type of "active_panel" is "Unknown | dict[Any, Any]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/helpers.py:111:24 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, /, default: Unknown | _T@get) -> (Unknown | _T@get)] | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py:231:23 - error: Argument of type "JSONValue | None" cannot be assigned to parameter "stage_map" of type "Mapping[str, Mapping[str, object]] | None" in function "upsert_llm_configuration"
    Type "JSONValue" is not assignable to type "Mapping[str, Mapping[str, object]] | None"
      Type "float" is not assignable to type "Mapping[str, Mapping[str, object]] | None"
        "float" is not assignable to "Mapping[str, Mapping[str, object]]"
        "float" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py:232:28 - error: Argument of type "JSONValue | None" cannot be assigned to parameter "provider_chain" of type "Iterable[str] | None" in function "upsert_llm_configuration"
    Type "JSONValue" is not assignable to type "Iterable[str] | None"
      Type "float" is not assignable to type "Iterable[str] | None"
        "float" is incompatible with protocol "Iterable[str]"
          "__iter__" is not present
        "float" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py:309:17 - error: Argument of type "int | float | bool | str | dict[str, JSONValue] | list[JSONValue] | None" cannot be assigned to parameter "api_key" of type "str | None" in function "upsert_org_provider_credential"
    Type "int | float | bool | str | dict[str, JSONValue] | list[JSONValue] | None" is not assignable to type "str | None"
      Type "float" is not assignable to type "str | None"
        "float" is not assignable to "str"
        "float" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py:310:16 - error: Argument of type "Any | int | float | bool | str | dict[str, JSONValue] | list[JSONValue]" cannot be assigned to parameter "models" of type "Iterable[Mapping[str, object]] | None" in function "upsert_org_provider_credential"
    Type "Any | int | float | bool | str | dict[str, JSONValue] | list[JSONValue]" is not assignable to type "Iterable[Mapping[str, object]] | None"
      Type "float" is not assignable to type "Iterable[Mapping[str, object]] | None"
        "float" is incompatible with protocol "Iterable[Mapping[str, object]]"
          "__iter__" is not present
        "float" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/cases/updates.py:311:18 - error: Argument of type "int | float | str | dict[str, JSONValue] | list[JSONValue] | Literal[True]" cannot be assigned to parameter "metadata" of type "Mapping[str, object] | None" in function "upsert_org_provider_credential"
    Type "int | float | str | dict[str, JSONValue] | list[JSONValue] | Literal[True]" is not assignable to type "Mapping[str, object] | None"
      Type "float" is not assignable to type "Mapping[str, object] | None"
        "float" is not assignable to "Mapping[str, object]"
        "float" is not assignable to "None" (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:37:12 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:37:17 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:37:53 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:37:53 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:37:58 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:114:24 - error: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:114:24 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:114:28 - error: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:117:9 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:117:9 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/artifacts.py:117:14 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:45:5 - error: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:45:12 - error: Type of "for_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:45:12 - error: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:45:12 - error: Type of "first" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:45:21 - error: Cannot access attribute "for_user" for class "QuerySet[Case, Case]"
    Attribute "for_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:61:42 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:61:42 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:61:47 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:95:45 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:95:45 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:95:50 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:108:39 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:108:39 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/create.py:108:44 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:57:52 - error: Argument of type "Organization | None" cannot be assigned to parameter "organization" of type "Organization" in function "_get_case_for_request"
    Type "Organization | None" is not assignable to type "Organization"
      "None" is not assignable to "Organization" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:89:5 - error: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:89:12 - error: Type of "for_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:89:12 - error: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:89:12 - error: Type of "first" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:89:21 - error: Cannot access attribute "for_user" for class "QuerySet[Case, Case]"
    Attribute "for_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:124:10 - error: Unnecessary isinstance call; "_ImmutableQueryDict" is always an instance of "QueryDict" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:151:47 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:151:47 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:151:52 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:160:13 - error: Type of "chunk" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:161:31 - error: Argument type is unknown
    Argument corresponds to parameter "buffer" in function "write" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:188:47 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:188:47 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:188:52 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:247:9 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:247:9 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:247:14 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:267:9 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:267:9 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "append_job_log" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/text.py:267:14 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:59:12 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:59:17 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:59:53 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:59:53 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:59:58 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:134:9 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:134:9 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:134:14 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:140:13 - error: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:140:13 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/jobs_actions/title.py:140:17 - error: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/alerts.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/alerts.py:167:26 - error: Return type of lambda, "tuple[Unknown, Any]", is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/alerts.py:168:13 - error: No overloads for "get" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/alerts.py:168:38 - error: Argument of type "Any | None" cannot be assigned to parameter "key" of type "str" in function "get"
    Type "Any | None" is not assignable to type "str"
      "None" is not assignable to "str" (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:41:9 - error: Type of "provider_chain" is partially unknown
    Type of "provider_chain" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:64:69 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:67:42 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:68:47 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:69:41 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:70:46 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:77:19 - error: Type "Dict[str, Any] | None" is not assignable to declared type "Dict[str, Any]"
    Type "Dict[str, Any] | None" is not assignable to type "Dict[str, Any]"
      "None" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:82:12 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:87:64 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:88:69 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:89:63 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:90:68 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:129:42 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:130:47 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:131:41 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis.py:132:46 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:55:38 - error: Type of parameter "llm_settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:55:38 - error: Type annotation is missing for parameter "llm_settings" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:59:9 - error: Type of "assignment" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:59:23 - error: Type of "assignments" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:59:23 - error: Type of "values" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:60:12 - error: Type of "target" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:64:24 - error: Type of "stage_key" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:65:26 - error: Type of "label" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:65:46 - error: Type of "stage_key" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:66:32 - error: Type of "description" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:69:18 - error: Type of "stage_key" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:69:18 - error: Argument type is unknown
    Argument corresponds to parameter "element" in function "add" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:81:45 - error: Type of parameter "llm_settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:81:45 - error: Type annotation is missing for parameter "llm_settings" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:84:22 - error: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "_stage_definitions_for_target" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:94:9 - error: Type of "assignment" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:94:22 - error: Type of "stage" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:96:9 - error: Type of "selected_provider" is partially unknown
    Type of "selected_provider" is "Unknown | Any | Literal['azure']" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:97:13 - error: Type of "providers" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:98:31 - error: Type of "providers" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:101:9 - error: Type of "selected_model" is partially unknown
    Type of "selected_model" is "Unknown | Literal['']" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:101:26 - error: Type of "model" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:101:69 - error: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:102:49 - error: Type of "options" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:102:49 - error: Argument type is unknown
    Argument corresponds to parameter "map" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:105:42 - error: Argument of type "str | None" cannot be assigned to parameter "key" of type "str" in function "get"
    Type "str | None" is not assignable to type "str"
      "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:112:21 - error: Type of "candidate" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:121:41 - error: Argument type is partially unknown
    Argument corresponds to parameter "m" in function "update"
    Argument type is "dict[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:128:44 - error: Argument of type "str | None" cannot be assigned to parameter "stage_key" of type "str" in function "_stage_profile_hint"
    Type "str | None" is not assignable to type "str"
      "None" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:195:57 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:195:57 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "get_org_provider_credentials" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:195:62 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:197:25 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:197:25 - error: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "build_provider_registry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:197:30 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:206:54 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:206:54 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:206:59 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:208:33 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:208:33 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:208:38 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:214:37 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:214:37 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:214:42 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:219:62 - error: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:219:62 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:219:67 - error: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_llm.py:243:82 - error: Argument of type "LLMConfigurationPayload | None" cannot be assigned to parameter "active_config" of type "Dict[str, Any] | None" in function "_build_llm_urls"
    Type "LLMConfigurationPayload | None" is not assignable to type "Dict[str, Any] | None"
      Type "LLMConfigurationPayload" is not assignable to type "Dict[str, Any] | None"
        "LLMConfigurationPayload" is not assignable to "Dict[str, Any]"
        "LLMConfigurationPayload" is not assignable to "None" (reportArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:31:12 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:31:17 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:31:53 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:31:53 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:31:58 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:54:16 - error: Unnecessary "cast" call; type is already "dict[str, Any]" (reportUnnecessaryCast)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:253:61 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:257:40 - error: "get" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:386:49 - error: Unnecessary isinstance call; "Dict[str, Any]" is always an instance of "dict[Unknown, Unknown]" (reportUnnecessaryIsInstance)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:417:13 - error: Type of "item" is partially unknown
    Type of "item" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:418:12 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/analysis_modules.py:499:13 - error: Expected mapping for dictionary unpack operator (reportGeneralTypeIssues)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:38:39 - error: Type of "memberships" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:38:39 - error: Type of "select_related" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:38:39 - error: Argument type is unknown
    Argument corresponds to parameter "iterable" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:38:44 - error: Cannot access attribute "memberships" for class "Case"
    Attribute "memberships" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:46:28 - error: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:46:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/case_memberships.py:46:33 - error: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:40:9 - error: Type of "metadata" is partially unknown
    Type of "metadata" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:41:9 - error: Type of "history" is partially unknown
    Type of "history" is "Unknown | list[Dict[str, Any]] | Iterable[Dict[str, Any]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:41:45 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:43:9 - error: Type of "artifact_title" is partially unknown
    Type of "artifact_title" is "Any | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:43:79 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:47:13 - error: Type of "entry" is partially unknown
    Type of "entry" is "Unknown | Dict[str, Any]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:48:27 - error: Argument type is partially unknown
    Argument corresponds to parameter "map" in function "__init__"
    Argument type is "Unknown | dict[str, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:50:49 - error: Argument type is partially unknown
    Argument corresponds to parameter "default" in function "setdefault"
    Argument type is "Any | Unknown | None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:63:5 - error: Type of "status_counts" is partially unknown
    Type of "status_counts" is "Counter[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:73:9 - error: Type of "violations" is partially unknown
    Type of "violations" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:75:36 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown] | tuple[Unknown, ...]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:76:17 - error: Type of "violation" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:77:32 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:77:32 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:86:21 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:87:21 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:88:20 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:89:18 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:90:30 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (int | None), (key: Unknown, default: int, /) -> int, (key: Unknown, default: _T@get, /) -> (int | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:133:9 - error: Type of "violations" is partially unknown
    Type of "violations" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:137:13 - error: Type of "violation" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:138:13 - error: Type of "violation_data" is partially unknown
    Type of "violation_data" is "Unknown | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:139:28 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:139:28 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:140:13 - error: Type of "category" is partially unknown
    Type of "category" is "Unknown | Literal['Violation']" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:140:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/guardian.py:140:58 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/job_actions.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/job_actions.py:23:19 - error: Type of "case_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/job_actions.py:23:19 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/job_actions.py:23:23 - error: Cannot access attribute "case_id" for class "Job"
    Attribute "case_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:157:5 - error: Type of "empty_notes" is partially unknown
    Type of "empty_notes" is "dict[str, bool | int | list[Unknown] | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:194:22 - error: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:194:22 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:194:24 - error: Cannot access attribute "user_id" for class "CaseMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:205:9 - error: Type of "telem" is partially unknown
    Type of "telem" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:211:9 - error: Type of "agent" is partially unknown
    Type of "agent" is "Unknown | Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:211:18 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:212:26 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:212:26 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Any | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:213:9 - error: Type of "meta" is partially unknown
    Type of "meta" is "Unknown | Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:213:16 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:214:24 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:214:24 - error: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "__new__"
    Argument type is "Unknown | Any | Literal['']" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:217:9 - error: Type of "transcript_payload" is partially unknown
    Type of "transcript_payload" is "Unknown | Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:217:30 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:218:9 - error: Type of "path" is partially unknown
    Type of "path" is "Unknown | Any | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:218:16 - error: Type of "get" is partially unknown
    Type of "get" is "Unknown | Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:276:5 - error: Type of "case_notes" is partially unknown
    Type of "case_notes" is "dict[str, bool | int | list[Unknown] | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:285:46 - error: Argument type is partially unknown
    Argument corresponds to parameter "notes" in function "_notes_panel"
    Argument type is "dict[str, bool | int | list[Unknown] | None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:300:36 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:300:36 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:300:41 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:300:57 - error: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:300:62 - error: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:301:39 - error: Type of "client_user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:301:39 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:301:44 - error: Cannot access attribute "client_user_id" for class "Case"
    Attribute "client_user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:301:63 - error: Type of "client_user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:301:68 - error: Cannot access attribute "client_user_id" for class "Case"
    Attribute "client_user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:306:25 - error: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:306:25 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:306:36 - error: Cannot access attribute "user_id" for class "CaseMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:375:9 - error: Type of "downloads" is partially unknown
    Type of "downloads" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:376:9 - error: Type of "latest_downloads" is partially unknown
    Type of "latest_downloads" is "list[Any | Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:376:42 - error: Type of "download" is partially unknown
    Type of "download" is "Any | Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:376:67 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Unknown" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:380:5 - error: Type of "transcribe_notes" is partially unknown
    Type of "transcribe_notes" is "Any | dict[str, bool | int | list[Unknown] | None]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:408:46 - error: Argument type is partially unknown
    Argument corresponds to parameter "notes" in function "_notes_panel"
    Argument type is "dict[str, str | List[Dict[str, str | None]] | bool | int | None] | Any | dict[str, bool | int | list[Unknown] | None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:471:5 - error: Type of "analyze_latest" is partially unknown
    Type of "analyze_latest" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:472:5 - error: Type of "analyze_history" is partially unknown
    Type of "analyze_history" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:483:56 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:489:53 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:529:5 - error: Type of "compose_latest" is partially unknown
    Type of "compose_latest" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:530:5 - error: Type of "compose_history" is partially unknown
    Type of "compose_history" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:533:5 - error: Type of "compose_details" is partially unknown
    Type of "compose_details" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:538:56 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:546:34 - error: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:546:34 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "Unknown | Any" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:550:34 - error: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:594:9 - error: Type of "membership" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:594:23 - error: Type of "memberships" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:594:23 - error: Type of "select_related" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:594:41 - error: Cannot access attribute "memberships" for class "Organization"
    Attribute "memberships" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:595:9 - error: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:595:16 - error: Type of "user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:598:38 - error: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:598:38 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:598:65 - error: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:598:87 - error: Type of "username" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/presenters/tool_panels.py:598:87 - error: Argument type is unknown
    Argument corresponds to parameter "default" in function "getattr" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/apps/platform/ui/views/selectors/jobs.py
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/selectors/jobs.py:23:20 - error: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/apps/platform/ui/views/selectors/jobs.py:34:17 - error: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/db/models/job.py
  /home/user/Code/uDocket/udocket.com/db/models/job.py:29:5 - warning: Type of "upload_progress" is partially unknown
    Type of "upload_progress" is "Column[Unknown]" (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/scripts/typing/annotate_fixtures.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/annotate_fixtures.py:67:38 - error: Condition will always evaluate to False since the types "int" and "None" have no overlap (reportUnnecessaryComparison)
  /home/user/Code/uDocket/udocket.com/scripts/typing/annotate_fixtures.py:67:60 - error: Condition will always evaluate to False since the types "int" and "None" have no overlap (reportUnnecessaryComparison)
/home/user/Code/uDocket/udocket.com/scripts/typing/bootstrap_env.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/bootstrap_env.py:17:9 - error: Import "CACHE_ROOT" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/scripts/typing/bootstrap_env.py:29:9 - error: Import "CACHE_ROOT" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py:24:9 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py:25:5 - warning: Type of "unique" is partially unknown
    Type of "unique" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py:25:21 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "sorted"
    Argument type is "dict[Unknown, Any | None]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py:25:35 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "fromkeys"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_strict.py:26:12 - warning: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/scripts/typing/check_stubs.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_stubs.py:34:13 - warning: Type of "item" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_stubs.py:97:5 - warning: Type of "modules" is partially unknown
    Type of "modules" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/check_stubs.py:99:56 - warning: Argument type is partially unknown
    Argument corresponds to parameter "modules" in function "ensure_module_stubs"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/scripts/typing/enforce_pyright_strict.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/enforce_pyright_strict.py:74:13 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/enforce_pyright_strict.py:77:13 - warning: Type of "module" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/enforce_pyright_strict.py:78:19 - warning: Argument type is unknown
    Argument corresponds to parameter "values" in function "print" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/enforce_pyright_strict.py:81:34 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py:11:5 - error: "_normalize_stage_map" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py:31:12 - warning: Return type, "dict[str, dict[Unknown, Unknown]]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py:31:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py:31:33 - warning: Type of "key" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/lint_stage_overrides.py:31:38 - warning: Type of "value" is unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/scripts/typing/strictify.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/strictify.py:97:9 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/strictify.py:104:17 - warning: Type of "file_path" is unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:41:5 - warning: Type of "pyright_stats" is partially unknown
    Type of "pyright_stats" is "Any | dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:42:5 - warning: Type of "helpers" is partially unknown
    Type of "helpers" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:43:5 - warning: Type of "strict_modules" is partially unknown
    Type of "strict_modules" is "Any | list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:52:22 - warning: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:54:8 - warning: Type of "output" is partially unknown
    Type of "output" is "Unknown | Any | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:54:18 - warning: Type of "get" is partially unknown
    Type of "get" is "Any | Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:55:24 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "extend"
    Argument type is "list[Unknown | Any | str]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:55:36 - warning: Type of "strip" is partially unknown
    Type of "strip" is "Unknown | Any" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:64:33 - warning: Argument type is partially unknown
    Argument corresponds to parameter "helpers" in function "format_helper_table"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/scripts/typing/sync_docs.py:68:32 - warning: Argument type is partially unknown
    Argument corresponds to parameter "strict_modules" in function "format_strict_list"
    Argument type is "Any | list[Unknown]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/conftest.py
  /home/user/Code/uDocket/udocket.com/tests/conftest.py:9:5 - error: Function "_temp_storage_root" is not accessed (reportUnusedFunction)
  /home/user/Code/uDocket/udocket.com/tests/conftest.py:9:66 - warning: Type of parameter "settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/conftest.py:9:66 - error: Type annotation is missing for parameter "settings" (reportMissingParameterType)
/home/user/Code/uDocket/udocket.com/tests/test_analyze_stages.py
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_stages.py:4:5 - error: "_assign_entity_defaults" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_stages.py:5:5 - error: "_assign_relation_defaults" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_stages.py:7:72 - error: "_normalize_event" is private and used outside of the module in which it is declared (reportPrivateUsage)
/home/user/Code/uDocket/udocket.com/tests/test_api.py
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:26:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:40:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:42:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:42:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:42:25 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:51:36 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_authenticate" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:61:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:63:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:63:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:63:25 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_api.py:67:36 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_authenticate" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/test_azure_client.py
  /home/user/Code/uDocket/udocket.com/tests/test_azure_client.py:98:5 - warning: Type of "payload" is partially unknown
    Type of "payload" is "dict[str, list[dict[str, int | str | dict[str, str | list[dict[str, str | dict[str, list[dict[str, str | list[Unknown]]]]]]]]] | dict[str, int]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_azure_client.py:128:35 - warning: Argument type is partially unknown
    Argument corresponds to parameter "payload" in function "_client"
    Argument type is "dict[str, list[dict[str, int | str | dict[str, str | list[dict[str, str | dict[str, list[dict[str, str | list[Unknown]]]]]]]]] | dict[str, int]]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:4:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:10:5 - error: "_normalize_graph_payload" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:11:5 - error: "_normalize_timeline_payload" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:16:42 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:16:42 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:17:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:18:5 - warning: Type of "analysis_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:19:5 - warning: Type of "ops_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:20:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:21:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:23:5 - warning: Type of "summary_json" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:24:5 - warning: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:25:5 - warning: Type of "summary_md" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:26:5 - warning: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:28:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:29:5 - warning: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:33:5 - warning: Type of "stage_outputs" is partially unknown
    Type of "stage_outputs" is "dict[str, tuple[dict[str, list[Unknown]], dict[str, int], str] | tuple[dict[str, str | list[Unknown]], dict[str, int], str] | tuple[str, dict[str, int], str] | tuple[dict[str, str], dict[str, int], str]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:46:9 - warning: Type of "key" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:47:16 - warning: Return type, "tuple[dict[str, list[Unknown]], dict[str, int], str] | tuple[dict[str, str | list[Unknown]], dict[str, int], str] | tuple[str, dict[str, int], str] | tuple[dict[str, str], dict[str, int], str]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:49:56 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(self: Unknown, **kwargs: Unknown) -> (tuple[dict[str, list[Unknown]], dict[str, int], str] | tuple[dict[str, str | list[Unknown]], dict[str, int], str] | tuple[str, dict[str, int], str] | tuple[dict[str, str], dict[str, int], str])" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:53:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "compose" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:55:27 - warning: Argument type is unknown
    Argument corresponds to parameter "summary_json_path" in function "compose" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:56:31 - warning: Argument type is unknown
    Argument corresponds to parameter "summary_markdown_path" in function "compose" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:57:25 - warning: Argument type is unknown
    Argument corresponds to parameter "transcript_path" in function "compose" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:90:42 - warning: Argument of type "dict[str, list[dict[str, str | float | list[str]]]]" cannot be assigned to parameter "payload" of type "Mapping[str, JSONValue]" in function "_normalize_timeline_payload"
    "dict[str, list[dict[str, str | float | list[str]]]]" is not assignable to "Mapping[str, JSONValue]"
      Type parameter "_VT_co@Mapping" is covariant, but "list[dict[str, str | float | list[str]]]" is not a subtype of "JSONValue"
        Type "list[dict[str, str | float | list[str]]]" is not assignable to type "JSONValue"
          "list[dict[str, str | float | list[str]]]" is not assignable to "int"
          "list[dict[str, str | float | list[str]]]" is not assignable to "float"
          "list[dict[str, str | float | list[str]]]" is not assignable to "bool"
          "list[dict[str, str | float | list[str]]]" is not assignable to "str"
          "list[dict[str, str | float | list[str]]]" is not assignable to "None"
    ... (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:92:5 - warning: Type of "normalized" is partially unknown
    Type of "normalized" is "Unknown | str | int | float | bool | str | dict[str, JSONValue] | list[JSONValue] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:92:18 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:92:18 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:92:18 - warning: Argument of type "Literal[0]" cannot be assigned to parameter "key" of type "str" in function "__getitem__"
    "Literal[0]" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:92:18 - error: "__getitem__" method not defined on type "Literal[True]" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['id']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['id']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:93:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['uuid']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['uuid']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:94:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:98:5 - warning: Type of "payload" is partially unknown
    Type of "payload" is "dict[str, list[dict[str, str | list[Unknown]]] | list[dict[str, str | list[dict[str, float | str]]]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:124:39 - warning: Argument of type "dict[str, list[dict[str, str | list[Unknown]]] | list[dict[str, str | list[dict[str, float | str]]]]]" cannot be assigned to parameter "payload" of type "Mapping[str, JSONValue]" in function "_normalize_graph_payload"
    "dict[str, list[dict[str, str | list[Unknown]]] | list[dict[str, str | list[dict[str, float | str]]]]]" is not assignable to "Mapping[str, JSONValue]"
      Type parameter "_VT_co@Mapping" is covariant, but "list[dict[str, str | list[Unknown]]] | list[dict[str, str | list[dict[str, float | str]]]]" is not a subtype of "JSONValue"
        Type "list[dict[str, str | list[Unknown]]] | list[dict[str, str | list[dict[str, float | str]]]]" is not assignable to type "JSONValue"
          Type "list[dict[str, str | list[Unknown]]]" is not assignable to type "JSONValue"
            "list[dict[str, str | list[Unknown]]]" is not assignable to "int"
            "list[dict[str, str | list[Unknown]]]" is not assignable to "float"
            "list[dict[str, str | list[Unknown]]]" is not assignable to "bool"
            "list[dict[str, str | list[Unknown]]]" is not assignable to "str"
    ... (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:127:5 - warning: Type of "entity" is partially unknown
    Type of "entity" is "Unknown | str | int | float | bool | str | dict[str, JSONValue] | list[JSONValue] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:127:14 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:127:14 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:127:14 - warning: Argument of type "Literal[0]" cannot be assigned to parameter "key" of type "str" in function "__getitem__"
    "Literal[0]" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:127:14 - error: "__getitem__" method not defined on type "Literal[True]" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:128:5 - warning: Type of "relation" is partially unknown
    Type of "relation" is "Unknown | str | int | float | bool | str | dict[str, JSONValue] | list[JSONValue] | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:128:16 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:128:16 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:128:16 - warning: Argument of type "Literal[0]" cannot be assigned to parameter "key" of type "str" in function "__getitem__"
    "Literal[0]" is not assignable to "str" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:128:16 - error: "__getitem__" method not defined on type "Literal[True]" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['uuid']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['uuid']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:129:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['id']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['id']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:130:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['uuid']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['uuid']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:131:12 - warning: Argument of type "Literal['uuid']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['uuid']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['id']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['id']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:132:12 - warning: Argument of type "Literal['id']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['id']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:138:5 - error: Variable "system_prompt" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:138:33 - error: Variable "response_schema" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_compose_lib.py:138:57 - error: "_build_prompts" is protected and used outside of the class in which it is declared (reportPrivateUsage)
/home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:4:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:49:21 - error: "_parse_verdict" is protected and used outside of the class in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:47 - warning: Type of parameter "provider" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:47 - error: Type annotation is missing for parameter "provider" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:57 - warning: Type of parameter "model_name" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:57 - error: Type annotation is missing for parameter "model_name" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:69 - warning: Type of parameter "credential_payload" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:69 - error: Type annotation is missing for parameter "credential_payload" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:89 - warning: Type of parameter "options" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:90:89 - error: Type annotation is missing for parameter "options" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:24 - warning: Type of parameter "messages" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:24 - error: Type annotation is missing for parameter "messages" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:34 - warning: Type of parameter "temperature" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:34 - error: Type annotation is missing for parameter "temperature" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:47 - warning: Type of parameter "max_tokens" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:104:47 - error: Type annotation is missing for parameter "max_tokens" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:113:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*, provider: Unknown, model_name: Unknown, credential_payload: Unknown, options: Unknown) -> SimpleNamespace" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:115:60 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(provider_runtime: Unknown) -> DummyClient" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:115:67 - error: Type of parameter "provider_runtime" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:128:12 - error: Operator ">=" not supported for types "object" and "int" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:130:39 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:130:39 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:131:5 - warning: Type of "text_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:132:5 - warning: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:139:18 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:146:36 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:12 - warning: Type of "startswith" is partially unknown
    Type of "startswith" is "Unknown | ((prefix: str | tuple[str, ...], start: SupportsIndex | None = ..., end: SupportsIndex | None = ..., /) -> bool)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: Cannot access attribute "startswith" for class "int"
    Attribute "startswith" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: Cannot access attribute "startswith" for class "float"
    Attribute "startswith" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: Cannot access attribute "startswith" for class "bool"
    Attribute "startswith" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: "startswith" is not a known attribute of "None" (reportOptionalMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: Cannot access attribute "startswith" for class "dict[str, JSONValue]"
    Attribute "startswith" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_guardian_agent.py:148:32 - warning: Cannot access attribute "startswith" for class "list[JSONValue]"
    Attribute "startswith" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/test_llm_runtime.py
  /home/user/Code/uDocket/udocket.com/tests/test_llm_runtime.py:50:28 - warning: Argument of type "Dict[str, object]" cannot be assigned to parameter "credential_payload" of type "Mapping[str, JSONValue] | None" in function "build_provider_runtime_config"
    Type "Dict[str, object]" is not assignable to type "Mapping[str, JSONValue] | None"
      "Dict[str, object]" is not assignable to "Mapping[str, JSONValue]"
        Type parameter "_VT_co@Mapping" is covariant, but "object" is not a subtype of "JSONValue"
          Type "object" is not assignable to type "JSONValue"
            "object" is not assignable to "int"
            "object" is not assignable to "float"
            "object" is not assignable to "bool"
            "object" is not assignable to "str"
    ... (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_llm_runtime.py:61:5 - warning: Type of "delenv" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_llm_runtime.py:61:17 - warning: Cannot access attribute "delenv" for class "MonkeyPatch"
    Attribute "delenv" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/test_logging_config.py
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:9:5 - warning: Type of "logger_cfg" is partially unknown
    Type of "logger_cfg" is "list[str] | str | dict[str, str | bool] | dict[str, str] | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:9:18 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (dict[str, str] | None), (key: str, default: dict[str, str], /) -> dict[str, str], (key: str, default: _T@get, /) -> (dict[str, str] | _T@get)] | Overload[(key: str, /) -> (list[str] | str | None), (key: str, default: list[str] | str, /) -> (list[str] | str), (key: str, default: _T@get, /) -> (list[str] | str | _T@get)] | Overload[(key: str, /) -> (dict[str, str | bool] | None), (key: str, default: dict[str, str | bool], /) -> dict[str, str | bool], (key: str, default: _T@get, /) -> (dict[str, str | bool] | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:9:37 - warning: Cannot access attribute "get" for class "int"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:9:37 - warning: Cannot access attribute "get" for class "bool"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:11:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (str | bool | None), (key: str, default: str | bool, /) -> (str | bool), (key: str, default: _T@get, /) -> (str | bool | _T@get)] | Overload[(key: str, /) -> (str | None), (key: str, default: str, /) -> str, (key: str, default: _T@get, /) -> (str | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:11:23 - warning: Cannot access attribute "get" for class "list[str]"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:11:23 - warning: Cannot access attribute "get" for class "str"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:16:5 - warning: Type of "logger_cfg" is partially unknown
    Type of "logger_cfg" is "list[str] | str | dict[str, str | bool] | dict[str, str] | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:16:18 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (dict[str, str] | None), (key: str, default: dict[str, str], /) -> dict[str, str], (key: str, default: _T@get, /) -> (dict[str, str] | _T@get)] | Overload[(key: str, /) -> (list[str] | str | None), (key: str, default: list[str] | str, /) -> (list[str] | str), (key: str, default: _T@get, /) -> (list[str] | str | _T@get)] | Overload[(key: str, /) -> (dict[str, str | bool] | None), (key: str, default: dict[str, str | bool], /) -> dict[str, str | bool], (key: str, default: _T@get, /) -> (dict[str, str | bool] | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:16:37 - warning: Cannot access attribute "get" for class "int"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:16:37 - warning: Cannot access attribute "get" for class "bool"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:18:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (str | bool | None), (key: str, default: str | bool, /) -> (str | bool), (key: str, default: _T@get, /) -> (str | bool | _T@get)] | Overload[(key: str, /) -> (str | None), (key: str, default: str, /) -> str, (key: str, default: _T@get, /) -> (str | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:18:23 - warning: Cannot access attribute "get" for class "list[str]"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:18:23 - warning: Cannot access attribute "get" for class "str"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:22:5 - warning: Type of "logger_cfg" is partially unknown
    Type of "logger_cfg" is "list[str] | str | dict[str, str | bool] | dict[str, str] | Unknown | None" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:22:18 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (dict[str, str] | None), (key: str, default: dict[str, str], /) -> dict[str, str], (key: str, default: _T@get, /) -> (dict[str, str] | _T@get)] | Overload[(key: str, /) -> (list[str] | str | None), (key: str, default: list[str] | str, /) -> (list[str] | str), (key: str, default: _T@get, /) -> (list[str] | str | _T@get)] | Overload[(key: str, /) -> (dict[str, str | bool] | None), (key: str, default: dict[str, str | bool], /) -> dict[str, str | bool], (key: str, default: _T@get, /) -> (dict[str, str | bool] | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:22:37 - warning: Cannot access attribute "get" for class "int"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:22:37 - warning: Cannot access attribute "get" for class "bool"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:24:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Unknown | Overload[(key: str, /) -> (str | bool | None), (key: str, default: str | bool, /) -> (str | bool), (key: str, default: _T@get, /) -> (str | bool | _T@get)] | Overload[(key: str, /) -> (str | None), (key: str, default: str, /) -> str, (key: str, default: _T@get, /) -> (str | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:24:23 - warning: Cannot access attribute "get" for class "list[str]"
    Attribute "get" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_logging_config.py:24:23 - warning: Cannot access attribute "get" for class "str"
    Attribute "get" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:3:8 - error: Import "io" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:25:5 - error: Function "_is_dev_open" is not accessed (reportUnusedFunction)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:25:45 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:25:45 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:26:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:27:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:27:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:44:17 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:44:17 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:48:33 - error: Cannot access attribute "delay" for class "function"
    Attribute "delay" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:29 - warning: Type of parameter "_args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:29 - error: Type annotation is missing for parameter "_args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:65 - warning: Type of parameter "_kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:65 - error: Type annotation is missing for parameter "_kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:77 - error: "Dict" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:182:87 - error: "Any" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:188:34 - warning: Argument of type "str | None" cannot be assigned to parameter "args" of type "StrPath" in function "__new__"
    Type "str | None" is not assignable to type "StrPath"
      Type "None" is not assignable to type "StrPath"
        "None" is not assignable to "str"
        "None" is incompatible with protocol "PathLike[str]"
          "__fspath__" is not present (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:29 - warning: Type of parameter "_args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:29 - error: Type annotation is missing for parameter "_args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:86 - warning: Type of parameter "_kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:86 - error: Type annotation is missing for parameter "_kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:98 - error: "Dict" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:237:108 - error: "Any" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:384:54 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(..., case_id: str, job_id: str) -> Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:385:54 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(..., case_id: str, job_id: str, summary_job_id: str) -> Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:413:40 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/test_platform_flow.py:422:40 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
/home/user/Code/uDocket/udocket.com/tests/test_provider_credentials_uuid.py
  /home/user/Code/uDocket/udocket.com/tests/test_provider_credentials_uuid.py:1:16 - error: Import "_uuid" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/test_provider_credentials_uuid.py:3:8 - error: Import "pytest" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/test_provider_credentials_uuid.py:51:16 - error: Could not access item in TypedDict
    "display_name" is not a required key in "ProviderCredentialDetails", so access may result in runtime exception (reportTypedDictNotRequiredAccess)
  /home/user/Code/uDocket/udocket.com/tests/test_provider_credentials_uuid.py:52:16 - error: Could not access item in TypedDict
    "is_enabled" is not a required key in "ProviderCredentialDetails", so access may result in runtime exception (reportTypedDictNotRequiredAccess)
/home/user/Code/uDocket/udocket.com/tests/test_settings_config.py
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:10:39 - error: "_collect_secret_file_values" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:31:71 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:31:71 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:48:63 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:48:63 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:58:73 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:58:73 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:67:95 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:67:95 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:93:59 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:93:59 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:114:60 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:114:60 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:126:50 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:126:50 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:132:51 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:132:51 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:138:59 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:138:59 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:148:70 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:148:70 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:158:76 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:158:76 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:170:76 - warning: Type of parameter "configure_env" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_config.py:170:76 - error: Type annotation is missing for parameter "configure_env" (reportMissingParameterType)
/home/user/Code/uDocket/udocket.com/tests/test_settings_validators.py
  /home/user/Code/uDocket/udocket.com/tests/test_settings_validators.py:20:9 - error: No parameter named "_env_file" (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_settings_validators.py:21:9 - error: No parameter named "_env_file_encoding" (reportCallIssue)
/home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:23:5 - error: "_normalize_stage_map" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:68:5 - warning: Type of "summary_payload" is partially unknown
    Type of "summary_payload" is "dict[str, dict[str, str | list[str]] | dict[str, list[str]] | list[dict[str, str | list[Unknown]]] | list[dict[str, str]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:99:9 - warning: Type of "outline" is partially unknown
    Type of "outline" is "dict[str, dict[str, dict[str, str] | list[Unknown]] | list[dict[str, str | None]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:122:35 - warning: Argument of type "dict[str, dict[str, dict[str, str] | list[Unknown]] | list[dict[str, str | None]]]" cannot be assigned to parameter "outline" of type "JSONObject" in function "__init__"
    "dict[str, dict[str, dict[str, str] | list[Unknown]] | list[dict[str, str | None]]]" is not assignable to "dict[str, JSONValue]"
      Type parameter "_VT@dict" is invariant, but "dict[str, dict[str, str] | list[Unknown]] | list[dict[str, str | None]]" is not the same as "JSONValue"
      Consider switching from "dict" to "Mapping" which is covariant in the value type (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:139:9 - warning: Type of "hints" is partially unknown
    Type of "hints" is "dict[str, list[dict[str, str | list[Unknown]]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:163:34 - warning: Argument type is partially unknown
    Argument corresponds to parameter "hints" in function "__init__"
    Argument type is "dict[str, list[dict[str, str | list[Unknown]]]]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:167:18 - warning: Argument of type "dict[str, dict[str, str | list[str]] | dict[str, list[str]] | list[dict[str, str | list[Unknown]]] | list[dict[str, str]]]" cannot be assigned to parameter "data" of type "JSONObject" in function "__init__"
    "dict[str, dict[str, str | list[str]] | dict[str, list[str]] | list[dict[str, str | list[Unknown]]] | list[dict[str, str]]]" is not assignable to "dict[str, JSONValue]"
      Type parameter "_VT@dict" is invariant, but "dict[str, str | list[str]] | dict[str, list[str]] | list[dict[str, str | list[Unknown]]] | list[dict[str, str]]" is not the same as "JSONValue"
      Consider switching from "dict" to "Mapping" which is covariant in the value type (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:208:55 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:208:55 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:209:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:211:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:215:31 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "parse_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:223:51 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:223:51 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:224:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:225:23 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:227:31 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "parse_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:234:67 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:234:67 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:235:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:236:5 - warning: Type of "transcript_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:237:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:239:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:243:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:247:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:282:68 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:282:68 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:283:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:284:5 - warning: Type of "transcript_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:285:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:287:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:291:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:295:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:301:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:319:53 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:319:53 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:320:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:321:5 - warning: Type of "transcript_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:322:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:324:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:333:22 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:338:70 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:338:70 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:339:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:340:5 - warning: Type of "transcript_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:341:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:343:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:347:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:351:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:384:35 - warning: Type of "lower" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:384:53 - warning: Type of "value" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:384:62 - warning: "object" is not iterable
    "__iter__" method not defined (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:388:78 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:388:78 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:389:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:390:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:391:23 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:393:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:399:38 - warning: Argument of type "Any | None" cannot be assigned to parameter "object" of type "float" in function "append"
    Type "Any | None" is not assignable to type "float"
      "None" is not assignable to "float" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:400:36 - warning: Argument of type "Any | None" cannot be assigned to parameter "object" of type "int" in function "append"
    Type "Any | None" is not assignable to type "int"
      "None" is not assignable to "int" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:407:5 - error: Argument missing for parameter "value" (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:415:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:417:15 - warning: Argument type is unknown
    Argument corresponds to parameter "input" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:451:13 - warning: Type of "prompt" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:453:13 - warning: Type of "chunk_text" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:453:26 - warning: Type of "split" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:454:30 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:454:40 - warning: Type of "line" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:454:48 - warning: Type of "splitlines" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:454:75 - warning: Type of "strip" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:460:13 - warning: Type of "payload" is partially unknown
    Type of "payload" is "dict[str, dict[str, dict[str, str] | list[Unknown]] | list[dict[str, str | None]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:492:20 - warning: Argument of type "FailingClient" cannot be assigned to parameter "llm_client" of type "ChatClient | None" in function "generate_outline"
    Type "FailingClient" is not assignable to type "ChatClient | None"
      "FailingClient" is incompatible with protocol "ChatClient"
        "chat" is an incompatible type
          Type "(*, messages: Unknown, temperature: Unknown, max_tokens: Unknown, response_format: Unknown) -> tuple[str, dict[str, int]]" is not assignable to type "(*, messages: Sequence[ChatMessage], temperature: float = 1, max_tokens: int | None = None, response_format: ResponseFormat | None = None) -> tuple[str, TokenUsage]"
            Parameter "temperature" is missing default argument
            Parameter "max_tokens" is missing default argument
            Parameter "response_format" is missing default argument
            Function return type "tuple[str, dict[str, int]]" is incompatible with type "tuple[str, TokenUsage]"
    ... (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:502:47 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:502:47 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:503:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:505:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:509:30 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "parse_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:532:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:532:28 - warning: Type of parameter "input_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:532:28 - error: Type annotation is missing for parameter "input_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:532:40 - warning: Type of parameter "case_dir" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:532:40 - error: Type annotation is missing for parameter "case_dir" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:533:16 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:538:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:542:28 - warning: Argument type is partially unknown
    Argument corresponds to parameter "resolve_transcript" in function "__init__"
    Argument type is "(input_path: Unknown, case_dir: Unknown) -> Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:555:12 - error: Operator "<=" not supported for types "int" and "int | None"
    Operator "<=" not supported for types "int" and "None" (reportOperatorIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:558:27 - error: Operator "+" not supported for "None" (reportOptionalOperand)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:561:74 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:561:74 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:562:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:567:5 - error: Argument missing for parameter "value" (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:572:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:573:5 - warning: Type of "transcript_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:574:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:576:9 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:585:22 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:592:80 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:592:80 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:612:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:614:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:615:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:616:23 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:622:22 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:630:72 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:630:72 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:649:9 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:655:10 - error: "ProviderRuntimeConfig" is not defined (reportUndefinedVariable)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:661:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*, provider: LLMProvider, model_name: str, credential_payload: Dict[str, Any] | None, options: Dict[str, Any] | None) -> Unknown" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:664:26 - warning: Argument of type "MonkeyPatch" cannot be assigned to parameter "monkeypatch" of type "MonkeyPatch" in function "_install_stage_stubs"
    "MonkeyPatchProtocol" is not assignable to "MonkeyPatch" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:666:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:667:5 - warning: Type of "transcript" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:668:23 - warning: Argument type is unknown
    Argument corresponds to parameter "path" in function "_write_transcript" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:674:22 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "analyze" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:688:48 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:688:48 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:718:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:730:22 - error: Type "MutableMapping[str, Any]" is not assignable to declared type "Dict[str, Any]"
    "MutableMapping[str, Any]" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:744:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:756:19 - error: Type "MutableMapping[str, Any]" is not assignable to declared type "Dict[str, Any]"
    "MutableMapping[str, Any]" is not assignable to "Dict[str, Any]" (reportAssignmentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:759:33 - error: "_char_limit_for_stage" is protected and used outside of the class in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:27 - warning: Type of parameter "messages" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:27 - error: Type annotation is missing for parameter "messages" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:37 - warning: Type of parameter "temperature" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:37 - error: Type annotation is missing for parameter "temperature" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:50 - warning: Type of parameter "max_tokens" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:50 - error: Type annotation is missing for parameter "max_tokens" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:62 - warning: Type of parameter "response_format" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:791:62 - error: Type annotation is missing for parameter "response_format" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:792:13 - warning: Type of "response_format" is partially unknown
    Type of "response_format" is "Unknown | None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:793:13 - warning: Type of "sample" is partially unknown
    Type of "sample" is "dict[str, dict[str, str | list[str]] | dict[str, list[str]] | dict[str, str | list[Unknown]] | list[Unknown]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:820:20 - warning: Argument of type "DummyJSONClient" cannot be assigned to parameter "llm_client" of type "ChatClient | None" in function "generate_summary_payload"
    Type "DummyJSONClient" is not assignable to type "ChatClient | None"
      "DummyJSONClient" is incompatible with protocol "ChatClient"
        "chat" is an incompatible type
          Type "(*, messages: Unknown, temperature: Unknown, max_tokens: Unknown, response_format: Unknown | None = None) -> tuple[str, dict[str, int]]" is not assignable to type "(*, messages: Sequence[ChatMessage], temperature: float = 1, max_tokens: int | None = None, response_format: ResponseFormat | None = None) -> tuple[str, TokenUsage]"
            Parameter "temperature" is missing default argument
            Parameter "max_tokens" is missing default argument
            Function return type "tuple[str, dict[str, int]]" is incompatible with type "tuple[str, TokenUsage]"
      "DummyJSONClient" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:825:12 - warning: Type of "response_format" is partially unknown
    Type of "response_format" is "Unknown | None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - error: "__getitem__" method not defined on type "int" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - error: "__getitem__" method not defined on type "float" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - error: "__getitem__" method not defined on type "bool" (reportIndexIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - warning: Argument of type "Literal['overview']" cannot be assigned to parameter "key" of type "SupportsIndex | slice[Any, Any, Any]" in function "__getitem__"
    Type "Literal['overview']" is not assignable to type "SupportsIndex | slice[Any, Any, Any]"
      "Literal['overview']" is incompatible with protocol "SupportsIndex"
        "__index__" is not present
      "Literal['overview']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - error: Object of type "None" is not subscriptable (reportOptionalSubscript)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - error: No overloads for "__getitem__" match the provided arguments (reportCallIssue)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:826:12 - warning: Argument of type "Literal['overview']" cannot be assigned to parameter "s" of type "slice[Any, Any, Any]" in function "__getitem__"
    "Literal['overview']" is not assignable to "slice[Any, Any, Any]" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:832:13 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:832:35 - warning: Type of parameter "state" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:832:35 - error: Type annotation is missing for parameter "state" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:833:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:9 - warning: Type of "parse_transcript" is partially unknown
    Type of "parse_transcript" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:28 - warning: Type of "context_builder" is partially unknown
    Type of "context_builder" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:46 - warning: Type of "extract_outline" is partially unknown
    Type of "extract_outline" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:64 - warning: Type of "build_timeline_seeds" is partially unknown
    Type of "build_timeline_seeds" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:87 - warning: Type of "build_entity_hints" is partially unknown
    Type of "build_entity_hints" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:108 - warning: Type of "draft_markdown" is partially unknown
    Type of "draft_markdown" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:125 - warning: Type of "qa_and_finalize" is partially unknown
    Type of "qa_and_finalize" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/test_analyze_lib.py:835:143 - warning: Type of "write_ops_and_artifacts" is partially unknown
    Type of "write_ops_and_artifacts" is "(self: Self@Dummy, state: Unknown) -> Unknown" (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:25:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:26:35 - warning: Type of "pk" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:27:12 - warning: Type of "org_memberships" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:27:12 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:27:12 - warning: Type of "exists" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:28:5 - warning: Type of "refresh_from_db" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:29:12 - warning: Type of "display_name" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:30:12 - warning: Type of "email" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:31:12 - warning: Type of "is_staff" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:32:12 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:48:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:49:5 - warning: Type of "refresh_from_db" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:50:12 - warning: Type of "org_memberships" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:50:12 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:50:12 - warning: Type of "exists" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:51:12 - warning: Type of "is_staff" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:52:12 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:74:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:75:35 - warning: Type of "pk" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:76:12 - warning: Type of "org_memberships" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:76:12 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:76:12 - warning: Type of "exists" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:84:12 - warning: Type of "is_staff" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_admin_wizard.py:85:12 - warning: Type of "is_superuser" is unknown (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:13:14 - warning: Cannot assign to attribute "OIDC_OP_TOKEN_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_TOKEN_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:14:14 - warning: Cannot assign to attribute "OIDC_OP_AUTHORIZATION_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_AUTHORIZATION_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:15:14 - warning: Cannot assign to attribute "OIDC_OP_USER_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_USER_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:16:14 - warning: Cannot assign to attribute "OIDC_OP_JWKS_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_JWKS_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:19:12 - warning: Type of "get_username" is partially unknown
    Type of "get_username" is "(claims: Unknown) -> (LiteralString | Unknown | Any | str)" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:24:14 - warning: Cannot assign to attribute "OIDC_OP_TOKEN_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_TOKEN_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:25:14 - warning: Cannot assign to attribute "OIDC_OP_AUTHORIZATION_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_AUTHORIZATION_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:26:14 - warning: Cannot assign to attribute "OIDC_OP_USER_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_USER_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:27:14 - warning: Cannot assign to attribute "OIDC_OP_JWKS_ENDPOINT" for class "SettingsFixture"
    Attribute "OIDC_OP_JWKS_ENDPOINT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_oidc_backend.py:32:10 - warning: Type of "filter_users_by_claims" is partially unknown
    Type of "filter_users_by_claims" is "(claims: Unknown) -> QuerySet[AbstractBaseUser, AbstractBaseUser]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:18:10 - warning: Type of parameter "user" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:18:10 - error: Type annotation is missing for parameter "user" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:18:21 - warning: Type of parameter "headers" is partially unknown
    Parameter type is "Unknown | None" (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:18:21 - error: Type annotation is missing for parameter "headers" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:20:34 - warning: Argument type is unknown
    Argument corresponds to parameter "data" in function "get" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:20:34 - warning: Argument type is unknown
    Argument corresponds to parameter "secure" in function "get" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:20:34 - warning: Argument type is unknown
    Argument corresponds to parameter "headers" in function "get" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:20:34 - warning: Argument type is unknown
    Argument corresponds to parameter "query_params" in function "get" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:21:36 - warning: Argument of type "(r: HttpRequest) -> None" cannot be assigned to parameter "get_response" of type "_GetResponseCallable | _AsyncGetResponseCallable" in function "__init__"
    Type "(r: HttpRequest) -> None" is not assignable to type "_GetResponseCallable | _AsyncGetResponseCallable"
      Type "(r: HttpRequest) -> None" is not assignable to type "(request: HttpRequest, /) -> HttpResponseBase"
        Function return type "None" is incompatible with type "HttpResponseBase"
          "None" is not assignable to "HttpResponseBase"
      Type "(r: HttpRequest) -> None" is not assignable to type "(request: HttpRequest, /) -> Awaitable[HttpResponseBase]"
        Function return type "None" is incompatible with type "Awaitable[HttpResponseBase]"
          "None" is incompatible with protocol "Awaitable[HttpResponseBase]"
            "__await__" is not present (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:24:20 - warning: Cannot assign to attribute "user" for class "WSGIRequest"
    Type "Unknown | None" is not assignable to type "_AnyUser"
      Type "None" is not assignable to type "_AnyUser"
        "None" is not assignable to "AbstractBaseUser"
        "None" is not assignable to "AnonymousUser" (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:30:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:33:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:33:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:33:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:36:25 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_req" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:40:25 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_req" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:47:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:49:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:49:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:49:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:52:25 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_req" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:62:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:64:5 - warning: Type of "su" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:64:10 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:64:35 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:71:25 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_req" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:78:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:81:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:81:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:81:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:88:25 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_req" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:97:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:99:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:99:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:99:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:105:28 - warning: Type of parameter "qs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:105:28 - error: Type annotation is missing for parameter "qs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:109:40 - warning: Type of "filter" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:109:40 - warning: Argument type is unknown
    Argument corresponds to parameter "qs" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:112:20 - warning: Type of "exists" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:112:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:115:13 - warning: Type of "data" is partially unknown
    Type of "data" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:115:25 - warning: Type of "values_list" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:115:25 - warning: Argument type is unknown
    Argument corresponds to parameter "iterable" in function "__init__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:116:16 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: str, /) -> (Unknown | None), (key: str, default: Unknown, /) -> Unknown, (key: str, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:117:17 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:118:24 - warning: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:119:13 - warning: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:120:20 - warning: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:122:13 - warning: Return type is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:123:20 - warning: Return type is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:123:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "iter" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:125:31 - warning: Type of parameter "name" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:125:31 - error: Type annotation is missing for parameter "name" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:126:28 - warning: Argument type is unknown
    Argument corresponds to parameter "o" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:126:38 - warning: Argument type is unknown
    Argument corresponds to parameter "name" in function "getattr" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:128:22 - warning: Type of parameter "args" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:128:22 - error: Type annotation is missing for parameter "args" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:128:30 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:128:30 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/accounts/test_org_resolution.py:131:67 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(...) -> WrappedMembershipQS" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:24:20 - warning: Type of parameter "user" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:24:20 - error: Type annotation is missing for parameter "user" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:27:36 - warning: Argument of type "(r: HttpRequest) -> None" cannot be assigned to parameter "get_response" of type "_GetResponseCallable | _AsyncGetResponseCallable" in function "__init__"
    Type "(r: HttpRequest) -> None" is not assignable to type "_GetResponseCallable | _AsyncGetResponseCallable"
      Type "(r: HttpRequest) -> None" is not assignable to type "(request: HttpRequest, /) -> HttpResponseBase"
        Function return type "None" is incompatible with type "HttpResponseBase"
          "None" is not assignable to "HttpResponseBase"
      Type "(r: HttpRequest) -> None" is not assignable to type "(request: HttpRequest, /) -> Awaitable[HttpResponseBase]"
        Function return type "None" is incompatible with type "Awaitable[HttpResponseBase]"
          "None" is incompatible with protocol "Awaitable[HttpResponseBase]"
            "__await__" is not present (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:36:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:40:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:40:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:40:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:53:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:54:5 - warning: Type of "scoped_qs" is partially unknown
    Type of "scoped_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:54:17 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:56:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:58:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:60:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:62:38 - warning: Argument of type "UUID" cannot be assigned to parameter "org_id" of type "str | None" in function "set_active_admin_org_id"
    Type "UUID" is not assignable to type "str | None"
      "UUID" is not assignable to "str"
      "UUID" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:63:5 - warning: Type of "filtered_qs" is partially unknown
    Type of "filtered_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:63:19 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:69:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:76:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:76:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:76:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:101:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:102:5 - warning: Type of "scoped_qs" is partially unknown
    Type of "scoped_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:102:17 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:104:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:106:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:108:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:110:38 - warning: Argument of type "UUID" cannot be assigned to parameter "org_id" of type "str | None" in function "set_active_admin_org_id"
    Type "UUID" is not assignable to type "str | None"
      "UUID" is not assignable to "str"
      "UUID" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:111:5 - warning: Type of "filtered_qs" is partially unknown
    Type of "filtered_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:111:19 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:117:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:119:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:119:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:119:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:127:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:130:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:135:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:138:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:138:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:138:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:152:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:155:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:160:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:162:5 - warning: Type of "admin_user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:162:18 - warning: Type of "create_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:162:43 - warning: Cannot access attribute "create_superuser" for class "Manager[_UserModel]"
    Attribute "create_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:166:24 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_login" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:175:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:182:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:182:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:182:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:211:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:212:5 - warning: Type of "scoped_qs" is partially unknown
    Type of "scoped_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:212:17 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:213:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:215:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:217:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:219:38 - warning: Argument of type "UUID" cannot be assigned to parameter "org_id" of type "str | None" in function "set_active_admin_org_id"
    Type "UUID" is not assignable to type "str | None"
      "UUID" is not assignable to "str"
      "UUID" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:220:5 - warning: Type of "filtered_qs" is partially unknown
    Type of "filtered_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:220:19 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:221:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:226:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:233:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:233:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:233:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:245:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:247:5 - warning: Type of "scoped_qs" is partially unknown
    Type of "scoped_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:247:17 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:248:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:249:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:251:12 - warning: Type of "has_view_permission" is partially unknown
    Type of "has_view_permission" is "(request: HttpRequest, obj: Unknown | None = None) -> bool" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:253:38 - warning: Argument of type "UUID" cannot be assigned to parameter "org_id" of type "str | None" in function "set_active_admin_org_id"
    Type "UUID" is not assignable to type "str | None"
      "UUID" is not assignable to "str"
      "UUID" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:254:5 - warning: Type of "filtered_qs" is partially unknown
    Type of "filtered_qs" is "QuerySet[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:254:19 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:255:17 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:260:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:270:5 - warning: Type of "superuser" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:270:17 - warning: Type of "create_superuser" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:270:42 - warning: Cannot access attribute "create_superuser" for class "Manager[_UserModel]"
    Attribute "create_superuser" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:276:30 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "_admin_request" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:277:16 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:277:16 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:279:38 - warning: Argument of type "UUID" cannot be assigned to parameter "org_id" of type "str | None" in function "set_active_admin_org_id"
    Type "UUID" is not assignable to type "str | None"
      "UUID" is not assignable to "str"
      "UUID" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:280:25 - warning: Type of "get_queryset" is partially unknown
    Type of "get_queryset" is "(request: HttpRequest) -> QuerySet[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/admin/test_tenant_admin.py:280:25 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "QuerySet[Unknown, Any]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:3:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:21:41 - warning: Type of parameter "org_case" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:21:41 - error: Type annotation is missing for parameter "org_case" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:22:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:23:5 - warning: Type of "_" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:23:8 - warning: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:32:42 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:36:45 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:38:5 - warning: Type of "refresh_from_db" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:39:12 - warning: Type of "title" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:42:46 - warning: Type of parameter "org_case" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:42:46 - error: Type annotation is missing for parameter "org_case" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:42:83 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:42:83 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:43:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:44:5 - warning: Type of "_" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:44:8 - warning: Type of "case" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:51:5 - warning: Type of "transcript_path" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:52:5 - warning: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_access_policies.py:53:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:14:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:24:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:43:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:51:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:62:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:62:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:62:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/authorization/test_authz_api.py:66:31 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_authenticate" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/cases/test_case_api.py
  /home/user/Code/uDocket/udocket.com/tests/cases/test_case_api.py:14:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/cases/test_case_api.py:33:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:7:8 - error: "os" is imported more than once (reportDuplicateImport)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:81:51 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:81:51 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:88:49 - warning: Argument type is unknown
    Argument corresponds to parameter "tmp_dir" in function "_copy_to_tmp" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:89:40 - warning: Argument type is unknown
    Argument corresponds to parameter "out_dir" in function "normalize_audio" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:95:45 - warning: Argument type is unknown
    Argument corresponds to parameter "tmp_dir" in function "_copy_to_tmp" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:96:38 - warning: Argument type is unknown
    Argument corresponds to parameter "out_dir" in function "normalize_audio" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:101:51 - warning: Argument type is unknown
    Argument corresponds to parameter "tmp_dir" in function "_copy_to_tmp" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:102:46 - warning: Argument type is unknown
    Argument corresponds to parameter "out_dir" in function "normalize_audio" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:109:44 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:109:44 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:116:5 - warning: Type of "case_dir" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:117:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:128:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "transcribe" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:144:18 - warning: Argument type is unknown
    Argument corresponds to parameter "case_dir" in function "transcribe" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:158:40 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:158:40 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:165:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:166:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:166:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:167:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:167:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:178:36 - warning: Cannot access attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:186:38 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:196:48 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:196:48 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:212:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:213:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:213:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:214:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:214:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:226:36 - warning: Cannot access attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:232:38 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:243:56 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:243:56 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:258:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:259:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:259:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:260:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:260:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:273:36 - warning: Cannot access attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/e2e/test_transcribe_e2e.py:279:38 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
/home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:3:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:18:68 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:18:68 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:19:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:19:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:20:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:20:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:21:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:27:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:27:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:27:31 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:45:24 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_login" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:50:27 - warning: Type of "streaming_content" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:50:27 - warning: Argument type is unknown
    Argument corresponds to parameter "iterable_of_bytes" in function "join" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:50:36 - warning: Cannot access attribute "streaming_content" for class "_MonkeyPatchedResponse"
    Attribute "streaming_content" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:55:72 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:55:72 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:56:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:56:33 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:57:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:57:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:58:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:64:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:64:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:64:31 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_download_analysis.py:70:24 - warning: Argument type is unknown
    Argument corresponds to parameter "user" in function "force_login" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:14:44 - error: "_update_job_meta" is private and used outside of the module in which it is declared (reportPrivateUsage)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:19:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:51:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:60:12 - warning: Type of "reviewed_by_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:60:16 - warning: Cannot access attribute "reviewed_by_id" for class "Job"
    Attribute "reviewed_by_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:60:34 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:60:43 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:68:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:97:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:97:18 - error: Variable "reviewer" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:106:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:115:18 - error: Variable "reviewer" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:136:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:136:18 - error: Variable "reviewer" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:138:43 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:138:43 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:138:48 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:143:36 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:143:36 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "_update_job_meta" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:143:41 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:152:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:153:36 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:153:36 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:153:41 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:185:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:185:18 - error: Variable "reviewer" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:186:36 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:186:36 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ensure_case_dirs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_review_api.py:186:41 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:25:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:42:5 - warning: Type of "data_owner" is partially unknown
    Type of "data_owner" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:42:18 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:43:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:44:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:48:5 - warning: Type of "data_contrib" is partially unknown
    Type of "data_contrib" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:48:20 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:49:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:50:12 - warning: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:54:5 - warning: Type of "data_reviewer" is partially unknown
    Type of "data_reviewer" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:54:21 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:60:5 - warning: Type of "data_anon" is partially unknown
    Type of "data_anon" is "ReturnDict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_serializers.py:60:17 - warning: Type of "data" is partially unknown
    Type of "data" is "ReturnDict[Unknown, Unknown]" (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:4:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:18:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:32:39 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:32:39 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:32:44 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:110:11 - error: Variable "owner" is not accessed (reportUnusedVariable)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_telemetry_api.py:124:18 - error: Variable "reviewer" is not accessed (reportUnusedVariable)
/home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:17:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:18:14 - warning: Cannot assign to attribute "STORAGE_ROOT" for class "SettingsFixture"
    Attribute "STORAGE_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:42:38 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:42:38 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:42:43 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:53:82 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:53:82 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:54:63 - warning: Argument type is unknown
    Argument corresponds to parameter "storage_root" in function "_setup_case_with_job" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:66:85 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:66:85 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:67:51 - warning: Argument type is unknown
    Argument corresponds to parameter "storage_root" in function "_setup_case_with_job" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:80:90 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:80:90 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/jobs/test_verify_hash.py:81:63 - warning: Argument type is unknown
    Argument corresponds to parameter "storage_root" in function "_setup_case_with_job" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:7:26 - error: Import "timezone" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(case_id: Unknown, org_id: Unknown, job_id: Unknown, updates: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:16 - error: Type of parameter "case_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:25 - error: Type of parameter "org_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:33 - error: Type of parameter "job_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:41 - error: Type of parameter "updates" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:29:68 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "append"
    Argument type is "tuple[Unknown, Unknown, Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(case_id: Unknown, org_id: Unknown, job_id: Unknown, message: Unknown, level: str = "INFO") -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:16 - error: Type of parameter "case_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:25 - error: Type of parameter "org_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:33 - error: Type of parameter "job_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:41 - error: Type of parameter "message" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:34:81 - warning: Argument type is partially unknown
    Argument corresponds to parameter "object" in function "append"
    Argument type is "tuple[Unknown, Unknown, Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:63:12 - warning: Type of "approx" is partially unknown
    Type of "approx" is "(expected: Unknown, rel: Unknown | None = None, abs: Unknown | None = None, nan_ok: bool = False) -> ApproxBase" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:63:45 - warning: Type of "approx" is partially unknown
    Type of "approx" is "(expected: Unknown, rel: Unknown | None = None, abs: Unknown | None = None, nan_ok: bool = False) -> ApproxBase" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:92:12 - warning: Type of "approx" is partially unknown
    Type of "approx" is "(expected: Unknown, rel: Unknown | None = None, abs: Unknown | None = None, nan_ok: bool = False) -> ApproxBase" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:92:49 - warning: Type of "approx" is partially unknown
    Type of "approx" is "(expected: Unknown, rel: Unknown | None = None, abs: Unknown | None = None, nan_ok: bool = False) -> ApproxBase" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:151:53 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*args: Unknown, **kwargs: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:151:61 - error: Type of parameter "args" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:151:69 - error: Type of parameter "kwargs" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:152:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*args: Unknown, **kwargs: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:152:60 - error: Type of parameter "args" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/test_job_runtime_context.py:152:68 - error: Type of parameter "kwargs" is partially unknown (reportUnknownLambdaType)
/home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:3:21 - error: Import "Path" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:18:108 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:18:108 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:19:5 - warning: Type of "media_root" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:20:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:21:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:21:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:51:28 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:51:28 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:53:13 - warning: Type of "call_payload" is partially unknown
    Type of "call_payload" is "dict[str, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:76:58 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(_org_id: Unknown) -> SimpleNamespace" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:76:65 - error: Type of parameter "_org_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:77:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_: Unknown, **__: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:77:60 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:77:65 - error: Type of parameter "__" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:79:45 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:90:111 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:90:111 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:91:5 - warning: Type of "media_root" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:92:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:93:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:93:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:123:28 - warning: Type of parameter "kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:123:28 - error: Type annotation is missing for parameter "kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:125:13 - warning: Type of "call_payload" is partially unknown
    Type of "call_payload" is "dict[str, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:148:58 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(_org_id: Unknown) -> SimpleNamespace" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:148:65 - error: Type of parameter "_org_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:149:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_: Unknown, **__: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:149:60 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:149:65 - error: Type of parameter "__" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_guardian_task.py:151:36 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
/home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:19:118 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:19:118 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:20:5 - warning: Type of "media_root" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:21:5 - warning: Type of "mkdir" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:22:14 - warning: Cannot assign to attribute "MEDIA_ROOT" for class "SettingsFixture"
    Attribute "MEDIA_ROOT" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:22:31 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:35:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_: Unknown, **__: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:35:60 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:35:65 - error: Type of parameter "__" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:36:52 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_: Unknown, **__: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:36:60 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:36:65 - error: Type of parameter "__" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:37:46 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_: Unknown, **__: Unknown) -> None" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:37:54 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:37:59 - error: Type of parameter "__" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:41:47 - error: Type of parameter "_" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:46:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(organization_id: Unknown, config_id: Unknown, target: Unknown) -> dict[str, str | list[str] | dict[Unknown, Unknown]]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:46:16 - error: Type of parameter "organization_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:46:33 - error: Type of parameter "config_id" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:46:44 - error: Type of parameter "target" is unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:46:52 - error: Return type of lambda, "dict[str, str | list[str] | dict[Unknown, Unknown]]", is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:51:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(**_kwargs: Unknown) -> dict[str, str | list[str] | dict[Unknown, Unknown]]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:51:18 - error: Type of parameter "_kwargs" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:51:27 - error: Return type of lambda, "dict[str, str | list[str] | dict[Unknown, Unknown]]", is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:53:69 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_args: Unknown, **_kwargs: Unknown) -> dict[Unknown, Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:53:77 - error: Type of parameter "_args" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:53:86 - error: Type of parameter "_kwargs" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:53:95 - error: Return type of lambda, "dict[Unknown, Unknown]", is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:57:9 - warning: Argument type is partially unknown
    Argument corresponds to parameter "value" in function "setattr"
    Argument type is "(*_args: Unknown, **_kwargs: Unknown) -> list[str]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:57:17 - error: Type of parameter "_args" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:57:26 - error: Type of parameter "_kwargs" is partially unknown (reportUnknownLambdaType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:90:28 - warning: Type of parameter "config" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:90:28 - error: Type annotation is missing for parameter "config" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:30 - warning: Type of parameter "input" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:30 - error: Type annotation is missing for parameter "input" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:37 - warning: Type of parameter "case_dir" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:37 - error: Type annotation is missing for parameter "case_dir" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:47 - warning: Type of parameter "job_id" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:47 - error: Type annotation is missing for parameter "job_id" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:57 - warning: Type of parameter "_kwargs" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:93:57 - error: Type annotation is missing for parameter "_kwargs" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:94:31 - warning: Argument type is unknown
    Argument corresponds to parameter "args" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:97:59 - warning: Argument type is unknown
    Argument corresponds to parameter "args" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:97:74 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:101:23 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
  /home/user/Code/uDocket/udocket.com/tests/platform/operations/test_analyze_task.py:102:23 - error: Cannot access attribute "run" for class "function"
    Attribute "run" is unknown (reportFunctionMemberAccess)
/home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:22:5 - warning: Type of "user_a" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:22:14 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:22:27 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:23:5 - warning: Type of "user_b" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:23:14 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/tenancy/test_scope_helpers.py:23:27 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:17:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:23:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:23:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:23:31 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:88:80 - warning: Type of parameter "tmp_path" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:88:80 - error: Type annotation is missing for parameter "tmp_path" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:89:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:95:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:95:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:95:31 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:124:18 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:136:18 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:148:18 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_analysis_presenters.py:169:22 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_page.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_page.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:13:71 - warning: Type of parameter "django_user_model" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:13:71 - error: Type annotation is missing for parameter "django_user_model" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:15:5 - warning: Type of "user" is partially unknown
    Type of "user" is "Unknown | User" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:15:18 - warning: Type of "objects" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:15:18 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:50:5 - warning: Type of "force_login" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:50:12 - warning: Cannot access attribute "force_login" for class "ClientFixture"
    Attribute "force_login" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:51:5 - warning: Type of "session" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:51:15 - warning: Type of "session" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:51:22 - warning: Cannot access attribute "session" for class "ClientFixture"
    Attribute "session" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_artifacts_view.py:53:5 - warning: Type of "save" is unknown (reportUnknownMemberType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:24:25 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:24:25 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:24:34 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:25:28 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:25:28 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:25:35 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:26:22 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:26:22 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:26:28 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:27:30 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:27:30 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:27:42 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:16 - warning: Type of "reviewer_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:16 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:21 - warning: Cannot access attribute "reviewer_id" for class "Case"
    Attribute "reviewer_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:41 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:41 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:31:50 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:16 - warning: Type of "client_user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:16 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:21 - warning: Cannot access attribute "client_user_id" for class "Case"
    Attribute "client_user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:44 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:44 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:32:51 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:17 - warning: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:21 - warning: Cannot access attribute "user_id" for class "CaseMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:64 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:64 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:35:70 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:17 - warning: Type of "user_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:17 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:21 - warning: Cannot access attribute "user_id" for class "CaseMembership"
    Attribute "user_id" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:70 - warning: Type of "id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:70 - warning: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_membership.py:38:82 - warning: Cannot access attribute "id" for class "User"
    Attribute "id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_case_pages.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_pages.py:14:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_pages.py:32:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_pages.py:47:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_case_tool_panels.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_tool_panels.py:53:5 - warning: Type of "analysis_modules" is partially unknown
    Type of "analysis_modules" is "list[dict[str, str | dict[str, bool | list[Unknown] | None] | list[Unknown] | None]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_case_tool_panels.py:65:26 - warning: Argument type is partially unknown
    Argument corresponds to parameter "analysis_modules" in function "build_tool_panels"
    Argument type is "list[dict[str, str | dict[str, bool | list[Unknown] | None] | list[Unknown] | None]]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_pages.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_pages.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_pages.py:53:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_presenters.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_presenters.py:10:5 - warning: Type of "artifacts" is partially unknown
    Type of "artifacts" is "list[dict[str, int | str | dict[str, list[dict[str, str | list[Unknown]] | dict[str, str | list[dict[str, str]]]]]]]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_presenters.py:37:40 - warning: Argument type is partially unknown
    Argument corresponds to parameter "artifacts" in function "collect_guardian_reviews"
    Argument type is "list[dict[str, int | str | dict[str, list[dict[str, str | list[Unknown]] | dict[str, str | list[dict[str, str]]]]]]]" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_report.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_guardian_report.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:3:8 - error: Import "io" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:38:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:69:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:102:5 - warning: Type of "ids" is partially unknown
    Type of "ids" is "set[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:102:27 - warning: Type of "item" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:104:5 - warning: Type of "status_map" is partially unknown
    Type of "status_map" is "dict[Unknown, Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_creation.py:104:50 - warning: Type of "item" is unknown (reportUnknownVariableType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_job_detail_panel.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_detail_panel.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_detail_panel.py:31:33 - warning: Type of "organization_id" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_detail_panel.py:31:33 - warning: Argument type is unknown
    Argument corresponds to parameter "organization_id" in function "ops_dir" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_detail_panel.py:31:38 - warning: Cannot access attribute "organization_id" for class "Case"
    Attribute "organization_id" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:65:5 - warning: Type of "status_values" is partially unknown
    Type of "status_values" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:65:42 - warning: Type of "option" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:65:52 - warning: "object" is not iterable
    "__iter__" method not defined (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:66:5 - warning: Type of "agent_values" is partially unknown
    Type of "agent_values" is "list[Unknown]" (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:66:41 - warning: Type of "option" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:66:51 - warning: "object" is not iterable
    "__iter__" method not defined (reportGeneralTypeIssues)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:68:16 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:68:38 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "set[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:68:42 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:69:16 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:69:37 - warning: Argument type is partially unknown
    Argument corresponds to parameter "obj" in function "len"
    Argument type is "set[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:69:41 - warning: Argument type is partially unknown
    Argument corresponds to parameter "iterable" in function "__init__"
    Argument type is "list[Unknown]" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_job_tables.py:73:12 - error: Operator ">=" not supported for types "object" and "Literal[1]" (reportOperatorIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_jobs_presenters.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_jobs_presenters.py:51:5 - error: Variable "case" is not accessed (reportUnusedVariable)
/home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:82:5 - warning: Type of "delenv" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:82:17 - warning: Cannot access attribute "delenv" for class "MonkeyPatch"
    Attribute "delenv" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:86:66 - warning: Type of parameter "llm_settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:86:66 - error: Type annotation is missing for parameter "llm_settings" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:89:22 - warning: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "build_provider_registry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:107:68 - warning: Type of parameter "llm_settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:107:68 - error: Type annotation is missing for parameter "llm_settings" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:124:22 - warning: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "build_provider_registry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:126:30 - warning: Argument of type "dict[str, dict[str, str | list[dict[str, str]]]]" cannot be assigned to parameter "provider_credentials" of type "Mapping[str, ProviderCredentialDetails] | None" in function "build_provider_registry"
    Type "dict[str, dict[str, str | list[dict[str, str]]]]" is not assignable to type "Mapping[str, ProviderCredentialDetails] | None"
      "dict[str, dict[str, str | list[dict[str, str]]]]" is not assignable to "Mapping[str, ProviderCredentialDetails]"
        Type parameter "_VT_co@Mapping" is covariant, but "dict[str, str | list[dict[str, str]]]" is not a subtype of "ProviderCredentialDetails"
          "dict[str, str | list[dict[str, str]]]" is not assignable to "ProviderCredentialDetails"
      "dict[str, dict[str, str | list[dict[str, str]]]]" is not assignable to "None" (reportArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:138:62 - warning: Type of parameter "llm_settings" is unknown (reportUnknownParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:138:62 - error: Type annotation is missing for parameter "llm_settings" (reportMissingParameterType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:141:22 - warning: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "build_provider_registry" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:148:15 - warning: Type of "build_llm_stage_configs" is partially unknown
    Type of "build_llm_stage_configs" is "(*, target: str, llm_settings: Unknown, stage_map: Dict[str, Dict[str, Any]], provider_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:150:22 - warning: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "build_llm_stage_configs" (reportUnknownArgumentType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:173:29 - warning: Type of "build_llm_stage_configs" is partially unknown
    Type of "build_llm_stage_configs" is "(*, target: str, llm_settings: Unknown, stage_map: Dict[str, Dict[str, Any]], provider_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]" (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_presenters.py:175:22 - warning: Argument type is unknown
    Argument corresponds to parameter "llm_settings" in function "build_llm_stage_configs" (reportUnknownArgumentType)
/home/user/Code/uDocket/udocket.com/tests/ui/test_llm_settings.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_llm_settings.py:16:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:14:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:59:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:100:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:157:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:204:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_organization_settings.py:244:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:15:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:30:5 - warning: Type of "user" is unknown (reportUnknownVariableType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:30:12 - warning: Type of "create_user" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:30:37 - warning: Cannot access attribute "create_user" for class "Manager[_UserModel]"
    Attribute "create_user" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:32:5 - warning: Type of "force_login" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:32:12 - warning: Cannot access attribute "force_login" for class "ClientFixture"
    Attribute "force_login" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:47:14 - warning: Cannot assign to attribute "PLATFORM_DEV_OPEN" for class "SettingsFixture"
    Attribute "PLATFORM_DEV_OPEN" is unknown (reportAttributeAccessIssue)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:50:12 - warning: Type of "LOGIN_URL" is unknown (reportUnknownMemberType)
  /home/user/Code/uDocket/udocket.com/tests/ui/test_permissions_page.py:50:21 - warning: Cannot access attribute "LOGIN_URL" for class "SettingsFixture"
    Attribute "LOGIN_URL" is unknown (reportAttributeAccessIssue)
/home/user/Code/uDocket/udocket.com/typings/channels/__init__.pyi
  /home/user/Code/uDocket/udocket.com/typings/channels/__init__.pyi:3:12 - error: "layers" is specified in __all__ but is not present in module (reportUnsupportedDunderAll)
  /home/user/Code/uDocket/udocket.com/typings/channels/__init__.pyi:3:22 - error: "generic" is specified in __all__ but is not present in module (reportUnsupportedDunderAll)
  /home/user/Code/uDocket/udocket.com/typings/channels/__init__.pyi:3:33 - error: "db" is specified in __all__ but is not present in module (reportUnsupportedDunderAll)
/home/user/Code/uDocket/udocket.com/typings/channels/generic/__init__.pyi
  /home/user/Code/uDocket/udocket.com/typings/channels/generic/__init__.pyi:3:12 - error: "websocket" is specified in __all__ but is not present in module (reportUnsupportedDunderAll)
/home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:60:51 - error: The class "X509Extension" is deprecated
    X509Extension support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:64:44 - error: The class "X509Extension" is deprecated
    X509Extension support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:90:51 - error: The class "X509Extension" is deprecated
    X509Extension support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:93:38 - error: The class "X509Extension" is deprecated
    X509Extension support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:126:36 - error: The class "Revoked" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:129:74 - error: The class "CRL" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:131:36 - error: The class "Revoked" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:141:28 - error: The class "CRL" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:188:30 - error: The class "CRL" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
  /home/user/Code/uDocket/udocket.com/typings/vendor/OpenSSL-stubs/crypto.pyi:190:49 - error: The class "CRL" is deprecated
    CRL support in pyOpenSSL is deprecated. You should use the APIs in cryptography. (reportDeprecated)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/conf/__init__.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/conf/__init__.pyi:9:15 - error: Import "global_settings" is not accessed (reportUnusedImport)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/conf/__init__.pyi:45:17 - error: __new__ override should take a "cls" parameter (reportSelfClsParameterName)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/handlers/asgi.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/handlers/asgi.pyi:32:9 - error: Mismatch between signature of __new__ and __init__ in class "ASGIRequest"
    Signature of __init__ is "(scope: Mapping[str, Any], body_file: IO[bytes]) -> None"
    Signature of __new__ is "() -> _MutableHttpRequest" (reportInconsistentConstructor)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/handlers/wsgi.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/handlers/wsgi.pyi:28:9 - error: Mismatch between signature of __new__ and __init__ in class "WSGIRequest"
    Signature of __init__ is "(environ: WSGIEnvironment) -> None"
    Signature of __new__ is "() -> _MutableHttpRequest" (reportInconsistentConstructor)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/serializers/xml_serializer.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/core/serializers/xml_serializer.pyi:4:6 - error: Import "xml.sax.expatreader" could not be resolved (reportMissingImports)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:47:31 - error: Type "Self@Model" cannot be assigned to type variable "_T@Manager"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_T@Manager"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:49:29 - error: Type "Self@Model" cannot be assigned to type variable "_M@Options"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_M@Options"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:59:27 - error: Type "Self@Model" cannot be assigned to type variable "_Model@QuerySet"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_Model@QuerySet"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:106:33 - error: Type "Self@Model" cannot be assigned to type variable "_Model@QuerySet"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_Model@QuerySet"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:112:33 - error: Type "Self@Model" cannot be assigned to type variable "_Model@QuerySet"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_Model@QuerySet"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/db/models/base.pyi:120:41 - error: Type "Self@Model" cannot be assigned to type variable "_M@Options"
    Type "Model*" is not assignable to upper bound "Model" for type variable "_M@Options"
      "Model*" is not assignable to "Model" (reportInvalidTypeArguments)
/home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/utils/deconstruct.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/django-stubs/utils/deconstruct.pyi:12:21 - error: Instance methods should take a "self" parameter (reportSelfClsParameterName)
/home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/auth.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/auth.pyi:5:6 - warning: Stub file not found for "mozilla_django_oidc.utils" (reportMissingTypeStubs)
/home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/middleware.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/middleware.pyi:6:6 - warning: Stub file not found for "mozilla_django_oidc.auth" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/middleware.pyi:7:6 - warning: Stub file not found for "mozilla_django_oidc.utils" (reportMissingTypeStubs)
/home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/urls.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/urls.pyi:4:6 - warning: Stub file not found for "mozilla_django_oidc" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/urls.pyi:5:6 - warning: Stub file not found for "mozilla_django_oidc.utils" (reportMissingTypeStubs)
/home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/views.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/views.pyi:5:6 - warning: Stub file not found for "mozilla_django_oidc.utils" (reportMissingTypeStubs)
/home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/contrib/drf.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/contrib/drf.pyi:4:6 - warning: Stub file not found for "mozilla_django_oidc.auth" (reportMissingTypeStubs)
  /home/user/Code/uDocket/udocket.com/typings/vendor/mozilla_django_oidc-stubs/mozilla_django_oidc/contrib/drf.pyi:5:6 - warning: Stub file not found for "mozilla_django_oidc.utils" (reportMissingTypeStubs)
/home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:8:41 - error: "postgres_fields" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:16:12 - error: "uritemplate" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:24:12 - error: "yaml" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:32:12 - error: "requests" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:36:12 - error: "pygments" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:41:12 - error: "markdown" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:43:5 - error: "apply_markdown" is declared as a TypeAlias and can be assigned only once (reportRedeclaration)
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/compat.pyi:43:9 - error: Function declaration "apply_markdown" is obscured by a declaration of the same name (reportRedeclaration)
/home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/decorators.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/decorators.pyi:16:34 - error: Import "APIView" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/fields.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/fields.pyi:15:40 - error: Import "DjangoImageField" is not accessed (reportUnusedImport)
/home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/request.pyi
  /home/user/Code/uDocket/udocket.com/typings/vendor/rest_framework-stubs/request.pyi:59:9 - error: Mismatch between signature of __new__ and __init__ in class "Request"
    Signature of __init__ is "(request: HttpRequest, parsers: Sequence[BaseParser] | None = ..., authenticators: Sequence[BaseAuthentication] | None = ..., negotiator: BaseContentNegotiation | None = ..., parser_context: dict[str, Any] | None = ...) -> None"
    Signature of __new__ is "() -> _MutableHttpRequest" (reportInconsistentConstructor)
912 errors, 1919 warnings, 0 informations 
Completed in 31.192sec

Analysis stats
Total files parsed and bound: 2645
Total files checked: 1390

Timing stats
Find Source Files:    0.43sec
Read Source Files:    0.77sec
Tokenize:             1.64sec
Parse:                2.48sec
Resolve Imports:      1.38sec
Bind:                 2.79sec
Check:                19.91sec
Detect Cycles:        0sec
WARNING: there is a new pyright version available (v1.1.392 -> v1.1.406).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`
```

## Helpers

| Helper | Version | Status | Last Run |
| --- | --- | --- | --- |
| annotate_fixtures | 0.1.0 | noop | 2025-10-05T00:48:27.852541+00:00 |
| bootstrap_env | 0.1.0 | ok | 2025-10-05T15:51:45.333494+00:00 |
| check_stubs | 0.1.0 | ok | 2025-10-05T00:50:48.275330+00:00 |
| manager_codemod | 0.1.0 | ok | 2025-10-05T01:12:14.502402+00:00 |
| vendor_stubs | 0.1.0 | ok | 2025-10-05T16:36:47.163829+00:00 |

## Strict Modules

- `apps/platform/accounts/admin.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/accounts/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/accounts/utils.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/artifacts/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/authorization/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/cases/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/cases/urls.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/jobs/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/operations` (verified 2025-10-05T09:59:21.344981+00:00)
- `apps/platform/operations/audit.py` (verified 2025-10-05T02:35:51.158148+00:00)
- `apps/platform/operations/consumers.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/operations/guardian.py` (verified 2025-10-05T02:01:56.432469+00:00)
- `apps/platform/operations/llm.py` (verified 2025-10-05T03:56:36.755416+00:00)
- `apps/platform/operations/models.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `apps/platform/operations/runtime.py` (verified 2025-10-05T03:11:31.320806+00:00)
- `apps/platform/operations/services/analysis.py` (verified 2025-10-05T04:59:48.388129+00:00)
- `apps/platform/operations/services/compose.py` (verified 2025-10-05T04:59:48.388129+00:00)
- `apps/platform/operations/storage.py` (verified 2025-10-05T02:30:08.369351+00:00)
- `apps/platform/operations/utils.py` (verified 2025-10-05T02:23:55.005915+00:00)
- `apps/platform/operations/views.py` (verified 2025-10-05T02:23:55.005915+00:00)
- `apps/platform/ui/admin.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `config/settings.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `packages/core/agents/analyze_lib.py` (verified 2025-10-05T04:59:48.388129+00:00)
- `packages/core/agents/common/azure_client.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `packages/core/agents/common/io.py` (verified 2025-10-05T01:44:10.645472+00:00)
- `packages/core/agents/compose_lib.py` (verified 2025-10-05T12:29:14.118682+00:00)
- `packages/core/agents/transcribe_lib.py` (verified 2025-10-05T12:29:14.118682+00:00)
- `apps/platform/operations/task_modules/guardian.py` (verified 2025-10-05T12:29:14.118682+00:00)
- `apps/platform/operations/task_modules/transcribe.py` (verified 2025-10-05T12:29:14.118682+00:00)
