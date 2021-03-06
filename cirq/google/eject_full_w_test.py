# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Iterable

import cirq
import cirq.google as cg


def assert_optimizes(before: cirq.Circuit,
                     expected: cirq.Circuit,
                     compare_unitaries: bool = True):
    opt = cg.EjectFullW()

    circuit = before.copy()
    opt.optimize_circuit(circuit)

    # They should have equivalent effects.
    if compare_unitaries:
        cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
            circuit, expected, 1e-8)

    # And match the expected circuit.
    assert circuit == expected, (
        "Circuit wasn't optimized as expected.\n"
        "INPUT:\n"
        "{}\n"
        "\n"
        "EXPECTED OUTPUT:\n"
        "{}\n"
        "\n"
        "ACTUAL OUTPUT:\n"
        "{}\n"
        "\n"
        "EXPECTED OUTPUT (detailed):\n"
        "{!r}\n"
        "\n"
        "ACTUAL OUTPUT (detailed):\n"
        "{!r}").format(before, expected, circuit, expected, circuit)

    # And it should be idempotent.
    opt.optimize_circuit(circuit)
    assert circuit == expected


def quick_circuit(*moments: Iterable[cirq.OP_TREE]) -> cirq.Circuit:
    return cirq.Circuit([cirq.Moment(cirq.flatten_op_tree(m)) for m in moments])


def test_absorbs_z():
    q = cirq.NamedQubit('q')

    # Full Z.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.125).on(q)],
            [cirq.Z(q)],
        ),
        expected=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.625).on(q)],
            [],
        ))

    # Partial Z.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.125).on(q)],
            [cirq.S(q)],
        ),
        expected=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.375).on(q)],
            [],
        ))

    # Multiple Zs.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.125).on(q)],
            [cirq.S(q)],
            [cirq.T(q)**-1],
        ),
        expected=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [],
            [],
        ))


def test_crosses_czs():
    a = cirq.NamedQubit('a')
    b = cirq.NamedQubit('b')

    # Full CZ.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(a)],
            [cirq.CZ(a, b)],
        ),
        expected=quick_circuit(
            [cirq.Z(b)],
            [cirq.CZ(a, b)],
            [cg.ExpWGate(phase_exponent=0.25).on(a)],
        ))
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.125).on(a)],
            [cirq.CZ(b, a)],
        ),
        expected=quick_circuit(
            [cirq.Z(b)],
            [cirq.CZ(a, b)],
            [cg.ExpWGate(phase_exponent=0.125).on(a)],
        ))

    # Partial CZ.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.CZ(a, b)**0.25],
        ),
        expected=quick_circuit(
            [cirq.Z(b)**0.25],
            [cirq.CZ(a, b)**-0.25],
            [cg.ExpWGate().on(a)],
        ))

    # Double cross.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.125).on(a)],
            [cg.ExpWGate(phase_exponent=0.375).on(b)],
            [cirq.CZ(a, b)**0.25],
        ),
        expected=quick_circuit(
            [],
            [],
            [cirq.CZ(a, b)**0.25],
            [cg.ExpWGate(phase_exponent=0.5).on(b),
             cg.ExpWGate(phase_exponent=0.25).on(a)],
        ))


def test_toggles_measurements():
    a = cirq.NamedQubit('a')
    b = cirq.NamedQubit('b')

    # Single.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(a)],
            [cirq.measure(a, b)],
        ),
        expected=quick_circuit(
            [],
            [cirq.measure(a, b, invert_mask=(True,))],
        ))
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(b)],
            [cirq.measure(a, b)],
        ),
        expected=quick_circuit(
            [],
            [cirq.measure(a, b, invert_mask=(False, True))],
        ))

    # Multiple.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(a)],
            [cg.ExpWGate(phase_exponent=0.25).on(b)],
            [cirq.measure(a, b)],
        ),
        expected=quick_circuit(
            [],
            [],
            [cirq.measure(a, b, invert_mask=(True, True))],
        ))

    # Xmon.
    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(a)],
            [cirq.measure(a, b, key='t')],
        ),
        expected=quick_circuit(
            [],
            [cirq.measure(a, b, invert_mask=(True,), key='t')],
        ))


def test_cancels_other_full_w():
    q = cirq.NamedQubit('q')

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
        ),
        expected=quick_circuit(
            [],
            [],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [cg.ExpWGate(phase_exponent=0.125).on(q)],
        ),
        expected=quick_circuit(
            [],
            [cirq.Z(q)**-0.25],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(q)],
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
        ),
        expected=quick_circuit(
            [],
            [cirq.Z(q)**0.5],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [cg.ExpWGate().on(q)],
        ),
        expected=quick_circuit(
            [],
            [cirq.Z(q)**-0.5],
        ))


def test_phases_partial_ws():
    q = cirq.NamedQubit('q')

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(q)],
            [cg.ExpWGate(phase_exponent=0.25, exponent=0.5).on(q)],
        ),
        expected=quick_circuit(
            [],
            [cg.ExpWGate(phase_exponent=-0.25, exponent=0.5).on(q)],
            [cg.ExpWGate().on(q)],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [cg.ExpWGate(exponent=0.5).on(q)],
        ),
        expected=quick_circuit(
            [],
            [cg.ExpWGate(phase_exponent=0.5, exponent=0.5).on(q)],
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
            [cg.ExpWGate(phase_exponent=0.5, exponent=0.75).on(q)],
        ),
        expected=quick_circuit(
            [],
            [cg.ExpWGate(exponent=0.75).on(q)],
            [cg.ExpWGate(phase_exponent=0.25).on(q)],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(q)],
            [cg.ExpWGate(exponent=-0.25, phase_exponent=0.5).on(q)]
        ),
        expected=quick_circuit(
            [],
            [cg.ExpWGate(exponent=-0.25, phase_exponent=-0.5).on(q)],
            [cg.ExpWGate().on(q)],
        ))


def test_blocked_by_unknown_and_symbols():
    a = cirq.NamedQubit('a')
    b = cirq.NamedQubit('b')

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.SWAP(a, b)],
            [cg.ExpWGate().on(a)],
        ),
        expected=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.SWAP(a, b)],
            [cg.ExpWGate().on(a)],
        ))

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.Z(a)**cirq.Symbol('z')],
            [cg.ExpWGate().on(a)],
        ),
        expected=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.Z(a)**cirq.Symbol('z')],
            [cg.ExpWGate().on(a)],
        ),
        compare_unitaries=False)

    assert_optimizes(
        before=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.CZ(a, b)**cirq.Symbol('z')],
            [cg.ExpWGate().on(a)],
        ),
        expected=quick_circuit(
            [cg.ExpWGate().on(a)],
            [cirq.CZ(a, b)**cirq.Symbol('z')],
            [cg.ExpWGate().on(a)],
        ),
        compare_unitaries=False)
