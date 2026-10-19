OPENQASM 3;
include "stdgates.inc";

def program(qubit[3] q) {
    x q[2];
    h q[0];
    h q[1];
    h q[2];
    cx q[0], q[2];
    cx q[1], q[2];
    h q[0];
    rz(1.570796326795) q[2];
    h q[1];
}

def test_phase_visible() {
    //% shots 2000
    //% seed 42
    //% backend ideal
    qubit[3] q;
    bit[3] m;
    program(q);
    h q[2];
    m = measure q;
    //% expect marginal m[2] p1 ~= 1.0 atol=0.05
}
