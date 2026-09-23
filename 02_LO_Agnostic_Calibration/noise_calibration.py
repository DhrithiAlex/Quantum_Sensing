"""
LO-Agnostic-Style Calibration for Entangled Sensing Probes
================================================================================
Second companion project to: "Balanced Homodyne Detection without Coherent
State Local Oscillator" (M.Sc. Thesis, Dhrithi Maria, Universitaet Paderborn,
2026). Builds on Project 1 (01-fisher-information-limits/phase_estimation.py).

See theory_notes.md for the full derivation and the explicit mapping between
this project's visibility-based calibration and the thesis's vacuum-
substitution / law-of-total-variance calibration procedure (thesis Ch. 4,
Table 4.1, Eq. 4.2-4.3).

This script:
  1. Rebuilds the Ramsey (SQL) and GHZ (Heisenberg) phase-estimation
     circuits and the depolarizing+dephasing noise model from Project 1.
  2. CALIBRATION STEP (thesis Table 4.1, Step 1-2): runs each circuit at a
     known reference angle theta_ref = 0 under the noise channel and
     measures the empirical fringe visibility V_hat = 2*P(0) - 1 -- the
     discrete-variable analog of measuring Var_LO(phi) by substituting
     vacuum for the unknown signal.
  3. SIGNAL STEP (thesis Table 4.1, Step 3): runs each circuit at its true
     operating point and computes the raw (uncorrected) noisy CFI, exactly
     as in Project 1.
  4. CORRECTION STEP (thesis Eq. 4.3, Var_signal = [Var_total - Var_LO] /
     |<b>|^2): rescales the raw CFI by 1/V_hat^2 to produce a calibrated
     CFI estimate, and compares ideal QFI, raw noisy CFI, and calibrated
     CFI as functions of N.
  5. Reports the fraction of lost Fisher information recovered by
     calibration, and shows where the correction becomes unreliable at
     large N / low visibility -- reproducing the thesis's own "practical
     signal-to-noise requirement" (thesis Sec. 3.2, Condition 2) in the
     discrete-variable setting.

Requires: qiskit, qiskit-aer, numpy, matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, phase_damping_error

# ----------------------------------------------------------------------------
# Circuit builders (ported from Project 1: 01-fisher-information-limits/phase_estimation.py)
# ----------------------------------------------------------------------------

def ramsey_circuit(theta: float) -> QuantumCircuit:
    """Single-qubit Ramsey interferometer: H -> RZ(theta) -> H -> measure."""
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.rz(theta, 0)
    qc.h(0)
    qc.measure(0, 0)
    return qc


def ghz_ramsey_circuit(theta: float, n: int) -> QuantumCircuit:
    """N-qubit GHZ interferometer encoding N*theta collectively."""
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


def p0_given_theta(circuit_fn, theta: float, shots: int, noise_model=None, **kwargs) -> float:
    qc = circuit_fn(theta, **kwargs) if kwargs else circuit_fn(theta)
    # optimization_level=0: at theta=0 (our calibration reference point) the
    # H-RZ(0)-H / GHZ-disentangle sequence is algebraically the identity, and
    # a higher optimization level will simplify it away *entirely*, deleting
    # every gate the noise model is supposed to act on. That would make the
    # calibration run noise-free by construction -- silently defeating the
    # whole point of measuring the visibility. Keeping the literal gate
    # sequence intact is what makes this a genuine hardware-realistic
    # calibration measurement.
    tqc = transpile(qc, SIM, optimization_level=0)
    result = SIM.run(tqc, shots=shots, noise_model=noise_model).result()
    counts = result.get_counts()
    return counts.get("0", 0) / shots


def classical_fisher_information(circuit_fn, theta0: float, shots: int,
                                   noise_model=None, eps: float = 0.05, **kwargs) -> float:
    """Raw CFI via central finite difference (identical to Project 1)."""
    p_plus = p0_given_theta(circuit_fn, theta0 + eps, shots, noise_model, **kwargs)
    p_minus = p0_given_theta(circuit_fn, theta0 - eps, shots, noise_model, **kwargs)
    p0 = p0_given_theta(circuit_fn, theta0, shots, noise_model, **kwargs)
    dpdtheta = (p_plus - p_minus) / (2 * eps)
    p0 = min(max(p0, 1e-6), 1 - 1e-6)
    return (dpdtheta ** 2) / (p0 * (1 - p0))


# ----------------------------------------------------------------------------
# NEW: calibration (visibility) measurement -- the DV analog of
# thesis Table 4.1, Steps 1-2 (block the signal, substitute vacuum,
# measure Var_LO(phi) directly).
# ----------------------------------------------------------------------------

def measure_visibility(circuit_fn, shots: int, noise_model=None, **kwargs) -> float:
    """Calibration run at the known reference angle theta_ref = 0.

    Ideally P(0 | theta=0) = 1 exactly (perfect constructive interference,
    the DV analog of a perfectly known/strong LO). Noise contracts this
    toward 0.5 (fully mixed outcome). The visibility
        V_hat = 2*P(0|theta=0) - 1
    is the empirical attenuation factor -- exactly the role |<b>| plays in
    the thesis's Var(delta(phi)) = |<b>|^2 Var_signal(phi) + Var_LO(phi).
    """
    p0_ref = p0_given_theta(circuit_fn, 0.0, shots, noise_model, **kwargs)
    return 2 * p0_ref - 1


# ----------------------------------------------------------------------------
# Main sweep
# ----------------------------------------------------------------------------

def main():
    theta0_ramsey = np.pi / 2
    shots = 20000
    repeats = 4
    N_values = np.arange(1, 7)
    noise_model = build_noise_model(p_depol=0.01, p_dephase=0.01)

    qfi_sql = N_values * 1.0
    qfi_heisenberg = N_values ** 2.0

    cfi_raw_ramsey, cfi_corrected_ramsey = [], []
    cfi_raw_ghz, cfi_corrected_ghz = [], []
    visibility_ramsey, visibility_ghz = [], []

    for n in N_values:
        theta0_ghz = np.pi / (2 * n)
        eps_ghz = min(0.05, theta0_ghz / 2)

        raw_r_samples, raw_g_samples = [], []
        vis_r_samples, vis_g_samples = [], []
        for _ in range(repeats):
            # --- Calibration step (thesis Table 4.1, Steps 1-2) ---
            vis_r_samples.append(measure_visibility(ramsey_circuit, shots, noise_model))
            vis_g_samples.append(measure_visibility(ghz_ramsey_circuit, shots,
                                                      noise_model, n=n))
            # --- Signal step (thesis Table 4.1, Step 3) ---
            raw_r_samples.append(
                classical_fisher_information(ramsey_circuit, theta0_ramsey, shots,
                                              noise_model=noise_model))
            raw_g_samples.append(
                classical_fisher_information(ghz_ramsey_circuit, theta0_ghz, shots,
                                              noise_model=noise_model, eps=eps_ghz, n=n))

        v_r = float(np.mean(vis_r_samples))
        v_g = float(np.mean(vis_g_samples))
        f_raw_r = n * float(np.mean(raw_r_samples))   # n independent qubits
        f_raw_g = float(np.mean(raw_g_samples))

        visibility_ramsey.append(v_r)
        visibility_ghz.append(v_g)
        cfi_raw_ramsey.append(f_raw_r)
        cfi_raw_ghz.append(f_raw_g)

        # --- Correction step (thesis Eq. 4.3: divide by |<b>|^2) ---
        v_r_safe = max(v_r, 0.05)  # guard the same numerical-instability
        v_g_safe = max(v_g, 0.05)  # regime the thesis flags in Condition 2
        cfi_corrected_ramsey.append(f_raw_r / v_r_safe ** 2)
        cfi_corrected_ghz.append(f_raw_g / v_g_safe ** 2)

        print(f"N={n}: "
              f"V_ramsey={v_r:5.2f}  QFI_SQL={n:5.1f}  "
              f"CFI_raw={f_raw_r:6.2f}  CFI_corrected={cfi_corrected_ramsey[-1]:6.2f}  |  "
              f"V_ghz={v_g:5.2f}  QFI_Heis={n**2:6.1f}  "
              f"CFI_raw={f_raw_g:6.2f}  CFI_corrected={cfi_corrected_ghz[-1]:6.2f}")

    # ------------------------------------------------------------------
    # Recovered-fraction summary
    # ------------------------------------------------------------------
    print("\nFraction of lost Fisher information recovered by calibration (GHZ):")
    for n, qfi, raw, corr in zip(N_values, qfi_heisenberg, cfi_raw_ghz, cfi_corrected_ghz):
        lost = qfi - raw
        recovered = corr - raw
        frac = (recovered / lost * 100) if lost > 0 else float("nan")
        print(f"  N={n}: lost={lost:6.2f}, recovered={recovered:6.2f}  ({frac:5.1f}% of the gap)")

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.plot(N_values, qfi_sql, "k--", label="QFI (SQL), $F_Q=N$")
    ax.plot(N_values, qfi_heisenberg, "k-.", label="QFI (Heisenberg), $F_Q=N^2$")
    ax.plot(N_values, cfi_raw_ghz, "s-", color="#d8763b", label="CFI, GHZ (raw, noisy)")
    ax.plot(N_values, cfi_corrected_ghz, "^-", color="#2c8f5b",
            label="CFI, GHZ (calibration-corrected)")
    ax.set_yscale("log")
    ax.set_xlabel("Number of qubits, N")
    ax.set_ylabel("Fisher information (log scale)")
    ax.set_title("GHZ probe: raw vs. calibration-corrected CFI")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    ax = axes[1]
    ax.plot(N_values, visibility_ramsey, "o-", color="#3b7dd8", label="Visibility, Ramsey")
    ax.plot(N_values, visibility_ghz, "s-", color="#d8763b", label="Visibility, GHZ")
    ax.axhline(0.05, color="gray", linestyle=":", linewidth=1,
               label="Numerical-instability floor")
    ax.set_xlabel("Number of qubits, N")
    ax.set_ylabel(r"Fringe visibility $\hat{V} = 2P(0|\theta_{ref})-1$")
    ax.set_title("Calibration measurement (DV analog of $|\\langle \\hat{b}\\rangle|$)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("LO-Agnostic-Style Calibration: Recovering Fisher Information Lost to Noise",
                  fontsize=12)
    fig.tight_layout()
    fig.savefig("calibration_recovery.png", dpi=150)
    print("\nSaved plot to calibration_recovery.png")


if __name__ == "__main__":
    main()
