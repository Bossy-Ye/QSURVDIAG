# Translation-conformance rule — frozen before any semantic result was computed

Timestamp of freeze: written prior to cloning the upstream MgcosA artifact and prior
to computing any state, unitary or comparison.

RULE. A Qolumbina Qiskit translation is admissible as an external subject only when
its behaviour can be tied to the upstream Q# program under the same concrete
pre-existing parameter tuple, register interpretation, initialization convention and
semantic contract, established without inspecting any mutation outcome.

Applied symmetrically to all ten MgcosA-derived generators. No generator is selected
for, or exempted from, this audit on grounds of C6, phase sensitivity, apparent
promise, or expected diagnostic relevance.

CONFORMANCE NOTION, chosen by contract type and not by convenience:
 A. Fixed-input / state-preparation contract -> compare final states for the same
    pre-existing concrete instance and input, modulo documented qubit ordering,
    register ordering, ancilla placement and one global phase. Equality decided at
    the study's existing numerical guard eps_num = 1e-9. A fixed-input contract is
    never strengthened into arbitrary-input unitary equivalence.
 B. Arbitrary-input unitary contract -> establish the operation-level relation, not
    equality on one convenient input. Where full unitary comparison is infeasible
    within existing technical limits, the result is Unresolved, never a weakened
    sampled-state check.
 C. Classical reversible mapping -> exhaustive computational-basis evaluation where
    feasible, or the mathematically specified mapping. Never inferred from examples.

INSTANCES. Only parameter tuples already present in the pinned Qolumbina artifact.
No new width, seed, input value or parameter combination is created. Every eligible
shipped tuple of a generator is audited; a failing tuple is never discarded because a
sibling tuple passes.

PHASE AND ORDERING. The register/ancilla/endianness map is established before any
comparison. One global phase is quotiented. Relative phase is NEVER quotiented, and
neither is changed register semantics, altered ancilla entanglement, nor output
ordering the specification does not permit.

OUTCOMES. Preserved / Not preserved / Unresolved. Unresolved is never converted to
Preserved on the basis of similar-looking gate sequences.

INDEPENDENCE. Translation conformance is evaluated without reference to C1 and
without reference to C6. Both C1 and preservation must hold independently for a
subject to be admissible. Evidence authored upstream is reported separately from
validation authored by this audit.
