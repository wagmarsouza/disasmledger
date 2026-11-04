# DisasmLedger

![DisasmLedger: bytes and traces backed by evidence](assets/disasmledger-logo.png)

Skills for traceable binary analysis and firmware test benches. The project contains three independent skills: `binary-analysis-profile` organises target identity, address maps, analysis units, and witnesses; `renode-bench` guides the creation of a Renode bench and the interpretation of program-counter traces; `decompile` orchestrates a staged, grade-gated reconstruction workflow over the other two and schedules work by call-graph closure. They can be used separately or together.

## Installation

With Node.js and the [Skills CLI](https://skills.sh/):

```powershell
npx skills add wagmarsouza/disasmledger --skill binary-analysis-profile
npx skills add wagmarsouza/disasmledger --skill renode-bench
npx skills add wagmarsouza/disasmledger --skill decompile
```

To clone the repository and use the scripts without an agent:

```powershell
git clone https://github.com/wagmarsouza/disasmledger.git
cd disasmledger
python -B -m unittest discover -s skills/binary-analysis-profile/tests -v
python -B -m unittest discover -s skills/renode-bench/tests -v
python -B -m unittest discover -s skills/decompile/tests -v
```

## Binary Analysis Profile

Read [the skill](skills/binary-analysis-profile/SKILL.md) and the templates in `skills/binary-analysis-profile/assets/templates/`. Complete the manifests with data from your own target; the bundled examples are synthetic.

```powershell
$b = '.\skills\binary-analysis-profile\scripts\binary_profile.py'
$p = 'C:\your-project'
python -B $b --project $p inspect --binary 'evidence\image.bin'
python -B $b --project $p target --input "$p\analysis\target.json"
python -B $b --project $p unit --target "$p\analysis\target.json" --input "$p\analysis\unit.json"
python -B $b --project $p witnesses --target "$p\analysis\target.json" --unit "$p\analysis\unit.json" --input "$p\analysis\witnesses.json"
```

The helper checks declared consistency and links manifests to files. It does not disassemble the binary, identify its architecture, authenticate logs, or establish semantic truth. The [synthetic pilot](skills/binary-analysis-profile/examples/run_pilot.py) verifies the workflow without real firmware:

```powershell
python -B skills/binary-analysis-profile/examples/run_pilot.py
```

## Renode Bench

Read [the skill](skills/renode-bench/SKILL.md) and [the usage guide](skills/renode-bench/references/usage.md). Renode is an external dependency. Copy `boot-trace.resc` into your project, then replace and review every platform, address, and firmware marker before running it.

```powershell
$renode = 'C:\Program Files\Renode\bin\Renode.exe'
$bench = 'C:\your-project\bench\boot-trace.resc'
& $renode --disable-gui --console $bench
python -B .\skills\renode-bench\scripts\analyze_trace.py 'C:\your-project\bench\trace-pc.log'
```

The trace analyser is read-only. Program-counter frequency helps select regions for investigation; emulation does not validate real hardware.

## Decompile

Read [the skill](skills/decompile/SKILL.md) and the references in `skills/decompile/references/` (methodology, toolchain routing, and differential testing). It is an orchestrator: it does not disassemble, execute, or grade anything itself. It sets out a grade ladder (G0 bogus, G1 raw, G2 semantics, G3 compiles, G4 bench-confirmed), routes each stage to the right tool, and composes `binary-analysis-profile` and `renode-bench` for the evidence steps.

The only executable helper is a read-only scheduler. It consumes a declared call graph and a declared grade map — produced by your own tools, in the formats shown in `skills/decompile/assets/templates/` — and reports which units are differentially testable now (their callee-closure is already reconstructed) and which undone helpers carry the most leverage:

```powershell
$c = '.\skills\decompile\scripts\closure.py'
$p = 'C:\your-project'
python -B $c --project $p report --callgraph "$p\analysis\callgraph.json" --grades "$p\analysis\grades.json"
```

It never establishes semantic truth or promotes a grade; `semantic_truth_verified` and `promotion_authorized` are always false. The [synthetic pilot](skills/decompile/examples/run_pilot.py) verifies the scheduling arithmetic without real firmware:

```powershell
python -B skills/decompile/examples/run_pilot.py
```

## Using DisasmLedger with VeriMission

[VeriMission](https://github.com/wagmarsouza/long-project-agent-harness) is optional. It coordinates long-running missions, acceptance criteria, claims, and retractions. DisasmLedger does not include the VeriMission executor and does not depend on it to run its helpers. If you use both projects, read the [optional integration guide](skills/binary-analysis-profile/references/v8-integration.md) and consult the installed harness version: canonical state and commands belong to that version.

## Scope and distribution

- The package publishes templates and synthetic tests. It contains no firmware, dumps, credentials, personal logs, or private hardware configuration.
- Preserve the original binary, identify its hash, and document its origin, configuration, observations, inferences, contradictions, and coverage denominator.
- Third-party tools, including Renode, have their own installation procedures and terms.
- This repository does not include a licence file. Public availability alone does not grant general permission to redistribute or modify the work; selecting a licence requires an explicit decision by the author.

The name DisasmLedger reflects the link between bytes, observations, and auditable conclusions. The logo was created for this project.
