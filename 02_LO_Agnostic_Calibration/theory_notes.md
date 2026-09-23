# LO-Agnostic-Style Calibration for Entangled Sensing Probes
### Recovering Fisher information lost to decoherence in GHZ phase estimation, using the thesis's own calibration logic

Author: Dhrithi Maria
Second companion project to: *Balanced Homodyne Detection without Coherent State Local Oscillator* (M.Sc. Thesis, Universität Paderborn, 2026)
Builds directly on Project 1: *Fisher Information Limits for Phase Estimation* (`01-fisher-information-limits/`)

---

## 1. The problem this project solves

Project 1 showed that a GHZ-entangled N-qubit probe achieves Heisenberg-scaling Fisher information (F_Q = N²) under ideal conditions, but that this advantage visibly erodes under realistic depolarizing/dephasing noise — the entanglement that buys precision also buys extra noise sensitivity. That result was left as an open question: *how much of the lost Fisher information can be recovered, without assuming a specific noise model, using only calibration measurements?*

This is exactly the structural problem the thesis solves for balanced homodyne detection, and the thesis's own machinery — the **law of total variance** decomposition and the **vacuum-substitution calibration procedure** (Ch. 4) — turns out to translate almost directly into the discrete-variable setting.

---

## 2. The thesis's calibration procedure, recapped exactly

The thesis writes the LO operator as b̂ = ⟨b̂⟩ + Δb̂ and splits the measured difference-photocurrent variance into a clean signal term and a noise term (thesis Eq. 4.2, derived via the law of total variance, Eq. 4.1):

  Var(δ̂(φ)) = |⟨b̂⟩|² Var_signal(φ) + Var_LO(φ)

Crucially, **Var_LO(φ) is never assumed analytically — it is measured directly**, via the calibration procedure of thesis Table 4.1:

| Step | Action |
|---|---|
| 1 | Block the signal input port and replace it with vacuum. |
| 2 | Record the variance of the difference photocurrent; this directly gives Var_LO(φ). |
| 3 | Restore the unknown signal and record the total measured variance Var(δ̂(φ)). |

The pure signal variance is then recovered by simple subtraction and rescaling (thesis Eq. 4.3):

  Var_signal(φ) = [ Var(δ̂(φ)) − Var_LO(φ) ] / |⟨b̂⟩|²

The essential idea: **run a reference measurement with the unknown quantity removed, characterize what the apparatus/noise alone contributes, then subtract it out of the real measurement** — without ever needing to model the noise analytically.

---

## 3. Translating this to the GHZ phase-estimation setting

In Project 1's Ramsey/GHZ circuits, the ideal outcome probability oscillates as

  P_ideal(θ) = ½ ( 1 + cos(kθ) ),  k = 1 (Ramsey) or k = N (GHZ)

Under depolarizing/dephasing noise, this fringe does not shift in frequency — decoherence in these circuits contracts its **amplitude** (the *visibility*, or *contrast*):

  P_noisy(θ) ≈ ½ ( 1 + V · cos(kθ) ),  0 ≤ V ≤ 1

This visibility V plays **exactly the role of the LO mean field ⟨b̂⟩ in the thesis**: it is the multiplicative factor by which noise attenuates the signal-carrying interference term, before any additive noise floor is considered. The correspondence is direct:

| Thesis quantity | This project's analog |
|---|---|
| LO mean field \|⟨b̂⟩\| (interference amplitude) | Fringe visibility V (oscillation amplitude) |
| Blocking the signal, substituting vacuum (Table 4.1, Step 1) | Running the circuit at a known reference angle θ_ref = 0 under the same noise channel |
| Measuring Var_LO(φ) directly from the vacuum run | Measuring the visibility loss directly from the θ_ref = 0 run: V̂ = 2·P_noisy(0) − 1 |
| Restoring the signal, measuring Var(δ̂(φ)) (Step 3) | Restoring the true unknown θ, measuring the noisy fringe / raw CFI as in Project 1 |
| Var_signal(φ) = [Var(δ̂(φ)) − Var_LO(φ)] / \|⟨b̂⟩\|² | CFI_corrected = CFI_raw / V̂² |
| Protocol requires no assumption about the LO's quantum state (Ch. 3–4) | Protocol requires no assumption about the noise channel's microscopic form — only that it is stationary between the calibration run and the real run |

The division by \|⟨b̂⟩\|² in the thesis and the division by V̂² here play the same mathematical role: both terms are the *square* of an amplitude attenuation factor, because variance (thesis) and Fisher information (here, since F_C ∝ (dP/dθ)²) both scale quadratically with the underlying signal amplitude.

### 3.1 Why this is only a *partial* recovery — and the thesis says so too

The thesis's Condition 2 (§3.2, Eq. 3.5) notes that when \|⟨b̂⟩\| is small, the subtraction in Eq. 4.3 involves a difference of two nearly-equal numbers and becomes numerically unstable, even though it is theoretically exact. The same limitation appears here: when depolarizing/dephasing noise pushes V toward the fully-mixed limit (P → ½ regardless of θ), dividing by V̂² amplifies statistical shot noise in the CFI estimate, since a small, noisily-measured V sits in the denominator. This project reproduces that same failure mode as N grows and the GHZ state's visibility collapses faster than the single-qubit Ramsey visibility — the DV counterpart of the thesis's own "practical signal-to-noise requirement."

---

## 4. What `noise_calibration.py` implements

1. Reuses the Ramsey and GHZ circuit builders and the depolarizing + dephasing noise model from Project 1.
2. **Calibration step**: for each N, runs the circuit at the known reference angle θ_ref = 0 under the noise model and measures the empirical visibility V̂_N = 2·P_noisy(0) − 1 (the DV analog of the vacuum-substitution measurement of Var_LO).
3. **Signal step**: runs the circuit at its true operating point (as in Project 1) and computes the raw (uncorrected) noisy CFI.
4. **Correction step**: rescales the raw CFI by 1/V̂_N², producing a calibrated CFI estimate, and compares all three curves — ideal QFI, raw noisy CFI, and calibration-corrected CFI — against N.
5. Quantifies the fraction of lost Fisher information recovered by calibration, and shows where the correction itself becomes unreliable (large N, low visibility), reproducing the thesis's own practical signal-to-noise caveat (§3.2, Condition 2) in the discrete-variable setting.

## 5. How to present this on your CV / portfolio

Frame it as: *"Designed and implemented a calibration protocol for entangled quantum sensing probes under decoherence, adapting the vacuum-substitution / law-of-total-variance methodology from my thesis's continuous-variable homodyne framework to recover Fisher information lost to noise in GHZ-based phase estimation — including reproducing, in the discrete-variable setting, the same practical signal-to-noise limitation the thesis identifies for low local-oscillator amplitude."*

This is the strongest possible portfolio narrative: two projects that are not independent demos, but a single coherent research program — extend the thesis's precision-limit question to the gate model (Project 1), then extend the thesis's own calibration solution to the same setting (Project 2) — exactly the kind of continuity a hiring committee or PhD supervisor is looking for.
