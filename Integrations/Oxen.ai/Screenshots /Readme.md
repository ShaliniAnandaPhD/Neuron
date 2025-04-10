## 📁 : **Original Dataset & RedTeam Corruption**

### Name: `1-original_and_corrupted_inputs`

1. **Initial Dataset Load (`heart.csv`)**  
   Displays the original dataset as imported — includes all 14 clinical fields with no alterations.

2. **Basic Stats View of Original Data**  
   Summary statistics like mean, median, and distribution across features (age, thal, cp, etc.).

3. **Null & Invalid Detection Output**  
   Diagnostic report showing missing values in `ca` and `thal`, plus detection of `thal=0` as invalid.

4. **Outlier Detection (Age 167)**  
   Outlier warning on biologically implausible age entries, flagged by inspection logic.

5. **RedTeam CLI – Corruption Triggered**  
   Execution of `neuron redteam`, simulating realistic clinical data drift and logical inconsistencies.

6. **RedTeam Output Summary**  
   Console printout summarizing number of corruptions per feature and type (categorical, numerical, logical).

7. **Corrupted Dataset Profile View**  
   Visual snapshot of the corrupted dataset’s structure and corrupted fields preview.

8. **Drift Detection: Feature Shift Summary**  
   Shows changes in mean, standard deviation, and entropy for features affected by red teaming.

9. **Corrupted Dataset Raw Sample Rows**  
   Table snippet including anomalous entries such as extremely low `chol` and malformed `thal` values.

10. **Schema Mismatch Report**  
   Report comparing original vs. corrupted schemas — includes newly introduced nulls and encoding mismatches.

---

## 📁 **Neuron Enhancement & Validation**

### Name: `2-enhancement_and_validation`

1. **Inspection Agent Issue Summary**  
   Result of `neuron inspect` showing nulls, distribution anomalies, and recommendations for repair.

2. **Enhancement Applied (Fix Log)**  
   Console output listing the applied fixes — imputation, normalization, encoding correction.

3. **Risk Score Engineering Explanation**  
   Visual showing logic for `combined_risk_score` and its contributing features/weights.

4. **Before vs. After Accuracy Report**  
   Shows performance gain after data enhancement: accuracy improves by +2.9%.

5. **Clean Dataset Preview with Risk Score**  
   Post-enhancement dataset showing new column and absence of nulls/invalids.

---

## 📁 **Version Control & Impact Tracking**

### Name: `3-version_control_and_diff_tracking`

1. **Oxen Init & Commit History**  
   Shows the sequential commit log for all dataset stages, beginning with `oxen init`.

2. **Oxen Diff Output: Structural & Statistical**  
   Highlights additions (e.g. risk score column), fixes, and row-level changes across versions.

3. **Metric Comparison Table**  
   F1, Precision, Recall, and Accuracy before and after enhancement — mapped to commit history.

4. **Oxen Web Dataset Card**  
   Public view of the dataset hosted on Oxen Hub, showing metadata and version history.

5. **Final Push Confirmation**  
   Screenshot confirming successful push and availability of the final dataset version.
