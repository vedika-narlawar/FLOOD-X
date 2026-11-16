# Model evaluation
No supervised model exists; **no accuracy, ROC, PR-AUC or confusion matrix is reported, by design.** `GET /api/model/metrics` returns `status: not_applicable` with the reason. The only quantitative evaluation is the weight-sensitivity analysis (`artifacts/metrics/sensitivity.json`, produced when real features exist) and unit tests of monotonicity, missing-input handling, reproducibility and category construction.
Path A (supervised) would require labelled observations, spatial CV / separate-event validation, calibration checks — not implemented.
