"""Minimal XLSX reader for pinned connectome adjacency workbooks.

Adapted from vdmkenny/celeganssim (MIT), scripts/xlsx.py.
Copyright (c) 2026 Kenny Van de Maele.

This is intentionally not a general spreadsheet parser. It supports the shared
strings, inline strings, numeric cells, and sparse rows used by the Cook/Witvliet
connectome workbooks.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}
CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")


def _col_index(ref: str) -> int:
    match = CELL_REF.match(ref)
    letters = match.group(1) if match else ref
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - 64)
    return value - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]


def _sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    relationships: dict[str, str] = {}
    root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in root.findall("p:Relationship", NS):
        relationships[rel.get("Id")] = rel.get("Target")
    out: dict[str, str] = {}
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    for sheet in workbook.iter(f"{{{NS['m']}}}sheet"):
        target = relationships.get(sheet.get(f"{{{NS['r']}}}id"), "")
        if target.startswith("/"):
            target = target[1:]
        elif not target.startswith("xl/"):
            target = "xl/" + target
        out[sheet.get("name")] = target
    return out


def sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return list(_sheet_paths(zf))


def read_sheet(path: Path, name: str) -> list[list]:
    with zipfile.ZipFile(path) as zf:
        paths = _sheet_paths(zf)
        if name not in paths:
            raise KeyError(f"no sheet {name!r}; have {list(paths)}")
        strings = _shared_strings(zf)
        root = ET.fromstring(zf.read(paths[name]))

    rows: list[dict[int, object]] = []
    width = 0
    for row in root.iter(f"{{{NS['m']}}}row"):
        cells: dict[int, object] = {}
        for cell in row.findall("m:c", NS):
            ref, typ = cell.get("r", ""), cell.get("t")
            value_node = cell.find("m:v", NS)
            if typ == "s":
                if value_node is None or value_node.text is None:
                    continue
                value = strings[int(value_node.text)]
            elif typ == "inlineStr":
                inline = cell.find("m:is", NS)
                value = "".join(t.text or "" for t in inline.iter(f"{{{NS['m']}}}t")) if inline is not None else None
            elif value_node is None or value_node.text is None:
                continue
            else:
                try:
                    value = float(value_node.text)
                except ValueError:
                    value = value_node.text
            if value is None or value == "":
                continue
            index = _col_index(ref)
            cells[index] = value
            width = max(width, index + 1)
        row_index = int(row.get("r", len(rows) + 1)) - 1
        while len(rows) < row_index:
            rows.append({})
        rows.append(cells)

    return [[row.get(index) for index in range(width)] for row in rows]
