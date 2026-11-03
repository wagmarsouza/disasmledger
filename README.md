# DisasmLedger

![DisasmLedger: bytes e rastros com evidência](assets/disasmledger-logo.png)

Skills para análise binária e bancadas de firmware com rastreabilidade. O projeto reúne duas skills independentes: `binary-analysis-profile` organiza identidade, mapa de endereços, unidades e testemunhos; `renode-bench` orienta uma bancada Renode e a leitura de traces de program counter. Podem ser usadas separadamente ou em conjunto.

## Instalação

Com Node.js e o [Skills CLI](https://skills.sh/):

```powershell
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
```

Para clonar e usar os scripts sem um agente:

```powershell
git clone https://github.com/wagmarsouza/disasmledger.git
cd disasmledger
python -B -m unittest discover -s skills/binary-analysis-profile/tests -v
python -B -m unittest discover -s skills/renode-bench/tests -v
```

## Binary Analysis Profile

Leia [a skill](skills/binary-analysis-profile/SKILL.md) e os modelos em `skills/binary-analysis-profile/assets/templates/`. Os manifestos são preenchidos com dados do seu alvo; os exemplos incluídos são sintéticos.

```powershell
$b = '.\skills\binary-analysis-profile\scripts\binary_profile.py'
$p = 'C:\seu-projeto'
python -B $b --project $p inspect --binary 'evidence\image.bin'
python -B $b --project $p target --input "$p\analysis\target.json"
python -B $b --project $p unit --target "$p\analysis\target.json" --input "$p\analysis\unit.json"
python -B $b --project $p witnesses --target "$p\analysis\target.json" --unit "$p\analysis\unit.json" --input "$p\analysis\witnesses.json"
```

O auxiliar confere a consistência declarada e o vínculo com arquivos. Ele não desassembla o binário, identifica a arquitetura, autentica logs ou estabelece verdade semântica. O [piloto sintético](skills/binary-analysis-profile/examples/run_pilot.py) permite verificar o fluxo sem firmware real:

```powershell
python -B skills/binary-analysis-profile/examples/run_pilot.py
```

## Renode Bench

Leia [a skill](skills/renode-bench/SKILL.md) e [as instruções de uso](skills/renode-bench/references/usage.md). Renode é uma dependência externa. Copie `boot-trace.resc` para o projeto, substitua e revise cada marcador de plataforma, endereço e firmware antes de executar.

```powershell
$renode = 'C:\Program Files\Renode\bin\Renode.exe'
$bench = 'C:\seu-projeto\bench\boot-trace.resc'
& $renode --disable-gui --console $bench
python -B .\skills\renode-bench\scripts\analyze_trace.py 'C:\seu-projeto\bench\trace-pc.log'
```

O analisador de trace é somente leitura. Frequência de PCs ajuda a selecionar regiões para investigar; emulação não valida hardware real.

## Uso com VeriMission

O [VeriMission](https://github.com/wagmarsouza/long-project-agent-harness) é opcional e coordena missões longas, critérios, claims e retratações. DisasmLedger não inclui seu executor nem depende dele para rodar os auxiliares. Se o utilizar, leia a [integração opcional](skills/binary-analysis-profile/references/v8-integration.md) e consulte a versão do harness instalada: o estado canônico e os comandos pertencem àquela versão.

## Escopo e distribuição

- O pacote publica modelos e testes sintéticos. Não inclui firmware, dumps, credenciais, logs pessoais ou configuração de hardware privado.
- Preserve o binário original, identifique seu hash e declare a origem, configuração, observações, inferências, contradições e cobertura com denominador.
- Ferramentas de terceiros, inclusive Renode, têm instalação e termos próprios.
- Este repositório não tem arquivo de licença. Publicação pública por si só não concede permissão geral para redistribuição ou modificação; uma licença requer escolha explícita do autor.

O nome DisasmLedger expressa o vínculo entre bytes, observações e conclusões auditáveis. O logotipo foi criado para este projeto.
