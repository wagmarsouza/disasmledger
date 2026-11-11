# Decompile 2.0 — reconstrução qualificada + Control 8.4

Extensão opcional, sem trocar as APIs anteriores de closure, proveniência, scheduler, adapter8.2
ou barras declaradas. As regras abaixo são o gate adicional de contagem qualificada, não uma
reescrita das classificações históricas. G4-stock e G4-recon continuam separados.

## Instalação e execução

Nada é instalado por estes arquivos. Helpers antigos usam biblioteca padrão. O novo gate AST
necessita pycparser (requirements-verified.txt), Python3.11+ e ferramentas externas autorizadas.
O pacote completo inclui as skills irmãs; o ZIP individual inclui uma cópia de distribuição
byte-idêntica do helper canônico binary_profile.py em scripts/vendor. Ela não é um novo motor
de identidade nem instala binary-analysis-profile. Atualize sempre a partir da fonte canônica.
Não há comando /skill universal. Para uma sessão peça ao agente para ler SKILL.md no caminho
extraído; instalação permanente é uma ação separada a autorizar.

```powershell
python -B C:/Pacotes/decompile/scripts/completion.py --help
python -B C:/Pacotes/decompile/examples/run_measurement_pilot.py --harness C:/Pacotes/harness_v8.4/scripts/harness.py
python -B C:/Pacotes/decompile/scripts/census_bars.py --project C:/Trabalho/Projeto --callgraph analysis/callgraph.json --grades analysis/grades.json --harness C:/Pacotes/harness_v8.4/scripts/harness.py --ascii
```

O piloto cria um projeto descartável e ferramentas sintéticas; não adota configurações reais.
No Linux acrescente `--compiler /usr/bin/gcc` para compilar/executar processos reais de um caso
C pequeno. Isto não é teste ARM/Renode/firmware. O código do piloto mostra o contrato completo;
os fixtures são deliberadamente sintéticos e não devem ser usados como verificadores de produção.

## Gates de domínio (todos obrigatórios)

1. representation: fonte C compatível com pycparser, símbolo único, qualificação vinculada ao hash,
   revisor aprovado e dependências completas. AST registra sinais de transliteração, goto,
   registradores, condições constantes e chamadas; não mede legibilidade automaticamente.
   Fonte linear legítima é aceita. `if` decorativo ou ausência de goto não prova reconstrução.
   Descriptor, machine-transliteration e hybrid não qualificam como structured-source.
2. compilation: preprocessamento e compilação reais por argv pinado, imagens novas e fonte/headers
   vinculados. Compilar outro arquivo ou usar imagem antiga falha. Inclua headers/linker/scripts
   em build_inputs; o verificador não descobre universalmente dependências omitidas.
3. behavior: observações diferenciais stock/candidate e estados de saída por testemunha, reset,
   IDs completos e run novo. Compilar ou round-trip de bytes sozinho não basta. Timeout,
   testemunha omitida e todos os casos terminando em fault não passam como equivalência.
4. independence: recibo liga a execução à imagem candidata efetivamente compilada. Origem
   original/unknown é rejeitada. Plataformas/ROMs permitidas precisam de imagens explicitamente
   aprovadas. Endereços MMIO/dados não são proibidos por regex; fluxo/chamadas são a questão.
5. controls: stock-v-stock saudável e candidato conhecido incorreto que realmente diverge.
   Controle que não distingue o defeito reprova. A e M usam a mesma cadeia de recibos físicos.

## Configuração e autoridade

Configure `disasm-completion-config-v1` com target/universe {path,sha256}, callgraph,
work_pattern:'completion/{run}', budget_seconds, tool_timeout_seconds, profile, tools e units.
O template em assets/templates é ilustrativo e inválido até preencher identidades/hashes reais.
O target e cada unit_manifest usam binary-analysis-profile; a identidade do universo é seu digest,
não um novo número inventado. Aliases da mesma entrada física não somam unidades distintas.
O grafo, as dependências e exclusões devem coincidir com o universo aprovado do harness.

