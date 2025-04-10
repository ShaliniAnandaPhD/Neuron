##  **Original Dataset & RedTeam Corruption**

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
