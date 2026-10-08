from __future__ import annotations

import pytest

import semantic
from ast_nodes import (
    Assignment, Block, BoolLiteral, FunctionDecl, IdentifierExpr, IntLiteral,
    PrintStmt, Program, ReturnStmt, SourceSpan, TypeName, VarDecl,
)
from cfg import Branch, CFG, Jump, Return, ScopeExit, Stop
from initialization import transfer
from semantic_errors import SemanticDiagnostic, SemanticError, SemanticErrorKind
from symbols import Scope, Symbol, SymbolKind


SPAN = SourceSpan(1, 1, 1, 2)


def function(statements, return_type=TypeName.INT):
    body = Block(span=SPAN, statements=statements)
    body.metadata["scope"] = Scope(parent=None)
    return FunctionDecl(
        span=SPAN, name="main", return_type=return_type, parameters=[], body=body,
    )


def test_arestas_de_ramificacao_e_retorno_sao_reciprocas():
    cfg = CFG(function([]))
    left, right = cfg.new_block(), cfg.new_block()
    cfg.terminate(cfg.entry, Branch(BoolLiteral(span=SPAN, value=True), left.id, right.id))
    returned = ReturnStmt(span=SPAN, value=IntLiteral(span=SPAN, value=1))
    cfg.terminate(left.id, Return(returned))
    cfg.terminate(right.id, Jump(cfg.fallthrough_exit))
    for block in cfg.blocks.values():
        for successor in block.successors:
            assert block.id in cfg.blocks[successor].predecessors
        for predecessor in block.predecessors:
            assert block.id in cfg.blocks[predecessor].successors
    assert isinstance(cfg.blocks[cfg.return_exit].terminator, Stop)
    assert not cfg.blocks[cfg.return_exit].successors
    assert not cfg.blocks[cfg.fallthrough_exit].successors


def test_destino_invalido_nao_deixa_uma_ramificacao_parcial():
    cfg = CFG(function([]))
    condition = BoolLiteral(span=SPAN, value=True)
    with pytest.raises(ValueError):
        cfg.terminate(cfg.entry, Branch(condition, cfg.return_exit, 9999))
    assert cfg.blocks[cfg.entry].terminator is None
    assert not cfg.blocks[cfg.entry].successors
    assert not cfg.blocks[cfg.return_exit].predecessors






def test_transferencia_distingue_shadowing_e_reinicia_declaracao_local():
    outer_decl = VarDecl(span=SPAN, type=TypeName.INT, name="x", initializer=None)
    inner_decl = VarDecl(span=SPAN, type=TypeName.INT, name="x", initializer=None)
    outer = Symbol("x", SymbolKind.VARIABLE, TypeName.INT, outer_decl)
    inner = Symbol("x", SymbolKind.VARIABLE, TypeName.INT, inner_decl)
    inner_decl.metadata["symbol"] = inner
    target = IdentifierExpr(span=SPAN, name="x")
    target.metadata["symbol"] = outer
    inner_scope = Scope(parent=None, symbols={"x": inner})
    cfg = CFG(function([]))
    block = cfg.new_block()
    incoming = {inner}
    block.operations = [inner_decl]
    assert transfer(block, incoming) == set()
    block.operations = [
        inner_decl,
        Assignment(span=SPAN, target=target, value=IntLiteral(span=SPAN, value=1)),
        ScopeExit(inner_scope),
    ]
    assert transfer(block, incoming) == {outer}
    assert incoming == {inner}


@pytest.mark.parametrize("failed_pass", ["resolve_names", "check_types"])
def test_erros_anteriores_impedem_a_passagem_de_fluxo(monkeypatch, failed_pass):
    calls = []
    diagnostic = SemanticDiagnostic(SemanticErrorKind.INVALID_MAIN, "teste", SPAN)

    def names(program):
        calls.append("resolve_names")
        if failed_pass == "resolve_names":
            raise SemanticError([diagnostic])

    def types(program):
        calls.append("check_types")
        if failed_pass == "check_types":
            raise SemanticError([diagnostic])

    def flow(program):
        calls.append("check_flow")

    monkeypatch.setattr(semantic, "resolve_names", names)
    monkeypatch.setattr(semantic, "check_types", types)
    monkeypatch.setattr(semantic, "check_flow", flow)
    with pytest.raises(SemanticError):
        semantic.SemanticAnalyzer().analyze(Program(span=SPAN, functions=[]))
    assert "check_flow" not in calls
    if failed_pass == "resolve_names":
        assert calls == ["resolve_names"]
    else:
        assert calls == ["resolve_names", "check_types"]
