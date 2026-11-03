# Organising a long-running binary-analysis mission

## 1. Fix the contract and identity

Start from the authorised objective: locate an algorithm, reconstruct a protocol, explain a region, compare versions, or validate a specific behaviour. Convert that objective into observable criteria; “understand the entire firmware” is not an executable criterion by itself. Define exclusions, output formats, available environment, and the level of evidence the user actually requires.

Keep an original copy and its provenance. SHA-256 identifies bytes, not their legitimacy, commercial version, or origin. Record which data was supplied, extracted, decompressed, decrypted, or reconstructed, including input and output hashes and the tool and configuration used. Never combine regions from two versions under one identity. Do not execute the target to discover its architecture.

The `binary-target-v1` manifest supports linear mapping through file segments: byte offset and size, with virtual addresses measured in `address_unit_bytes`. VA = base + (offset − segment offset) / units. Ranges must remain inside the file. Overlaps require explicitly different spaces, such as banks. File-less regions, relocation, MMIO, runtime RAM, and non-linear transformations require additional documentation and suitable criteria; do not invent a map merely to satisfy the helper.

Validate the map hypothesis separately using headers, architecture specifications, vectors, cross-references, and relevant observations. Structural approval of the manifest does not perform that validation. Keep ISA, endianness, and base-address uncertainty explicit until discriminated.

## 2. Inventory without inventing completeness

Create a versioned inventory with an identifier, range, address space, mode, classification, and source of the hypothesis. A unit may be a candidate function, a table, a mixed block, or an unknown region. Do not cut every file into equal chunks or count every block as a function.

For a function hypothesis, record candidate inputs, outputs, assumed calling convention, relevant branches, calls and references, possible interleaved data, and contradictions. An apparent return or recognised signature does not settle all boundaries. Indirect calls, tail calls, trampolines, compressed or generated code, and banks may leave explicit gaps.

The call graph is a technical result whose edges may be observed, inferred, or unknown. If a task coordinator is present, its graph represents work. Do not treat either graph as a substitute for the other or create a task for every instruction without a practical reason.

Define denominators for each question: inventoried regions examined, protocol requirements tested, defined critical paths, or contract cases. Example: “3 of 12 inventoried units were tested for hypothesis X; the inventory is incomplete, so whole-binary coverage is indeterminate.” Do not say “25% of the firmware is understood.” Exclude regions only with a traceable justification; a change to authorised scope requires mission revision.

## 3. Recover context and plan the smallest useful investigation

Consult the existing inventory and evidence. If using VeriMission, run `resume`, `validate`, `search`, and `review` for the installed version. Search by hash, offset or virtual address, identifier, and recorded aliases. Read status and limitations before reusing any result.

Use a stable topic, for example `bin:<sha256>:main:text:off-4:len-4:isa-<mode>`. Record friendly aliases without replacing identity. Define the hypothesis and its most plausible alternative, the cheapest test that separates them, and the mission criteria that test can actually satisfy. Do not repeat identical attempts until one produces a favourable output.

## 4. Export, verify, and record

After authorised analysis, freeze an export for each relevant unit or result: bytes, assembly with addresses and mode, references or pseudocode when relevant, exporter version and configuration, and limitations. A hash confirms the identity of those files. If correspondence between the export and binary is part of the conclusion, it requires an additional suitable test; the helper does not establish that semantic correspondence.

Generate traces and other artifacts before verification. Use names and versions that preserve older evidence. When a declared artifact must change, follow the revision or reopening process required by the adopted workflow. Do not edit old hashes to conceal changes. A tool database often changes because of irrelevant annotations; treating that database as context and bounded exports as evidence permits precise invalidation, provided the real dependencies are declared.

Run read-only verification and record the evidence scope. With VeriMission, use `evidence-scope`. Check whether commands genuinely distinguish the hypothesis. Record bounded behaviour as a claim only when the evidence supports the exact sentence; a helper result alone never authorises a semantic conclusion.

## 5. Resume and conclude

Keep the following in task context: hash and manifests; identifier, address space, offset, virtual address, and mode; tool and configuration; current hypothesis and alternatives; evidence and limitations; dependencies and retractions; open questions; next discriminating test; and operations awaiting reconciliation. Capsules and context packs are derived views; check freshness and recover original records when needed.

When changing firmware version, state the new identity and review the applicability of earlier conclusions. A presumed matching function or name does not transfer evidence automatically. Version comparison requires its own criterion.

At closure, separate what was described statically, observed on the bench, and observed in the final environment. Run acceptance for the adopted mission, present coverage with its universe and exclusions, and record limitations. A complete form or internally consistent database does not show that the binary's full semantics were recovered.
