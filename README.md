
# Department of Reuse Scripts

This repository contains the format checker and kappa calculator for DoR contributions.

### `config.py` 
This files contains important variables such as Github API token, issue list, etc. Please modify this file to match your requirements before running below scripts

### `wp_validator.py`
This scripts is a Work Package or CSV file validator. It will check for parsing errors, CSV layout issues, paper DOIs, and etc from the `ISSUE_LIST` list (see `config.py`). It will output a `wp_validation_results.csv` file in which you can find all the information related to faulty CSV files. 

### `kappa_score_calculator.py`
This script calculates the inter-rater reliability of submitted Work Packages. It will output a `kappa_scores_results.csv` file in which you can find the Kappa Scores of all DOIs present the Work Package list.

# Acknowledgement 
This repository is fork from **XiaoLing941212** original work on [DoR Scripts](https://github.com/XiaoLing941212/DoR_students).
