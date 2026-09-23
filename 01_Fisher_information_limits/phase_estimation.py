"""
Fisher Information Limits for Phase Estimation: Ramsey vs. GHZ Interferometry
================================================================================
Companion project to: "Balanced Homodyne Detection without Coherent State
Local Oscillator" (M.Sc. Thesis, Dhrithi Maria, Universitaet Paderborn, 2026)

See theory_notes.md for the full derivation and the mapping between this
project's Fisher-information formalism and the thesis's continuous-variable
quadrature/covariance-matrix framework.

This script:
  1. Builds single-qubit Ramsey circuits (N independent qubits -> SQL) and
     N-qubit GHZ circuits (-> Heisenberg limit) for phase estimation of an
     unknown angle theta.
  2. Estimates the Classical Fisher Information (CFI) numerically from
     simulated measurement statistics via a central finite difference,
     mirroring the thesis's calibration-from-measured-statistics philosophy
     (Ch. 4) rather than assuming the answer analytically.
  3. Compares CFI against the analytic Quantum Fisher Information (QFI) and
     the resulting Cramer-Rao bounds (SQL ~ 1/N, Heisenberg ~ 1/N^2).
  4. Repeats the comparison under a depolarizing/dephasing noise model to
     show how decoherence erodes the GHZ state's Heisenberg advantage.

Requires: qiskit, qiskit-aer, numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, phase_damping_error

# ----------------------------------------------------------------------------
# Circuit builders
# ----------------------------------------------------------------------------

def ramsey_circuit(theta: float) -> QuantumCircuit:
    """Single-qubit Ramsey interferometer encoding theta via RZ phase kickback.

    H -> RZ(theta) -> H -> measure.
    This is the DV analog of the LO phase shifter b-hat -> exp(i*phi) b-hat
    (thesis Eq. 1.3): here the phase is imprinted on a single-qubit probe
    rather than on a strong coherent LO mode.
    """
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.rz(theta, 0)
    qc.h(0)
    qc.measure(0, 0)
    return qc


def ghz_ramsey_circuit(theta: float, n: int) -> QuantumCircuit:
    """N-qubit GHZ interferometer encoding N*theta collectively.

    Prepare GHZ, apply a local RZ(theta) on every qubit (collective phase
    accumulation scales the encoded phase by N), disentangle, and measure
    the parity qubit. This is the entangled probe achieving F_Q = N^2
    (Heisenberg scaling) instead of F_Q = N for N independent qubits.
    """
    qc = QuantumCircuit(n, 1)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    for i in range(n):
        qc.rz(theta, i)
    for i in reversed(range(n - 1)):
        qc.cx(i, i + 1)
    qc.h(0)
    qc.measure(0, 0)
    return qc


# ----------------------------------------------------------------------------
# Noise model (depolarizing + dephasing), applied uniformly per qubit-gate
# ----------------------------------------------------------------------------

def build_noise_model(p_depol: float = 0.01, p_dephase: float = 0.01) -> NoiseModel:
    noise_model = NoiseModel()
    depol_err = depolarizing_error(p_depol, 1)
    dephase_err = phase_damping_error(p_dephase)
    combined = depol_err.compose(dephase_err)
    noise_model.add_all_qubit_quantum_error(combined, ["h", "rz"])
    two_q_depol = depolarizing_error(p_depol, 2)
    noise_model.add_all_qubit_quantum_error(two_q_depol, ["cx"])
    return noise_model


# ----------------------------------------------------------------------------
# Measurement statistics -> P(outcome=0 | theta), CFI via finite difference
# ----------------------------------------------------------------------------

SIM = AerSimulator()


def p0_given_theta(circuit_fn, theta: float, shots: int, noise_model=None, **kwargs) -> float:
    qc = circuit_fn(theta, **kwargs) if kwargs else circuit_fn(theta)
    tqc = transpile(qc, SIM)
    result = SIM.run(tqc, shots=shots, noise_model=noise_model).result()
    counts = result.get_counts()
    p0 = counts.get("0", 0) / shots
    return p0


def classical_fisher_information(circuit_fn, theta0: float, shots: int,
                                   noise_model=None, eps: float = 0.05, **kwargs) -> float:
    """CFI for a binary-outcome measurement via central finite difference:
        F_C = (dP/dtheta)^2 / [P (1-P)]
    evaluated at theta0, using P estimated from simulated shot statistics
    (mirrors the thesis's "extract variance from measured statistics,
    not from an assumed analytic form" philosophy, Ch. 4).
    """
    p_plus = p0_given_theta(circuit_fn, theta0 + eps, shots, noise_model, **kwargs)
    p_minus = p0_given_theta(circuit_fn, theta0 - eps, shots, noise_model, **kwargs)
    p0 = p0_given_theta(circuit_fn, theta0, shots, noise_model, **kwargs)
    dpdtheta = (p_plus - p_minus) / (2 * eps)
    p0 = min(max(p0, 1e-6), 1 - 1e-6)  # avoid singular denominator
    return (dpdtheta ** 2) / (p0 * (1 - p0))


# ----------------------------------------------------------------------------
# Main sweep: N = 1..6, compare SQL (independent qubits) vs Heisenberg (GHZ)
# ----------------------------------------------------------------------------

def main():
    # Ramsey probability oscillates as (1+cos(theta))/2 -> most sensitive at
    # theta = pi/2. The GHZ probability oscillates as (1+cos(N*theta))/2 (the
    # collective phase N*theta is the whole point of the entangled probe), so
    # its most sensitive operating point shifts with N: theta = pi/(2N).
    # Evaluating away from each circuit's optimal point would measure the
    # *operating-point choice*, not the achievable Fisher information, so we
    # scan each circuit at its own optimum -- exactly as an experimentalist
    # would bias a real interferometer to its point of maximum slope.
    theta0_ramsey = np.pi / 2
    shots = 20000
    repeats = 4  # average several independent shot-noise realizations so the
                 # CFI estimate itself isn't dominated by finite-sample noise
    N_values = np.arange(1, 7)

    qfi_sql = N_values * 1.0          # N independent qubits: F_Q = N
    qfi_heisenberg = N_values ** 2.0  # N-qubit GHZ: F_Q = N^2

    cfi_ramsey_ideal, cfi_ghz_ideal = [], []
    cfi_ramsey_noisy, cfi_ghz_noisy = [], []

    noise_model = build_noise_model(p_depol=0.01, p_dephase=0.01)

    for n in N_values:
        theta0_ghz = np.pi / (2 * n)
        eps_ghz = min(0.05, theta0_ghz / 2)  # keep the finite-diff step well
                                              # inside the fringe for large n

        f_single_ideal_samples, f_single_noisy_samples = [], []
        f_ghz_ideal_samples, f_ghz_noisy_samples = [], []
        for _ in range(repeats):
            # Independent-qubit (SQL) baseline: CFI of n independent
            # single-qubit Ramsey measurements adds linearly, so simulate
            # one and scale by n.
            f_single_ideal_samples.append(
                classical_fisher_information(ramsey_circuit, theta0_ramsey, shots))
            f_single_noisy_samples.append(
                classical_fisher_information(ramsey_circuit, theta0_ramsey, shots,
                                              noise_model=noise_model))
            # GHZ (Heisenberg) probe: simulate the actual n-qubit entangled
            # circuit at its own optimal operating point theta0 = pi/(2n).
            f_ghz_ideal_samples.append(
                classical_fisher_information(ghz_ramsey_circuit, theta0_ghz, shots,
                                              eps=eps_ghz, n=n))
            f_ghz_noisy_samples.append(
                classical_fisher_information(ghz_ramsey_circuit, theta0_ghz, shots,
                                              noise_model=noise_model, eps=eps_ghz, n=n))

        cfi_ramsey_ideal.append(n * float(np.mean(f_single_ideal_samples)))
        cfi_ramsey_noisy.append(n * float(np.mean(f_single_noisy_samples)))
        cfi_ghz_ideal.append(float(np.mean(f_ghz_ideal_samples)))
        cfi_ghz_noisy.append(float(np.mean(f_ghz_noisy_samples)))

        print(f"N={n}: "
              f"QFI_SQL={n:6.1f}  CFI_Ramsey(ideal)={cfi_ramsey_ideal[-1]:6.2f}  "
              f"CFI_Ramsey(noisy)={cfi_ramsey_noisy[-1]:6.2f}  |  "
              f"QFI_Heis={n**2:6.1f}  CFI_GHZ(ideal)={cfi_ghz_ideal[-1]:6.2f}  "
              f"CFI_GHZ(noisy)={cfi_ghz_noisy[-1]:6.2f}")

    # ------------------------------------------------------------------
    # Plot: Fisher information vs N (log scale shows SQL vs Heisenberg scaling)
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.plot(N_values, qfi_sql, "k--", label="QFI (SQL bound), $F_Q = N$")
    ax.plot(N_values, qfi_heisenberg, "k-.", label="QFI (Heisenberg bound), $F_Q = N^2$")
    ax.plot(N_values, cfi_ramsey_ideal, "o-", color="#3b7dd8", label="CFI, Ramsey (ideal)")
    ax.plot(N_values, cfi_ghz_ideal, "s-", color="#d8763b", label="CFI, GHZ (ideal)")
    ax.set_yscale("log")
    ax.set_xlabel("Number of qubits / probes, N")
    ax.set_ylabel("Fisher information (log scale)")
    ax.set_title("Ideal (noiseless) simulation")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    ax = axes[1]
    ax.plot(N_values, qfi_sql, "k--", label="QFI (SQL bound), $F_Q = N$")
    ax.plot(N_values, qfi_heisenberg, "k-.", label="QFI (Heisenberg bound), $F_Q = N^2$")
    ax.plot(N_values, cfi_ramsey_noisy, "o-", color="#3b7dd8", label="CFI, Ramsey (noisy)")
    ax.plot(N_values, cfi_ghz_noisy, "s-", color="#d8763b", label="CFI, GHZ (noisy)")
    ax.set_yscale("log")
    ax.set_xlabel("Number of qubits / probes, N")
    ax.set_ylabel("Fisher information (log scale)")
    ax.set_title("With depolarizing + dephasing noise (p=0.01)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    fig.suptitle("Standard Quantum Limit vs. Heisenberg Limit: Fisher Information Scaling",
                  fontsize=12)
    fig.tight_layout()
    fig.savefig("fisher_information_scaling.png", dpi=150)
    print("\nSaved plot to fisher_information_scaling.png")


if __name__ == "__main__":
    main()
