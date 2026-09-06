# Plan de integración de PRs

Estado local observado: `#5` corresponde a `feature/android-manual-capture`, `#7` a `feature/android-advanced-capture` sobre #5, y la evaluación parte de `main` en la referencia disponible. El orden recomendado, tras revisar CI y conflictos en GitHub, es:

1. #5 → `main`.
2. Retarget #7 a `main` y mergear #7 cuando su CI siga verde.
3. Integrar `feature/tfm-final-hardening` sobre #7 después de revisar este worktree.
4. Mantener #6 independiente sobre `main`; retarget solo si los cambios de documentación/evaluación requieren la base final.

Este orden debe confirmarse con los diffs actuales en GitHub porque el entorno no permite `fetch`, commit ni push. No se ha hecho ningún merge.
