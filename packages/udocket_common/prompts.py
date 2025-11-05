from __future__ import annotations

# pyright: strict
import json
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
from pathlib import Path
from typing import Any, cast

import yaml
from jinja2 import Environment, StrictUndefined, Template, meta
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

RESOURCE_PACKAGE = "packages.udocket_prompts.resources"
DEFAULT_LOCALE = "en-CA"
DEFAULT_LANGUAGE = "en"
TEMPLATE_EXTENSION = ".md.j2"

_FRONT_MATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)

_ENV = Environment(
    autoescape=False,
    trim_blocks=False,
    lstrip_blocks=False,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "DEFAULT_LOCALE",
    "PromptLogEntry",
    "PromptMetadata",
    "PromptRender",
    "PromptResource",
    "inline_prompt_entry",
    "iter_prompt_specs",
    "load_prompt",
    "prompt_entry_from_render",
    "render_prompt",
    "render_prompt_with_meta",
    "run_cli",
]


class PromptMetadata(BaseModel):
    """Structured metadata describing prompt requirements."""

    version: str = "1"
    description: str | None = None
    required_placeholders: list[str] = Field(default_factory=list)
    allowed_placeholders: list[str] = Field(default_factory=list)

    @field_validator("version", mode="before")
    @classmethod
    def _coerce_version(cls, value: Any) -> str:
        if value is None:
            return "1"
        return str(value)

    @field_validator("required_placeholders", "allowed_placeholders", mode="before")
    @classmethod
    def _ensure_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            sequence = cast(Sequence[object], value)
            return [str(item) for item in sequence]
        return [str(value)]

    @model_validator(mode="after")
    def _normalize(self) -> "PromptMetadata":
        allowed = set(self.allowed_placeholders)
        if not allowed and self.required_placeholders:
            allowed.update(self.required_placeholders)
        allowed.update(self.required_placeholders)
        self.allowed_placeholders = sorted(allowed)
        missing = set(self.required_placeholders) - set(self.allowed_placeholders)
        if missing:
            readable = ", ".join(sorted(missing))
            raise ValueError(f"Required placeholders missing from allowed set: {readable}")
        return self


@dataclass(frozen=True)
class PromptResource:
    """Loaded prompt resource with compiled template and metadata."""

    domain: str
    key: str
    locale: str
    path: Path
    template: Template
    metadata: PromptMetadata
    sha256: str
    placeholders: tuple[str, ...]


@dataclass(frozen=True)
class PromptRender:
    """Rendered prompt content accompanied by resolved metadata."""

    text: str
    resource: PromptResource


@dataclass(frozen=True)
class PromptLogEntry:
    """Struct capturing prompt usage for ops logging."""

    domain: str
    key: str
    locale: str
    sha256: str
    role: str


def iter_prompt_specs() -> Iterator[tuple[str, str, str]]:
    """Yield ``(domain, locale, filename)`` for all prompt templates."""

    try:
        root = resources.files(RESOURCE_PACKAGE)
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise RuntimeError("Prompt resource package is not installed") from exc

    for domain_entry in root.iterdir():
        if not domain_entry.is_dir():
            continue
        domain = domain_entry.name
        for locale_entry in domain_entry.iterdir():
            if not locale_entry.is_dir():
                continue
            locale = locale_entry.name
            for template_entry in locale_entry.iterdir():
                if template_entry.is_file() and template_entry.name.endswith(TEMPLATE_EXTENSION):
                    yield domain, locale, template_entry.name


def _candidate_locales(locale: str) -> list[str]:
    candidates: list[str] = []
    normalized = locale or DEFAULT_LOCALE
    candidates.append(normalized)
    if "-" in normalized:
        language = normalized.split("-", 1)[0]
        if language not in candidates:
            candidates.append(language)
    if DEFAULT_LOCALE not in candidates:
        candidates.append(DEFAULT_LOCALE)
    default_language = DEFAULT_LOCALE.split("-", 1)[0]
    if default_language not in candidates:
        candidates.append(default_language)
    if DEFAULT_LANGUAGE not in candidates:
        candidates.append(DEFAULT_LANGUAGE)
    return candidates


