"""
Zero-Noise Extrapolation for Quantum Sensing: Recovering Fisher Information
via Gate Folding
================================================================================
Third companion project to: "Balanced Homodyne Detection without Coherent
State Local Oscillator" (M.Sc. Thesis, Dhrithi Maria, Universitaet Paderborn,
2026). Builds on Project 1 (01-fisher-information-limits/) and Project 2 (02-lo-agnostic-calibration/).

See theory_notes.md for the full derivation and the mapping between ZNE's
noise-scaling-and-extrapolation strategy and the thesis's own robustness /
stress-test chapter (Ch. 5, Appendix A.2).

This script:
  1. Rebuilds the Ramsey (SQL) and GHZ (Heisenberg) circuits and the
     depolarizing+dephasing noise model from Projects 1-2.
  2. Implements UNITARY GATE FOLDING: U -> U (U^dagger U)^k, run at fold
     factors lambda = 1, 3, 5, which deliberately amplifies the circuit's
     noise by a known, controlled factor.
  3. Fits a linear Richardson extrapolation of the measured probability vs.
     fold factor and evaluates it at lambda -> 0 (the zero-noise limit).
  4. Recomputes the Classical Fisher Information from the ZNE-extrapolated
     probabilities, exactly as in Projects 1-2 but with a *different*,
     independent mitigation strategy (no reference/calibration circuit
     needed).
  5. Compares four curves against N: ideal QFI, raw noisy CFI (Project 1),
     calibration-corrected CFI (Project 2), and ZNE-corrected CFI (this
     project) -- a cross-validation of two independent mitigation methods.

Requires: qiskit, qiskit-aer, numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, phase_damping_error

# ----------------------------------------------------------------------------
# Circuit builders (ported from Projects 1-2), split into an "unfolded unitary
# part" and a separate measurement, so folding can be inserted between them.
# ----------------------------------------------------------------------------

def ramsey_unitary(theta: float) -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.rz(theta, 0)
    qc.h(0)
    return qc


def ghz_unitary(theta: float, n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    for i in range(n):
        qc.rz(theta, i)
    for i in reversed(range(n - 1)):
        qc.cx(i, i + 1)
    qc.h(0)
    return qc


def fold_circuit(unitary_qc: QuantumCircuit, scale: int) -> QuantumCircuit:
    """Unitary folding: U -> U (U^dagger U)^k for scale = 2k+1.

    Logically identical to U for a perfect circuit (U^dagger U = identity),
    but each extra (U^dagger, U) pair accumulates one more round trip's
    worth of real gate noise -- the deliberate, controlled noise
    amplification ZNE relies on.
    """
    if scale % 2 == 0 or scale < 1:
        raise ValueError("scale must be a positive odd integer (1, 3, 5, ...)")
    k = (scale - 1) // 2
    folded = unitary_qc.copy()
    for _ in range(k):
        folded = folded.compose(unitary_qc.inverse())
        folded = folded.compose(unitary_qc)
    return folded


def add_measurement(unitary_qc: QuantumCircuit) -> QuantumCircuit:
    n = unitary_qc.num_qubits
    qc = QuantumCircuit(n, 1)
    qc.compose(unitary_qc, inplace=True)
    qc.measure(0, 0)
    return qc


def build_noise_model(p_depol: float = 0.01, p_dephase: float = 0.01) -> NoiseModel:
    noise_model = NoiseModel()
    depol_err = depolarizing_error(p_depol, 1)
    dephase_err = phase_damping_error(p_dephase)
    combined = depol_err.compose(dephase_err)
    noise_model.add_all_qubit_quantum_error(combined, ["h", "rz"])
    two_q_depol = depolarizing_error(p_depol, 2)
    noise_model.add_all_qubit_quantum_error(two_q_depol, ["cx"])
    return noise_model


SIM = AerSimulator()


def p0_folded(unitary_builder, theta: float, scale: int, shots: int,
              noise_model=None, **kwargs) -> float:
    unitary_qc = unitary_builder(theta, **kwargs) if kwargs else unitary_builder(theta)
    folded = fold_circuit(unitary_qc, scale)
    qc = add_measurement(folded)
    tqc = transpile(qc, SIM, optimization_level=0)  # preserve the folded
                                                      # gate sequence -- see
                                                      # 02-lo-agnostic-calibration for
                                                      # why optimization_level=0
                                                      # matters here.
    result = SIM.run(tqc, shots=shots, noise_model=noise_model).result()
    counts = result.get_counts()
    return counts.get("0", 0) / shots


def zne_extrapolate(unitary_builder, theta: float, shots: int, noise_model,
                     scales=(1, 3, 5), **kwargs) -> float:
    """Richardson (linear) extrapolation of P(theta) to the zero-noise limit."""
    ps = [p0_folded(unitary_builder, theta, s, shots, noise_model, **kwargs)
          for s in scales]
    coeffs = np.polyfit(scales, ps, deg=1)  # coeffs[-1] = intercept at lambda=0
    p0_extrapolated = coeffs[-1]
    return float(np.clip(p0_extrapolated, 1e-6, 1 - 1e-6))


def cfi_from_probs(p_plus: float, p_minus: float, p0: float, eps: float) -> float:
    dpdtheta = (p_plus - p_minus) / (2 * eps)
    p0 = min(max(p0, 1e-6), 1 - 1e-6)
    return (dpdtheta ** 2) / (p0 * (1 - p0))


def raw_cfi(unitary_builder, theta0: float, shots: int, noise_model, eps: float,
            **kwargs) -> float:
    """Raw (unmitigated) CFI at fold scale 1, for the noisy-baseline comparison."""
    p_plus = p0_folded(unitary_builder, theta0 + eps, 1, shots, noise_model, **kwargs)
    p_minus = p0_folded(unitary_builder, theta0 - eps, 1, shots, noise_model, **kwargs)
    p0 = p0_folded(unitary_builder, theta0, 1, shots, noise_model, **kwargs)
    return cfi_from_probs(p_plus, p_minus, p0, eps)


def zne_cfi(unitary_builder, theta0: float, shots: int, noise_model, eps: float,
            scales=(1, 3, 5), **kwargs) -> float:
    """ZNE-mitigated CFI: extrapolate each of the three probabilities
    (theta0-eps, theta0, theta0+eps) to the zero-noise limit independently,
    then form the CFI from the extrapolated values."""
    p_plus = zne_extrapolate(unitary_builder, theta0 + eps, shots, noise_model,
                              scales, **kwargs)
    p_minus = zne_extrapolate(unitary_builder, theta0 - eps, shots, noise_model,
                               scales, **kwargs)
    p0 = zne_extrapolate(unitary_builder, theta0, shots, noise_model, scales, **kwargs)
    return cfi_from_probs(p_plus, p_minus, p0, eps)


# ----------------------------------------------------------------------------
# Calibration-corrected CFI (Project 2), reimplemented here for the
# side-by-side comparison plot.
# ----------------------------------------------------------------------------

def visibility(unitary_builder, shots: int, noise_model, **kwargs) -> float:
    p0_ref = p0_folded(unitary_builder, 0.0, 1, shots, noise_model, **kwargs)
    return 2 * p0_ref - 1


def calibration_cfi(unitary_builder, theta0: float, shots: int, noise_model,
                     eps: float, **kwargs) -> float:
    f_raw = raw_cfi(unitary_builder, theta0, shots, noise_model, eps, **kwargs)
    v = visibility(unitary_builder, shots, noise_model, **kwargs)
    v_safe = max(v, 0.05)
    return f_raw / v_safe ** 2


# ----------------------------------------------------------------------------
# Main sweep
# ----------------------------------------------------------------------------

def main():
    theta0_ramsey = np.pi / 2
    shots = 20000
    repeats = 3
    N_values = np.arange(1, 6)  # kept to 5 -- ZNE triples the circuit depth at
                                  # scale 5, so runtime grows faster with N
    noise_model = build_noise_model(p_depol=0.01, p_dephase=0.01)

    qfi_sql = N_values * 1.0
    qfi_heisenberg = N_values ** 2.0

    raw_ramsey, cal_ramsey, zne_ramsey = [], [], []
    raw_ghz, cal_ghz, zne_ghz = [], [], []

    for n in N_values:
        theta0_ghz = np.pi / (2 * n)
        eps_ghz = min(0.05, theta0_ghz / 2)

        raw_r, cal_r, zne_r = [], [], []
        raw_g, cal_g, zne_g = [], [], []
        for _ in range(repeats):
            raw_r.append(raw_cfi(ramsey_unitary, theta0_ramsey, shots, noise_model, 0.05))
            cal_r.append(calibration_cfi(ramsey_unitary, theta0_ramsey, shots,
                                          noise_model, 0.05))
            zne_r.append(zne_cfi(ramsey_unitary, theta0_ramsey, shots, noise_model, 0.05))

            raw_g.append(raw_cfi(ghz_unitary, theta0_ghz, shots, noise_model,
                                  eps_ghz, n=n))
            cal_g.append(calibration_cfi(ghz_unitary, theta0_ghz, shots, noise_model,
                                          eps_ghz, n=n))
            zne_g.append(zne_cfi(ghz_unitary, theta0_ghz, shots, noise_model,
                                  eps_ghz, n=n))

        raw_ramsey.append(n * float(np.mean(raw_r)))
        cal_ramsey.append(n * float(np.mean(cal_r)))
        zne_ramsey.append(n * float(np.mean(zne_r)))
        raw_ghz.append(float(np.mean(raw_g)))
        cal_ghz.append(float(np.mean(cal_g)))
        zne_ghz.append(float(np.mean(zne_g)))

        print(f"N={n}: QFI_Heis={n**2:6.1f}  "
              f"raw={raw_ghz[-1]:6.2f}  calibrated={cal_ghz[-1]:6.2f}  "
              f"ZNE={zne_ghz[-1]:6.2f}")

    print("\nAgreement between the two independent mitigation strategies (GHZ):")
    for n, cal, zne, qfi in zip(N_values, cal_ghz, zne_ghz, qfi_heisenberg):
        pct_of_qfi_cal = cal / qfi * 100
        pct_of_qfi_zne = zne / qfi * 100
        print(f"  N={n}: calibration reaches {pct_of_qfi_cal:5.1f}% of QFI, "
              f"ZNE reaches {pct_of_qfi_zne:5.1f}% of QFI "
              f"(difference: {abs(pct_of_qfi_cal - pct_of_qfi_zne):4.1f} pts)")

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.plot(N_values, qfi_sql, "k--", label="QFI (SQL), $F_Q=N$")
    ax.plot(N_values, qfi_heisenberg, "k-.", label="QFI (Heisenberg), $F_Q=N^2$")
    ax.plot(N_values, raw_ghz, "s-", color="#d8763b", label="CFI, GHZ (raw, noisy)")
    ax.plot(N_values, cal_ghz, "^-", color="#2c8f5b",
            label="CFI, GHZ (calibration-corrected, Project 2)")
    ax.plot(N_values, zne_ghz, "D-", color="#7b5bd8",
            label="CFI, GHZ (ZNE-corrected, this project)")
    ax.set_yscale("log")
    ax.set_xlabel("Number of qubits, N")
    ax.set_ylabel("Fisher information (log scale)")
    ax.set_title("Two Independent Error-Mitigation Strategies for GHZ Phase Estimation")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig("zne_vs_calibration.png", dpi=150)
    print("\nSaved plot to zne_vs_calibration.png")


if __name__ == "__main__":
    main()
