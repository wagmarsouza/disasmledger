# Evidence, benches, and claim ceilings

## Strength of each result

| Method | Permitted claim, when supported | Remaining gap |
| --- | --- | --- |
| Hash and declared map | These bytes and ranges were used; the map is internally consistent | Correct architecture and base, legitimacy, and behaviour |
| Static inspection | These instructions and references support this bounded hypothesis | Decoding, indirect paths, and actual behaviour may differ |
| Isolated function | The region produced the observed result under these inputs and state | Complete ABI, peripherals, concurrency, and integration |
| Emulated boot or integration | These states and effects occurred in the described model | Peripheral fidelity and behaviour on hardware |
| Hardware observation | The observed device and configuration behaved this way under these conditions | Other devices, inputs, versions, and universality |

These levels are not an automatic ladder. A hardware observation may be narrow, while a specific static proof may answer a different question better. Never convert log volume into a probability of truth.

## Preparing a relevant experiment

State the input and initial state, dependent inputs, reset and preconditions, observation point, expected oracle with independent justification, timeout or stopping condition, and final state. Record the tool and version, configuration, and dependencies. Distinguish the complete configuration from omitted elements. If the experiment used stubs, traps, forced RAM or register values, an artificial clock, intercepted calls, or substituted peripherals, list them precisely and limit the conclusion accordingly.

When the bench contributes to the claim, use a known-behaviour control to show that it can observe the relevant phenomenon, plus contrasting cases chosen to discriminate the hypothesis. Include boundaries, error conditions, and a plausible alternative as required by the contract. The helper's structural minimum is one control and two cases with different input content; it is not a calculation of sufficient sample size. Different inputs may exercise the same path or reproduce the same error.

Do not make the oracle copy the implementation or populate `observed` from `expected`. Observations must come from the execution or review that actually occurred and must reference preserved logs. Logs must identify enough context, outcome, and stopping information for analysis. An empty or irrelevant log does not support a conclusion even if its hash is correct. Any additional controls required by the mission remain mandatory.

After an interrupted or disconnected execution, record the outcome as unknown until the trace or checkpoint is recovered. Do not assume success from elapsed time or repeat externally consequential operations before reconciling state.

## Helper contract

`target` checks the bytes, hash, required fields, and declared linear map. `unit` checks range, alignment, address conversion, and the hash of the selected bytes. Neither command decodes instructions nor proves that a range is a function.

`witnesses` checks hashes for the binary, unit, manifests, inputs, and logs. It requires unique identifiers, non-empty expectations, a control, at least two distinct input-content sets, and a declaration of injections and limitations. It compares each expected key with the observed value and requires the key to exist. `true`, `1`, and `1.0` are distinct; use stable types and representations. Numeric tolerances require a suitable separate comparison, not an edited observation.

Additional observed fields are not automatically failures. Put relevant error conditions, including effects that must be absent, into the expectations. Comparisons do not prove that the JSON producer honestly reported what occurred. `execution_reference` is a textual reference, not authentication. The `hardware_observation` type does not turn the helper into a hardware validator.

Before hashing, manifests are normalised as UTF-8 JSON with sorted keys, compact separators, and no NaN values. `unit` returns `target_manifest_sha256` and `unit_manifest_sha256` for use in reports. Metadata changes also invalidate this conservative binding; they require review but do not necessarily mean the bytes or behaviour changed. The CLI rejects duplicate keys and non-finite numbers.

Internal paths must resolve to files inside the project. The helper rejects traversal, absolute paths, symlink escapes, and `.harness`. This is not isolation against an adversarial process replacing files during a read. Work with frozen evidence and declare all files relevant to the adopted verifier. Files are read fully into memory; for very large images, prepare and verify a specific strategy before using the helper rather than silently changing the target.

## Honesty audit for the conclusion

Report the exact claim, the method and environment actually used, files and checks, coverage and denominator, failed cases, and outstanding tests. An acceptable sentence is: “The two recorded cases match their expectations under the disclosed injections; integration and hardware were not tested.” Avoid “algorithm validated” when only the report was checked. Preserve negative results and permit retraction without inventing a numerical certainty score.