def _split_front_matter(raw_text: str) -> tuple[dict[str, Any], str]:
    match = _FRONT_MATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text
    meta_raw = match.group(1)
    try:
        metadata_untyped = yaml.safe_load(meta_raw)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid YAML front matter: {exc}") from exc
    metadata_candidate: object = metadata_untyped if metadata_untyped is not None else {}
    if not isinstance(metadata_candidate, Mapping):
        raise ValueError("Prompt metadata must be a mapping")
    metadata_mapping = cast(Mapping[object, object], metadata_candidate)
    metadata_dict: dict[str, object] = {}
    for key_obj, value in metadata_mapping.items():
        metadata_dict[str(key_obj)] = value
    body = raw_text[match.end() :]
    return metadata_dict, body


def _compile_template(body: str) -> tuple[Template, tuple[str, ...]]:
    parsed = _ENV.parse(body)
    placeholders = tuple(sorted(meta.find_undeclared_variables(parsed)))
    template = _ENV.from_string(body)
    return template, placeholders


def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_prompt(domain: str, key: str, locale: str = DEFAULT_LOCALE) -> PromptResource:
    """Load and compile the template matching ``domain``/``key``/``locale``."""

    rel_name = f"{key}{TEMPLATE_EXTENSION}"
    try:
        base = resources.files(RESOURCE_PACKAGE)
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise RuntimeError("Prompt resource package is not installed") from exc

    for candidate_locale in _candidate_locales(locale):
        template_path = base.joinpath(domain, candidate_locale, rel_name)
        if not template_path.is_file():
            continue
        with resources.as_file(template_path) as fs_path:
            raw = _read_template(fs_path)
            metadata_raw, body = _split_front_matter(raw)
            template, placeholders = _compile_template(body)
            enriched_metadata = dict(metadata_raw)
            if not enriched_metadata.get("allowed_placeholders"):
                enriched_metadata["allowed_placeholders"] = list(placeholders)
            metadata = PromptMetadata.model_validate(enriched_metadata)
            unused_required = set(metadata.required_placeholders) - set(placeholders)
            if unused_required:
                readable = ", ".join(sorted(unused_required))
                raise ValueError(
                    f"Prompt '{domain}/{key}' declares unused required placeholders: {readable}"
                )
            if metadata.allowed_placeholders:
                disallowed = set(placeholders) - set(metadata.allowed_placeholders)
                if disallowed:
                    readable = ", ".join(sorted(disallowed))
                    raise ValueError(
                        f"Prompt '{domain}/{key}' uses disallowed placeholders: {readable}"
                    )
            digest = sha256(body.encode("utf-8")).hexdigest()
            return PromptResource(
                domain=domain,
                key=key,
                locale=candidate_locale,
                path=fs_path,
                template=template,
                metadata=metadata,
                sha256=digest,
                placeholders=placeholders,
            )

    candidates = ", ".join(_candidate_locales(locale))
    raise FileNotFoundError(
        f"No prompt template found for domain='{domain}', key='{key}', locales={candidates}"
    )


def _validate_context(metadata: PromptMetadata, context: Mapping[str, Any]) -> None:
    missing = [name for name in metadata.required_placeholders if context.get(name) is None]
    if missing:
        readable = ", ".join(sorted(missing))
        raise ValueError(f"Missing required prompt variables: {readable}")
    if metadata.allowed_placeholders:
        unexpected = [name for name in context if name not in metadata.allowed_placeholders]
        if unexpected:
            readable = ", ".join(sorted(unexpected))
            raise ValueError(f"Unexpected prompt variables provided: {readable}")


def render_prompt_with_meta(
    domain: str,
    key: str,
    context: Mapping[str, Any] | None = None,
    *,
    locale: str = DEFAULT_LOCALE,
    strip: bool = True,
) -> PromptRender:
    """Render a prompt and return both content and metadata."""

    resource = load_prompt(domain=domain, key=key, locale=locale)
    ctx: Mapping[str, Any] = context or {}
    _validate_context(resource.metadata, ctx)
    text = resource.template.render(**ctx)
    if strip:
        text = text.strip()
    return PromptRender(text=text, resource=resource)


