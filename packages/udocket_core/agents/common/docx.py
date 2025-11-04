# pyright: strict

"""Minimal helpers for writing DOCX files without heavy dependencies."""

from __future__ import annotations

import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from xml.sax.saxutils import escape

from packages.udocket_common.time import format_utc

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>
"""


_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>
"""


_CORE_PROPS_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:creator>uDocket Compose Agent</dc:creator>
  <cp:lastModifiedBy>uDocket Compose Agent</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>
  <cp:revision>1</cp:revision>
</cp:coreProperties>
"""


def _paragraph_xml(text: str) -> str:
    safe = escape(text).replace("\n", "<w:br />")
    return '<w:p><w:r><w:t xml:space="preserve">' + safe + "</w:t></w:r></w:p>"


def _document_xml(paragraphs: Sequence[str]) -> str:
    content = paragraphs or ("",)
    body = "".join(_paragraph_xml(paragraph) for paragraph in content)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body>"
        "</w:document>"
    )


def write_basic_docx(
    *,
    paragraphs: Iterable[str],
    output_path: Path,
    title: str = "Compose Deliverable",
) -> Path:
    """Write a minimal DOCX file with the provided paragraphs."""

    para_list = [str(paragraph or "").strip("\r") for paragraph in paragraphs]
    timestamp = format_utc(timespec="seconds")
    core_props = _CORE_PROPS_TEMPLATE.format(
        title=escape(title),
        created=timestamp,
        modified=timestamp,
    )
    document_xml = _document_xml(para_list)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("docProps/core.xml", core_props)
        archive.writestr("word/document.xml", document_xml)
    return output_path


__all__ = ["write_basic_docx"]
