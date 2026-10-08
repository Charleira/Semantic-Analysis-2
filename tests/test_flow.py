from __future__ import annotations

import dataclasses
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from ast_nodes import Node, ast_to_dict
from flow_analysis import FlowAnalyzer
from semantic import SemanticAnalyzer
from semantic_errors import SemanticError, SemanticErrorKind
from conftest import IMPLEMENTATION_ROOT, STARTER_ROOT


CASES = Path(__file__).parent / "cases"


@pytest.mark.parametrize("name", [
    "parameters", "returning_branch", "both_return", "void_fallthrough",
    "infinite_loop", "unreachable",
])
def test_programas_validos(name, parse_annotated):
    program = parse_annotated((CASES / "valid" / f"{name}.mc").read_text())
    assert SemanticAnalyzer().analyze(program) is program


@pytest.mark.parametrize("name,line,column", [
    ("uninitialized_read", 3, 11),
    ("self_initializer", 2, 13),
    ("one_branch", 7, 11),
    ("loop_only", 8, 11),
    ("loop_local", 5, 15),
    ("shadowing", 7, 11),
    ("shadow_initializer", 4, 17),
    ("short_circuit", 3, 20),
    ("assignment_reads", 3, 9),
    ("return_reads", 3, 12),
    ("call_argument", 7, 13),
    ("condition_reads", 3, 9),
])
def test_leituras_invalidas_possuem_categoria_e_posicao(name, line, column, parse_annotated):
    program = parse_annotated((CASES / "invalid" / f"{name}.mc").read_text())
    with pytest.raises(SemanticError) as caught:
        FlowAnalyzer().analyze(program)
    actual = Counter((d.kind, d.line, d.column) for d in caught.value.diagnostics)
    assert actual == Counter([(SemanticErrorKind.UNINITIALIZED_READ, line, column)])


@pytest.mark.parametrize("name", ["missing_return", "partial_return", "nonliteral_loop"])
def test_fim_alcancavel_de_main_possui_diagnostico(name, parse_annotated):
    program = parse_annotated((CASES / "invalid" / f"{name}.mc").read_text())
    with pytest.raises(SemanticError) as caught:
        FlowAnalyzer().analyze(program)
    assert Counter((d.kind, d.line, d.column) for d in caught.value.diagnostics) == Counter([
        (SemanticErrorKind.MISSING_RETURN, 1, 1),
    ])


def descendants(node):
    yield node
    for field in dataclasses.fields(node):
        if field.name == "metadata":
            continue
        value = getattr(node, field.name)
        if isinstance(value, Node):
            yield from descendants(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Node):
                    yield from descendants(item)


def test_integracao_preserva_sintaxe_vinculos_e_tipos(parse_annotated):
    program = parse_annotated((STARTER_ROOT / "examples/integrated.mc").read_text())
    syntax = ast_to_dict(program)
    original_metadata = [
        (node, dict(node.metadata)) for node in descendants(program)
    ]
    analyzer = FlowAnalyzer()
    assert analyzer.analyze(program) is program
    assert ast_to_dict(program) == syntax
    for node, metadata in original_metadata:
        for key, value in metadata.items():
            assert node.metadata[key] is value
    for function in program.functions:
        facts = analyzer.functions[function.name]
        assert function.metadata["cfg"] is facts.cfg
        assert function.metadata["flow"] is facts
        assert facts.cfg.function is function
        assert facts.cfg.entry in facts.reachable
        assert set(facts.initialization.initialized_in) == facts.reachable
        assert set(facts.initialization.initialized_out) == facts.reachable


def test_erros_de_fluxo_sao_armazenados_sem_duplicacao(parse_annotated):
    program = parse_annotated(
        "int main() {\n"
        "    int x;\n"
        "    print(x, x);\n"
        "}\n"
    )
    with pytest.raises(SemanticError) as caught:
        FlowAnalyzer().analyze(program)
    assert Counter((d.kind, d.line, d.column) for d in caught.value.diagnostics) == Counter([
        (SemanticErrorKind.UNINITIALIZED_READ, 3, 11),
        (SemanticErrorKind.UNINITIALIZED_READ, 3, 14),
        (SemanticErrorKind.MISSING_RETURN, 1, 1),
    ])


def test_runner_valida_fluxo_e_modo_cfg_only_e_explicito():
    source = CASES / "invalid/uninitialized_read.mc"
    command = [sys.executable, "-B", str(IMPLEMENTATION_ROOT / "runner.py"), str(source)]
    result = subprocess.run(command, capture_output=True, text=True, cwd=IMPLEMENTATION_ROOT)
    assert result.returncode == 1
    assert "uninitialized_read" in result.stderr
    assert "3:11" in result.stderr
    assert not result.stdout
    result = subprocess.run(command + ["--cfg-only"], capture_output=True, text=True, cwd=IMPLEMENTATION_ROOT)
    assert result.returncode == 0
    assert "A análise de fluxo não foi executada" in result.stdout
    assert not result.stderr