profile contém reviewers (identificadores aprovados), execution_kind (`pc-trace` ou `process-image`),
platform_images com caminho/hash e allowed_external_calls. Revisor é declaração aprovada,
não identidade humana autenticada; revisão independente confiável precisa ser organizada pelo
operador. A AST é um auxiliar de revisão e não impede um revisor hostil de aprovar fonte ruim.

tools.compiler contém argv/preprocess_argv/executable_sha256/files; executor contém
argv/executable_sha256/files. files fixa os recursos/scripts de cada ferramenta. Placeholders
de compilação: {source},{output}; de execução: {stock},{image},{witnesses},{report},{unit},{entry},{run}.
As ferramentas são explícitas e confiáveis, não shell livre. O executor é externo: implemente
o formato de observação para sua arquitetura/bench; nenhum backend universal é prometido.

Cada unidade fornece unit_manifest, symbol, qualification, witnesses, negative_source e build_inputs.
Qualificação `disasm-source-qualification-v1` contém unit/source_sha256/representation/reviewer,
dependencies_complete/dependencies/acknowledged_signals/indirect_resolutions,
build_inputs_sha256 (digest canônico path→hash) e callgraph_sha256. Resoluções indiretas precisam
de targets e evidência física. Testemunhas `disasm-witnesses-v1` contêm pelo menos dois inputs
distintos com id e purpose. Alvos/platformas e controle negativo precisam de revisão apropriada.

O executor emite `disasm-execution-v1`: unit/entry/run_id, image/stock/witnesses {path,sha256},
complete e cases. Cada case traz id/stock/candidate/stock_status/candidate_status/reset/execution;
cada execution registra role/image/pc. `pc-trace` exige PC, `process-image` é apenas proveniência
de processo. Receipts verificam bindings/consistência; não autenticam um executor que inventa log.

No harness adote measurement_policy com gates representation/compilation/behavior/independence/
controls. Configure M e A para `python .../completion.py --project RAIZ --config config.json`.
Pine config/tools/corpus e use pinned_roles witnesses/negative_source/verifier_context para
impedir rebaseline silencioso após o primeiro fechamento. As entradas do projeto devem cobrir
fontes, reviews, testemunhas, headers, unit/target/universe/grafo/config e binário original.
Mudança governante exige revisão explícita de missão. Não escreva state.yaml nem grades para
promover a unidade. O produtor recebe run/context/output/previous/selection do próprio motor.

## Auditoria, cache e barras

M reconta o conjunto integral, revalida provas reutilizadas e só reexecuta o necessário; cache
não é execução nova. A reconta tudo, força execução das unidades congeladas e controles.
Falha do audit mantém hold no harness e obriga recuperação integral. Não confunda recontagem
integral com reexecução integral. Sem fonte/review/prova válida a unidade fica não qualificada.

As barras sem --harness mantêm comportamento histórico, explicitamente declarado. Com --harness
consultam measurement-report vivo; recusa/timeout/inventário ou grafo conflitante falham sem
fallback. Exibem declarado, comprovado atual, pendente e desatualizado; os três últimos particionam
o denominador vivo. Declarado é sobreposto, não deve ser somado aos demais. G0 só reduz o universo
por exclusão aprovada, não por edição oportunista de grades. Nenhuma barra promove nada.

## Limites

Pycparser suporta um subconjunto C após preprocessamento, não C++/todas as extensões GCC.
Testemunhas finitas, hash e fonte estruturada não provam equivalência universal. Verificação
de firmware real precisa de toolchain, runner confiável, rastros e corpus próprios. Não confunda
o piloto host C com essa validação. As declarações de revisão e completude de entradas são
fronteiras de confiança. Ferramentas fora da CLI e logs falsificados por um verificador confiado
não são fiscalizados magicamente. Toda conclusão deve declarar corpus, contexto e teto da prova.
