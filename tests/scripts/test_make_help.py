from __future__ import annotations

from pathlib import Path

import pytest
from _pytest.capture import CaptureFixture

from scripts import make_help

SAMPLE_MAKEFILE = """\
HELP_GROUP_FORMAT := "\\nGROUP:%s\\n"
HELP_CMD_FORMAT := " CMD:%s|%s\\n"

##@ Tests
pytest.all: ## Run tests
pytest.verbose: ## Run tests loudly

##@ Other Cache Cleaning
clean.coverage: ## Remove coverage artifacts
clean.tmp: ## Remove residual caches

##@ Docker Basics
docker.prune: ## Prune Docker resources
docker.reset: ## Reset Docker resources

##@ Docker Buildx
buildx.du: ## Inspect Buildx cache usage
buildx.prune: ## Prune Buildx caches

##@ Empty Section
"""


@pytest.fixture(name="sample_makefile_path")
def fixture_sample_makefile_path(tmp_path: Path) -> Path:
    path = tmp_path / "Makefile"
    path.write_text(SAMPLE_MAKEFILE, encoding="utf-8")
    return path


@pytest.fixture(name="sample_lines")
def fixture_sample_lines(sample_makefile_path: Path) -> list[str]:
    return sample_makefile_path.read_text(encoding="utf-8").splitlines()


def test_decode_from_make(sample_lines: list[str]) -> None:
    assert make_help.decode_from_make(sample_lines, "HELP_GROUP_FORMAT") == "\nGROUP:%s\n"
    assert make_help.decode_from_make(sample_lines, "HELP_CMD_FORMAT") == " CMD:%s|%s\n"


def test_decode_from_make_missing(sample_lines: list[str]) -> None:
    with pytest.raises(SystemExit, match="Missing definition"):
        make_help.decode_from_make(sample_lines, "UNKNOWN")


def test_collect_sections_and_commands(sample_lines: list[str]) -> None:
    sections, commands = make_help.collect_sections(sample_lines)
    assert sections == [
        ("tests", "Tests"),
        ("other.cache.cleaning", "Other Cache Cleaning"),
        ("docker.basics", "Docker Basics"),
        ("docker.buildx", "Docker Buildx"),
        ("empty.section", "Empty Section"),
    ]
    assert commands["docker.basics"] == [
        ("docker.prune", "Prune Docker resources"),
        ("docker.reset", "Reset Docker resources"),
    ]
    assert commands["other.cache.cleaning"][0][0] == "clean.coverage"


def test_select_sections_variants(sample_lines: list[str]) -> None:
    sections, _ = make_help.collect_sections(sample_lines)
    assert make_help.select_sections(sections, "docker") == [
        ("docker.basics", "Docker Basics"),
        ("docker.buildx", "Docker Buildx"),
    ]
    assert make_help.select_sections(sections, "docker.buildx") == [
        ("docker.buildx", "Docker Buildx")
    ]
    assert make_help.select_sections(sections, "docker.buildx.detail") == [
        ("docker.buildx", "Docker Buildx")
    ]


def test_select_commands_filters_by_prefix(sample_lines: list[str]) -> None:
    sections, commands = make_help.collect_sections(sample_lines)
    matches = make_help.select_commands(sections, commands, "clean")
    assert matches == [
        (
            "other.cache.cleaning",
            "Other Cache Cleaning",
            [
                ("clean.coverage", "Remove coverage artifacts"),
                ("clean.tmp", "Remove residual caches"),
            ],
        )
    ]


def test_render_help_for_section(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.render_help("docker", sample_makefile_path)
    assert result == 0
    output = capsys.readouterr().out
    assert "\nGROUP:Docker Basics\n" in output
    assert " CMD:docker.prune|Prune Docker resources" in output
    assert "\nGROUP:Docker Buildx\n" in output


def test_render_help_for_command_prefix(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.render_help("clean", sample_makefile_path)
    assert result == 0
    output = capsys.readouterr().out
    assert "\nGROUP:Other Cache Cleaning\n" in output
    assert " CMD:clean.coverage|Remove coverage artifacts" in output
    assert " CMD:clean.tmp|Remove residual caches" in output


def test_render_help_for_single_command(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.render_help("clean.coverage", sample_makefile_path)
    assert result == 0
    output = capsys.readouterr().out
    assert output.count("clean.coverage") == 1
    assert "clean.tmp" not in output


def test_render_help_no_commands(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.render_help("empty", sample_makefile_path)
    assert result == 0
    output = capsys.readouterr().out
    assert "\nGROUP:Empty Section\n" in output
    assert "no commands with help descriptions" in output


def test_render_help_unknown_group(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.render_help("missing", sample_makefile_path)
    assert result == 1
    output = capsys.readouterr().out
    assert "Unknown help group: missing" in output


def test_main_success(sample_makefile_path: Path, capsys: CaptureFixture[str]) -> None:
    result = make_help.main(["docker", str(sample_makefile_path)])
    assert result == 0
    assert "GROUP:Docker" in capsys.readouterr().out


def test_main_missing_makefile(tmp_path: Path) -> None:
    missing_path = tmp_path / "MissingMakefile"
    with pytest.raises(SystemExit, match="Makefile not found"):
        make_help.main(["docker", str(missing_path)])