def render_prompt(
    domain: str,
    key: str,
    context: Mapping[str, Any] | None = None,
    *,
    locale: str = DEFAULT_LOCALE,
    strip: bool = True,
) -> str:
    """Render a prompt and return the formatted string."""

    return render_prompt_with_meta(
        domain=domain,
        key=key,
        context=context,
        locale=locale,
        strip=strip,
    ).text


def prompt_entry_from_render(render: PromptRender, *, role: str) -> PromptLogEntry:
    return PromptLogEntry(
        domain=render.resource.domain,
        key=render.resource.key,
        locale=render.resource.locale,
        sha256=render.resource.sha256,
        role=role,
    )


def inline_prompt_entry(
    *,
    domain: str,
    key: str,
    locale: str,
    role: str,
    content: str,
) -> PromptLogEntry:
    digest = sha256(content.encode("utf-8")).hexdigest()
    return PromptLogEntry(domain=domain, key=key, locale=locale, sha256=digest, role=role)


def _lint_prompts() -> list[str]:
    errors: list[str] = []
    for domain, locale, filename in iter_prompt_specs():
        key = filename[: -len(TEMPLATE_EXTENSION)]
        try:
            resource = load_prompt(domain=domain, key=key, locale=locale)
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            errors.append(f"{domain}/{locale}/{filename}: {exc}")
            continue
        dummy_values: dict[str, Any] = {
            name: f"<{name}>" for name in resource.metadata.allowed_placeholders
        }
        try:
            resource.template.render(**dummy_values)
        except Exception as exc:  # pragma: no cover - render guard
            errors.append(f"{domain}/{locale}/{filename}: render failed ({exc})")
    return errors


def run_cli(argv: Iterable[str] | None = None) -> int:
    """Entry point for prompt tooling CLI."""

    import argparse

    parser = argparse.ArgumentParser(description="Prompt resource utilities.")
    sub = parser.add_subparsers(dest="command", required=True)

    lint_parser = sub.add_parser("lint", help="Validate all prompt templates.")
    lint_parser.set_defaults(command="lint")

    render_parser = sub.add_parser("render", help="Render a prompt to stdout.")
    render_parser.add_argument("domain", help="Prompt domain (e.g., analyze, compose).")
    render_parser.add_argument("key", help="Prompt key (e.g., system_summary).")
    render_parser.add_argument("--locale", default=DEFAULT_LOCALE, help="Locale to load.")
    render_parser.add_argument(
        "--vars",
        dest="vars_path",
        help="Path to JSON file providing prompt variables.",
    )
    render_parser.add_argument(
        "--no-strip",
        action="store_true",
        help="Preserve leading/trailing whitespace in rendered output.",
    )
    render_parser.set_defaults(command="render")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "lint":
        failures = _lint_prompts()
        if failures:
            for failure in failures:
                print(failure)
            return 1
        print("All prompt templates validated successfully.")
        return 0

    if args.command == "render":
        context: dict[str, Any] = {}
        if args.vars_path:
            with Path(args.vars_path).open("r", encoding="utf-8") as handle:
                context_obj = json.load(handle)
            if not isinstance(context_obj, Mapping):
                raise ValueError("Prompt variables JSON must be an object mapping.")
            context_mapping = cast(Mapping[object, object], context_obj)
            for key_obj, value_obj in context_mapping.items():
                if not isinstance(key_obj, str):
                    raise ValueError("Prompt variable keys must be text.")
                context[key_obj] = cast(Any, value_obj)
        output = render_prompt(
            args.domain,
            args.key,
            context=context,
            locale=args.locale,
            strip=not args.no_strip,
        )
        print(output)
        return 0

    raise RuntimeError(f"Unknown command: {args.command}")  # pragma: no cover - defensive


def main() -> None:  # pragma: no cover - thin CLI entry
    raise SystemExit(run_cli())


if __name__ == "__main__":  # pragma: no cover
    main()
