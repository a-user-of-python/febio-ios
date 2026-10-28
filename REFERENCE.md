# Reference numbers — host proof

Produced 2026-10-28 on Linux (x86-64) by `HostHarness/` driving the
exact app facade (`App/febio_facade.cpp`) through the in-process
FEBioLib API — the same call sequence the iPad app runs
(`FECoreKernel::SetInstance` → `febio::InitLibrary()` →
`FEBioModel::Input` → `febio::SolveModel`), **not** the febio
executable.

- FEBio: **4.13.0**, commit `9605327359ded64ea0d65dd1aeca484fc45a9acd`
- Build: CMake Release, `USE_MKL=OFF` → bundled **Skyline** solver
- Model: `Model/tension-block.feb` (99 nodes, 40 hex8 elements,
  neo-Hookean E=10, ν=0.3, +1.0 mm prescribed x-displacement,
  10 increments)

## Results (the on-device targets)

| Quantity | Host value |
|---|---|
| Solved | **yes — NORMAL TERMINATION** |
| Nodes / elements | 99 / 40 |
| Max displacement magnitude | **1.00083035 mm** |
| Max von Mises stress | **1.03970845** |
| Equilibrium iterations | 20 total (2 per step × 10 steps) |
| Solve wall time (host) | 0.102 s (log total elapsed 0.104 s) |

Sanity checks: the pulled face is prescribed exactly 1.0 mm in x;
the headline magnitude is slightly above 1.0 because corner nodes of
that face also contract laterally (Poisson effect) — sqrt(1² + 2·0.0285²)
≈ 1.00081, matching the computed 1.00083. Von Mises ≈ E·ε = 1.0 in
the small-strain limit; finite-strain neo-Hookean gives 1.0397.

**On-device pass criteria:** Solved OK, max displacement within
1e-6 of 1.00083035 (same code, same model, same solver — only the
CPU differs), max von Mises within 1e-4 relative. Solve time on the
iPad will differ and is reported, not judged.
