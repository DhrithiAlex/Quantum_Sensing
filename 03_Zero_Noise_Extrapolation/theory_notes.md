# Zero-Noise Extrapolation for Quantum Sensing: Recovering Fisher Information via Gate Folding

Author: Dhrithi Maria
Third companion project to: *Balanced Homodyne Detection without Coherent State Local Oscillator* (M.Sc. Thesis, Universität Paderborn, 2026)
Builds on Project 1 (`01-fisher-information-limits/`) and Project 2 (`02-lo-agnostic-calibration/`)

---

## 1. Where this sits in the series

Project 1 established that a GHZ-entangled probe reaches Heisenberg-scaling Fisher information ideally, but loses much of that advantage under decoherence. Project 2 recovered a large fraction of the loss using a **calibration-based** correction — measuring a known reference point and rescaling, directly modelled on the thesis's vacuum-substitution procedure (Ch. 4). This project asks the complementary question: **what does a second, independent error-mitigation strategy recover, and does combining the two do better than either alone?**

The strategy here is **Zero-Noise Extrapolation (ZNE)** via unitary gate folding and Richardson extrapolation — the same family of technique used elsewhere in my portfolio for VQE energy estimation (H₂ dissociation with ideal-vs-noisy-vs-ZNE-corrected curves), now applied to a completely different observable: not an energy expectation value, but a *Fisher information* / measurement-precision quantity.

## 2. Connection to the thesis's own robustness testing

The thesis does not use ZNE, but it does exactly the same conceptual maneuver in a different form: Chapter 5 ("Robustness and verification (stress test)") and Appendix A.2 ("Reconstruction with a Displaced Thermal LO: Excess Classical Noise") deliberately **increase** the noise/excess-noise level in the model and verify that the calibration protocol still recovers the correct signal variance. ZNE runs the same experiment in reverse: it deliberately **amplifies** the circuit noise by a controlled, known factor (via gate folding), measures the resulting degradation at several noise levels, and **extrapolates back to the zero-noise limit** — using the *shape* of the degradation curve itself as the correction, rather than a separate calibration measurement.

| Thesis's robustness testing (Ch. 5, App. A.2) | This project's ZNE |
|---|---|
| Deliberately increase LO noise / excess classical noise to stress-test the protocol | Deliberately amplify circuit noise via unitary gate folding (scale factors λ = 1, 3, 5) |
| Verify the calibration procedure (Ch. 4) still recovers the correct signal variance under the increased noise | Fit the measured probability vs. noise scale and extrapolate to the physically inaccessible λ → 0 (zero-noise) limit |
| Confirms robustness qualitatively across a chosen noise range | Produces a quantitative, per-N corrected Fisher information estimate |

## 3. Method: unitary folding + Richardson extrapolation

For a circuit implementing unitary U, folding replaces U with U (U† U)^k, which is logically identical (U(U†U)^k = U for a perfect, noiseless unitary) but physically accumulates k extra round trips' worth of gate noise. Running at fold factors λ = 1, 3, 5, ... traces out how the measured outcome probability degrades as a function of *injected* noise, and fitting a low-order polynomial in λ and evaluating at λ = 0 estimates what the circuit would have produced with no noise at all — without ever needing a separate calibration circuit or reference measurement, unlike Project 2.

  P_λ(θ) ≈ P_0(θ) + c₁·λ + c₂·λ² + ...   (linear fit used here: P_0 ≈ Richardson extrapolation to λ=0)

The Classical Fisher Information is then recomputed from the extrapolated probabilities at θ₀ − ε, θ₀, θ₀ + ε, exactly as in Projects 1 and 2, but using P_λ→0 in place of the raw noisy P.

## 4. What this project compares

For each N (Ramsey: independent qubits, GHZ: entangled probe), four quantities are computed side by side:

1. **Ideal QFI** (analytic: N for Ramsey/SQL, N² for GHZ/Heisenberg) — the ceiling.
2. **Raw noisy CFI** (Project 1) — the floor, no mitigation.
3. **Calibration-corrected CFI** (Project 2) — mitigation via a reference measurement.
4. **ZNE-corrected CFI** (this project) — mitigation via noise-scaling extrapolation, no reference measurement needed.

This directly answers a question a technical interviewer is likely to ask about any single mitigation result: *"is this specific to your method, or does an independent mitigation strategy agree?"* Having two independent corrections that both substantially close the gap to the ideal QFI is a much stronger result than either correction alone — and, where they disagree, that disagreement is itself informative about each method's blind spots (ZNE assumes a smooth, extrapolable noise-scaling law; calibration assumes a stationary, reproducible reference point — both assumptions can fail in different hardware regimes).

## 5. How to present this on your CV / portfolio

Frame it as: *"Implemented and cross-validated two independent, complementary error-mitigation strategies — reference-based calibration and zero-noise extrapolation via gate folding — for recovering Fisher information lost to decoherence in entangled quantum sensing probes, extending the noise-robustness methodology of my thesis's stress-testing chapter into the discrete-variable, error-mitigation setting."*
