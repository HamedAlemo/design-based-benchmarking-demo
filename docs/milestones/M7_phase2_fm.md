# M7 Phase 2: foundation-model probe maps (optional, not in the first run)

Do not start M7 unless the PI asks. It adds 8 to 12 models to strengthen H3 and connect to the representation-probing work.

## Outline

1. Models: frozen embeddings from several geospatial foundation models (for example Prithvi EO 2.0, Clay, AlphaEarth satellite embeddings, plus one or two others), all from 2021 imagery.
2. Training set: a fixed set of labeled cells outside MD and DE (for example southern Pennsylvania and northern Virginia), drawn from the same Chesapeake reference, identical for all models. Probes are a logistic regression and a k-NN classifier on the embeddings.
3. Prediction: wall-to-wall maps over the full extent on the analysis grid. Crosswalk is the identity (they predict the 5 classes directly).
4. Add the maps as new cell-table columns and append to the per-unit arrays. Rebuild only what depends on them (truth, unit arrays, F strata). Keep the D strata unchanged: they stay based on the three phase 1 products, so the FMs test the "new model on an existing shared sample" case directly.
5. Rerun M5 and M6 with K = 3 + new models, as a separate results folder. HYPOTHESES.md stays as is; any phase 2 criteria go in a new HYPOTHESES_phase2.md, written and frozen before running.
