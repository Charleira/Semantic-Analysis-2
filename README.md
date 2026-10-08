# Projeto MicroC — Análise Semântica 2

Leia o [enunciado completo](ENUNCIADO.pdf) e consulte a especificação normativa
da MicroC. O enunciado define as interfaces, regras e critérios desta entrega.

Implemente inicialização definida e verificação do fim das funções sobre um
grafo de fluxo de controle (CFG) derivado da AST. A AST permanece como
representação principal do compilador. O CFG referencia seus nós e acrescenta
conexões de execução.

## Recupere o trabalho anterior

Copie os módulos Python e os pacotes auxiliares da entrega anterior para
**`previous/`**. Todo o trabalho anterior fica nessa pasta. Os arquivos já
fornecidos nela preservam os contratos e contêm placeholders para as passagens
que o grupo deve recuperar.

```text
starter/
├── previous/           ← lexer, parser, AST, símbolos e Semântica 1 do grupo
├── cfg.py              ← estruturas do grafo
├── cfg_builder.py      ← construção do CFG
├── reachability.py     ← alcance
├── initialization.py   ← ponto fixo
├── flow_checker.py     ← verificações de fluxo
├── flow_analysis.py    ← coordenação do fluxo
├── semantic.py         ← pipeline semântico completo
├── semantic_errors.py  ← diagnósticos atualizados
├── runner.py           ← execução
├── examples/
└── tests/
```

O carregador `load_previous.py` disponibiliza essa pasta automaticamente.
Não altere os imports antigos nem acrescente `previous.` a eles. Todas as
passagens devem compartilhar as mesmas classes da AST e dos símbolos.

Mantenha os contratos de tokens, AST e símbolos publicados anteriormente.
As versões antigas de `semantic.py`, `runner.py` e `semantic_errors.py` podem
acompanhar a cópia em `previous/`. A nova etapa usa as versões atualizadas da
raiz. Elas integram a passagem de fluxo e acrescentam as categorias
`UNINITIALIZED_READ` e `MISSING_RETURN`. As categorias anteriores mantêm seus
nomes e valores.

Antes de construir um CFG, a AST deve possuir os metadados `symbol`, `scope` e
`type`. Declarações e usos compartilham os mesmos objetos de símbolo.

## O que já está fornecido

| Módulo | Parte fornecida | Parte a completar |
|---|---|---|
| `cfg.py` | Blocos, terminadores, arestas, saídas e impressão textual | Estruturas auxiliares adicionais, se necessárias |
| `cfg_builder.py` | Criação do grafo e coordenação inicial em `build` | Percurso dos blocos, tratamento dos comandos, condicionais e laços |
| `reachability.py` | Lista de trabalho e verificação de visita anterior | Registro da visita e expansão dos sucessores |
| `initialization.py` | Estado por identidade de símbolo, fronteira de entrada e transferências locais | Interseção dos predecessores e iteração até ponto fixo |
| `flow_checker.py` | Percurso ordenado das operações e visitantes de expressões | Diagnósticos de leitura não inicializada e fim alcançável |
| `flow_analysis.py` e `semantic.py` | Coordenação das passagens e armazenamento de diagnósticos | Integração com as implementações do grupo |

Os pontos pendentes lançam `NotImplementedError`. Não os substitua por um
retorno vazio apenas para executar o pipeline. Uma análise ausente não deve
produzir uma confirmação de validade.

## Construção do CFG

`CFGBuilder.build(function)` devolve o grafo de uma função. `_build_block`
percorre um bloco da AST da AST. Ele devolve o ID de um bloco básico aberto
onde o fluxo pode continuar, ou `None` quando nenhum caminho continua.

Comandos sequenciais podem compartilhar o bloco básico atual. O grupo
implementa o percurso e decide como tratar cada tipo de comando.

`_build_block`, `_build_statement`, `_build_if` e `_build_while` contêm somente
assinaturas, orientações e `NotImplementedError`. O grupo completa esses métodos
e pode criar seus próprios auxiliares. Isso inclui comandos sequenciais,
blocos aninhados, saídas de escopo, retornos, condicionais e laços.

Um ramo que retorna não participa da junção. Sem `else`, o caminho falso
continua. Somente `while (true)` com o literal `true` é reconhecido como laço
sem saída normal. Não avalie outras condições como constantes, inclusive
condições de `if`.

Use `CFG.terminate` para fechar blocos e registrar suas arestas. Não edite
predecessores ou sucessores isoladamente. `Return` leva à saída por retorno.
`Jump` pode levar à saída pelo fim do corpo. `Stop` fecha as saídas artificiais
e não representa um comando MicroC.

