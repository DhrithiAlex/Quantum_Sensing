# Quantum Sensing & Noise Robustness: From Continuous-Variable Homodyne Detection to the Gate Model

**Dhrithi Maria** — M.Sc. Theoretical Quantum Physics, Universität Paderborn

This repository is a three-part research program extending my M.Sc. thesis, *Balanced Homodyne Detection without Coherent State Local Oscillator* (Universität Paderborn, 2026, advisors: Prof. Dr. Jan Sperling, Prof. Dr. Torsten Meier), from continuous-variable quantum optics into discrete-variable, gate-model quantum computing, implemented in Qiskit.

The thesis develops a complete, LO-state-independent framework for (1) determining how precisely a signal can be extracted from a noisy interference measurement, and (2) recovering that signal's true statistics from noisy data via calibration — without ever assuming the noise source's exact quantum state. The three projects here ask and answer the same two questions in the qubit picture, plus a third: whether an entirely independent error-mitigation strategy agrees.

## The three projects

| # | Project | Question | Thesis analog |
|---|---|---|---|
| 1 | [**Fisher Information Limits for Phase Estimation**](01_Fisher_information_limits/) | What precision is achievable, and what does entanglement buy you? | Squeezed-vacuum signal beating shot noise (Ch. 5) ↔ GHZ entanglement beating the Standard Quantum Limit |
| 2 | [**LO-Agnostic-Style Calibration for Entangled Sensing Probes**](02_LO-Agnostic-Calibration/) | How much of the precision lost to noise can a calibration measurement give back? | Vacuum-substitution calibration procedure (Ch. 4, Table 4.1, Eq. 4.3) ↔ reference-angle visibility calibration |
| 3 | [**Zero-Noise Extrapolation for Quantum Sensing**](03-zero-noise-extrapolation/) | Does an independent mitigation strategy, with no reference measurement, agree with Project 2? | Deliberately-increased-noise stress testing (Ch. 5, App. A.2) ↔ gate folding + Richardson extrapolation |

Each project's `theory_notes.md` includes an explicit, equation-by-equation table mapping its formalism back to the corresponding thesis chapter and equation number — the goal throughout was continuity, not three disconnected demos.

## Key result

A GHZ-entangled N-qubit probe reaches Heisenberg-scaling Fisher information (F ∝ N²) under ideal conditions, but loses much of that advantage under realistic gate noise. Two independent mitigation strategies — a calibration measurement modeled directly on the thesis's own procedure, and zero-noise extrapolation via gate folding — each recover roughly 85-100% of the lost Fisher information, and largely agree with each other:

<p align="center">
  <img src="01-fisher-information-limits/fisher_information_scaling.png" width="48%">
  <img src="03-zero-noise-extrapolation/zne_vs_calibration.png" width="48%">
</p>

## Repository structure

```
quantum-sensing-portfolio/
├── 01-fisher-information-limits/    Project 1: SQL vs. Heisenberg scaling
├── 02-lo-agnostic-calibration/      Project 2: calibration-based noise recovery
├── 03-zero-noise-extrapolation/     Project 3: ZNE-based noise recovery
├── requirements.txt
└── LICENSE
```

Each subdirectory is self-contained and runnable independently: `pip install -r requirements.txt` once at the repo root, then `python3 <script>.py` inside any project folder.

## Requirements

```
qiskit
qiskit-aer
numpy
matplotlib
```

## About

M.Sc. graduate in theoretical quantum physics (Universität Paderborn), thesis on continuous-variable quantum optics / balanced homodyne detection. This repository is part of a job-search portfolio bridging that continuous-variable background to gate-model quantum computing for quantum hardware/software and research roles.
