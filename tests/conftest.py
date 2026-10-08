from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


STARTER_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_ROOT = Path(
    os.environ.get("MICROC_SEMANTIC_DIR", STARTER_ROOT)
).resolve()
sys.path.insert(0, str(IMPLEMENTATION_ROOT))

import load_previous  # noqa: E402


@pytest.fixture
def parse_annotated():
    from Lexer import Lexer
    from name_resolver import resolve_names
    from parser import Parser
    from type_checker import check_types

    def parse(source: str):
        program = Parser(Lexer(source).scan()).parse()
        resolve_names(program)
        check_types(program)
        return program

    return parse