`ScopeExit` marca a saída de um escopo no percurso normal. Ela não é um nó
sintático novo. O bloco pode conter comandos sequenciais e essas marcas em
`operations`. Condições e expressões de retorno ficam nos terminadores.

## Inicialização e retorno

A análise de inicialização é para frente e usa interseção nas junções.
Considere somente predecessores alcançáveis. Parâmetros entram inicializados.
Os demais estados começam por uma aproximação superior e são recalculados até
que nenhum conjunto mude. O universo fornecido contém os símbolos da função.
As transferências reiniciam declarações e descartam locais nas saídas de escopo.

O solver não emite diagnósticos. Depois da convergência, o verificador visita
cada bloco alcançável a partir de seu estado de entrada, na ordem dos comandos.
Assim, uma atribuição posterior não justifica uma leitura anterior. O destino
de uma atribuição é uma escrita. O lado direito é verificado antes da escrita.

O inicializador de uma declaração já referencia o novo símbolo. Em uma nova
execução de uma declaração local dentro de um laço, esse símbolo começa sem
valor garantido. A identidade dos símbolos distingue declarações de mesmo nome.

A verificação estática visita ambos os operandos de `&&` e `||`, inclusive
quando um literal permitiria pular o segundo durante a execução. A execução
MicroC mantém curto-circuito. Não há propagação de constantes nesta análise.

Uma função `int` ou `bool` é inválida se a saída pelo fim do corpo for
alcançável. Uma função `void` pode chegar a essa saída. Um caminho que diverge
em `while (true)` não precisa retornar. A passagem de fluxo não emite erros de
inicialização para operações inalcançáveis. Nomes e tipos continuam sendo
verificados sobre toda a AST antes desta passagem.

Use `SemanticDiagnostic` e armazene todos os erros antes de lançar `SemanticError`:

| Categoria | Coordenada relevante |
|---|---|
| `UNINITIALIZED_READ` | Início da ocorrência de `IdentifierExpr` lida |
| `MISSING_RETURN` | Início de `FunctionDecl` |

O texto das mensagens é escolha do grupo. Categorias e posições fazem
parte do contrato. Não duplique diagnósticos por causa das iterações do solver.

## Interfaces e liberdade de implementação

Preserve `SemanticAnalyzer.analyze(program)`, `CFGBuilder.build(function)` e
`compute_reachable(cfg)`. Em sucesso, `analyze` devolve o mesmo `Program`.
`check_flow(program)` retorna `None` em sucesso e lança `SemanticError` se
houver diagnósticos. Os nós mantêm seus vínculos e tipos anteriores.

Os resultados por função são armazenados em `FunctionDecl.metadata["cfg"]`
e `FunctionDecl.metadata["flow"]`. O segundo resultado expõe o CFG, o conjunto
de IDs alcançáveis e os estados `initialized_in` e `initialized_out` por bloco.
Os IDs são locais a cada grafo. Sua numeração e a quantidade de blocos auxiliares
não são resultados normativos da linguagem.

O grupo pode criar auxiliares, reorganizar os algoritmos e escolher uma lista
de trabalho diferente, preservando essas interfaces, os contratos das
estruturas fornecidas e o comportamento publicado. Não altere os nomes ou
campos da AST, dos símbolos ou dos diagnósticos. O parser continua responsável
pela sintaxe e pela construção da AST.

## Ambiente, execução e testes

O ambiente de referência é Python 3.12, com `pytest`.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python runner.py test.mc --cfg-only
python runner.py examples/branches.mc --cfg-only
python runner.py examples/loop.mc --cfg-only
python runner.py examples/integrated.mc --dump-cfg
python -m pytest -q
```

`--cfg-only` executa lexer, parser, nomes e tipos e mostra os grafos, sem
validar inicialização ou retorno ausente. A execução padrão valida todas as
passagens. `--dump-cfg` mostra os grafos após a validação completa.
As duas opções são alternativas e não podem ser usadas juntas.

O runner termina com status 0 para sucesso no modo solicitado, 1 para erro
léxico, sintático ou semântico, 2 para erro de uso ou leitura e 3 para um ponto
do scaffold ainda não implementado.

Comece por `tests/test_infrastructure.py`, que verifica partes já fornecidas.
Os testes de `tests/test_cfg.py` e `tests/test_flow.py` descrevem os resultados
esperados da implementação completa. Eles falham enquanto houver métodos
pendentes ou implementações anteriores ainda não recuperadas. Não marque os
testes como ignorados para obter um resultado positivo no GitHub Actions.

Consulte a especificação MicroC, §§ 5.3, 6.4, 7.5 e 8.3, e a Aula 9,
pp. 4–16 e 34–57. A Aula 7, pp. 26 e 33–34, retoma visibilidade, shadowing e
o próprio inicializador.
