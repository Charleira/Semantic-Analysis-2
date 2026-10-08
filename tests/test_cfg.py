from __future__ import annotations

from ast_nodes import (Block, FunctionDecl, IdentifierExpr, IntLiteral, PrintStmt, ReturnStmt, SourceSpan, TypeName, VarDecl)
from cfg import Branch, Return, ScopeExit
from cfg_builder import CFGBuilder
from reachability import compute_reachable
from symbols import Scope


def reachable_from(cfg, start):
    seen = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(cfg.blocks[current].successors)
    return seen


def test_if_com_dois_retornos_nao_alcanca_o_fim(parse_annotated):
    program = parse_annotated(
        "int main() { if (true) { return 1; } else { return 2; } }"
    )
    fn = program.functions[0]
    cfg = CFGBuilder().build(fn)
    reachable = compute_reachable(cfg)
    assert cfg.return_exit in reachable
    assert cfg.fallthrough_exit not in reachable
    branches = [b.terminator for b in cfg.blocks.values() if isinstance(b.terminator, Branch)]
    assert any(t.condition is fn.body.statements[0].condition for t in branches)


def test_if_sem_else_preserva_caminho_falso(parse_annotated):
    program = parse_annotated("int main() { if (true) { return 1; } }")
    cfg = CFGBuilder().build(program.functions[0])
    reachable = compute_reachable(cfg)
    assert cfg.return_exit in reachable
    assert cfg.fallthrough_exit in reachable


def test_while_com_condicao_de_parametro_tem_ciclo_e_saida(parse_annotated):
    program = parse_annotated(
        "void f(bool b) { while (b) { print(1); } } int main() { return 0; }"
    )
    cfg = CFGBuilder().build(program.functions[0])
    reachable = compute_reachable(cfg)
    assert cfg.fallthrough_exit in reachable
    test_blocks = [
        b for b in cfg.blocks.values()
        if isinstance(b.terminator, Branch)
        and isinstance(b.terminator.condition, IdentifierExpr)
    ]
    assert test_blocks
    # Verifique os caminhos, sem exigir uma quantidade de blocos auxiliares
    # ou que o corpo termine com uma aresta direta para o teste.
    assert any(
        b.id in reachable_from(cfg, b.terminator.true_target)
        and cfg.fallthrough_exit in reachable_from(cfg, b.terminator.false_target)
        for b in test_blocks
    )


def test_while_true_nao_alcanca_operacoes_posteriores(parse_annotated):
    program = parse_annotated("int main() { while (true) {} print(42); }")
    cfg = CFGBuilder().build(program.functions[0])
    reachable = compute_reachable(cfg)
    assert cfg.fallthrough_exit not in reachable
    later = program.functions[0].body.statements[1]
    assert not any(
        op is later for bid in reachable for op in cfg.blocks[bid].operations
    )


def test_bloco_aninhado_preserva_saida_de_escopo(parse_annotated):
    program = parse_annotated("int main() { { int x = 1; print(x); } return 0; }")
    nested = program.functions[0].body.statements[0]
    cfg = CFGBuilder().build(program.functions[0])
    assert any(
        isinstance(op, ScopeExit) and op.scope is nested.metadata["scope"]
        for block in cfg.blocks.values() for op in block.operations
    )
    assert any(isinstance(b.terminator, Return) for b in cfg.blocks.values())


SPAN = SourceSpan(1, 1, 1, 2)

def function(statements, return_type=TypeName.INT):
    body = Block(span=SPAN, statements=statements)
    body.metadata["scope"] = Scope(parent=None)
    return FunctionDecl(span=SPAN, name="main", return_type=return_type, parameters=[], body=body)


def test_sequencia_preserva_ast_e_retorno_impede_operacoes_posteriores():
    declaration = VarDecl(span=SPAN, type=TypeName.INT, name="x", initializer=None)
    returned = ReturnStmt(span=SPAN, value=IntLiteral(span=SPAN, value=0))
    unreachable = PrintStmt(span=SPAN, items=[IntLiteral(span=SPAN, value=42)])
    fn = function([declaration, returned, unreachable])
    cfg = CFGBuilder().build(fn)
    operations = [op for block in cfg.blocks.values() for op in block.operations]
    assert any(op is declaration for op in operations)
    assert not any(op is unreachable for op in operations)
    return_blocks = [b for b in cfg.blocks.values() if isinstance(b.terminator, Return)]
    assert len(return_blocks) == 1
    assert return_blocks[0].terminator.statement is returned
    assert return_blocks[0].successors == {cfg.return_exit}
    assert not cfg.blocks[cfg.fallthrough_exit].predecessors


def test_bloco_void_vazio_preserva_fronteira_e_chega_ao_fim():
    fn = function([], TypeName.VOID)
    cfg = CFGBuilder().build(fn)
    exits = [op for b in cfg.blocks.values() for op in b.operations if isinstance(op, ScopeExit)]
    assert len(exits) == 1
    assert exits[0].scope is fn.body.metadata["scope"]
    assert cfg.blocks[cfg.fallthrough_exit].predecessors

