###
### Work Package (CSV File) Validator 
###

import requests
import os
import re
from io import StringIO
import pandas as pd
import csv
import numpy as np
import math
import matplotlib.pyplot as plt
import config
from dateutil.parser import isoparse


def normalize_doi(x):
    """
    Normalizes the DOIs to a URL.
    """
    x = x.strip()
    if not x.startswith('http'):
        x = f'https://doi.org/{x}'

    return x


def normalize_index(x):
    """
    Normalizes a citation. Adds in square brackets on each side
    and removes spacing on the sides. Also converts to a str.
    """
    if not isinstance(x, str):
        if not math.isnan(x):
            x = str(int(x))
        else:
            x = str(x)

    x = x.strip()

    if len(x) == 0:
        return x
    if x[0] != '[':
        x = f'[{x}'
    if x[-1] != ']':
        x = f'{x}]'
    return x


found_errors = pd.DataFrame(columns=['issue_id', 'comment_id', 'user_id', 'csv_file', 'message', "url", "date"])


def log_error(error_code, issue, comment, message):
    global found_errors

    print(F"---------------{error_code}---------------")
    print(F">>> issue id\t:\t {issue}")
    print(F">>> comment id\t:\t{comment['id']}")
    print(F">>> user id\t:\t{comment['user']['login']}")
    print(F">>> message\t:\t{message}")
    print(F"------------------------------------------")

    csv_files = re.findall(r'[wWpP]{2}[\s\-a-zA-Z]+[.csv]+', comment["body"])
    file_name = None
    if len(csv_files) > 0:
        file_name = csv_files[0]
    date = isoparse(comment["created_at"])
    
    found_errors = found_errors.append({'issue_id': issue,
                                        'comment_id': comment['id'],
                                        'user_id': comment['user']['login'],
                                        'message': message,
                                        'csv_file': file_name,
                                        "url": comment["html_url"],
                                        "date": date}, ignore_index=True)


for i in config.ISSUE_LIST:
    print("current in issue", i)
    query_url = f"https://api.github.com/repos/bhermann/DoR/issues/{i}/comments"

    params = {
        "state": "open",
    }
    headers = {'Authorization': f'token {config.TOKEN}'}
    r = requests.get(query_url, headers=headers, params=params)

    result = r.json()

    # loop comment in the current issue
    for comment in result:
        if str(comment["id"]) in config.IGNORED_COMMENTS:
            if config.REPORT_IGNORED_COMMENTS: 
                log_error(0, i, comment, "__IGNORED_COMMENT__")
            continue
        
        link = re.findall(config.FILE_PATTERN, comment['body'])

        if len(link) > 0:

            file_url = link[0]
            # check 1. if uploaded file can be parsed into Pandas dataframe.
            r_file = requests.get(file_url)
            try:
                csv_text_stream = StringIO(r_file.content.decode('latin-1'))
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(csv_text_stream.readline()).delimiter
                csv_text_stream.seek(0)

                df = pd.read_csv(csv_text_stream, low_memory=False, sep=delimiter)
            except pd.errors.ParserError as err:
                log_error(1, i, comment, "Parse error, please check your file format.")
                continue

            df.columns = [x.strip() for x in df.columns]
            df.columns = [x.lower() for x in df.columns]

            if len(df.columns) < config.MIN_REQUIRED_COL_COUNT:
                log_error(2, i, comment, F"number of columns are less than {config.MIN_REQUIRED_COL_COUNT}; this file has {len(df.columns)} column(s)")
                continue

            # check 2. if gh_id is named correctly, and no empty cell in gh_id
            try:
                if "gh_id" not in df.columns[0]:
                    log_error(3, i, comment, F"'Column 'gh_id' not found or is in the wrong column index")
                if df[df.columns[0]].isnull().values.any():
                    log_error(4, i, comment, "There are empty cell(s) in 'gh_id' column")
            except IndexError:
                print("Key error")

            # check 3. if paper_doi is named correctly, no empty cell in paper_doi, and paper_doi is in correct format
            try:
                if "paper_doi" != df.columns[1].strip():
                    log_error(5, i, comment, F"Column 'paper_doi' not found or is in the wrong column index")

                if df[df.columns[1]].isnull().values.any():
                    log_error(17, i, comment, "There are empty cell(s) in 'paper_doi' column")

                unique_paper_doi = []
                for index, row in df.iterrows():
                    if row['paper_doi'] not in unique_paper_doi:
                        unique_paper_doi.append(row['paper_doi'])

                if len(unique_paper_doi) > config.WP_SIZE:
                    log_error(6, i, comment, F"Your 'paper_doi' column shows more than {config.WP_SIZE} papers")

                for _, row in df.iterrows():
                    temp_content = str(row[df.columns[1]]).strip()
                    if not temp_content == "nan":
                        if not temp_content.startswith("http") and not temp_content.startswith("10."):
                            log_error(7, i, comment, "content in the'paper_doi' column should start with either 'http(s)://' or '10.xxxxx'")
                            break
            except Exception:
                print("Key error")

            # check 4. if reuse_type is named correctly, and no empty cell in reuse_type
            try:
                if "reuse_type" != df.columns[2].strip():
                    log_error(8, i, comment, "Column 'reuse_type' not found or is in the wrong column index")

                if df[df.columns[2]].isnull().values.any():
                    log_error(9, i, comment, F"There exists empty cell(s) in reuse_type column")
            except IndexError:
                print("Key error")

            # check 5. if comment is named correctly
            try:
                if "comment" != df.columns[3].strip():
                    log_error(10, i, comment, F"Column 'comment' not found or is in the wrong column index")
            except IndexError:
                print("Key error")

            # check 6. if citation_number is named correctly
            try:
                if "citation_number" != df.columns[4].strip():
                    log_error(11, i, comment, "Column 'citation_number' not found or is in the wrong column index")
            except IndexError:
                print("Key error")

            # check 7. if reused_doi is named correctly, and if format of doi is correct
            try:
                if "reused_doi" != df.columns[5].strip():
                    log_error(12, i, comment, "Column 'reused_doi' not found or is in the wrong column index")

                for _, row in df.iterrows():
                    temp_content = str(row[df.columns[5]]).strip()
                    if not temp_content == "nan" and not temp_content == "":
                        if not temp_content.startswith("http") and not temp_content.startswith("10."):
                            log_error(13, i, comment, "content in the'reused_doi' column should start with either 'http(s)://' or '10.xxxxx'")
                            break
            except IndexError:
                print("Key error")

            # check 8. if alt_url is named correctly
            try:
                if "alt_url" != df.columns[6].strip():
                    log_error(14, i, comment, F"Column 'alt_url' column not found or is in the wrong column index")

            except IndexError:
                print("Key error")

            # check 9. whether reused_doi or alt_url is filled
            try:
                for _, row in df.iterrows():
                    temp_content = str(row[df.columns[5]]).strip()
                    if temp_content == "nan" or temp_content == "":
                        compare_content = str(row[df.columns[6]]).strip()
                        if compare_content == "nan" or compare_content == "":
                            has_error = 1
                            log_error(15, i, comment, "Both 'reused_doi' and 'alt_url' are empty")
                            break
            except IndexError:
                print("Key error")

            # check 10. whether page_num is named correctly and is filled
            try:
                if "page_num" != df.columns[7].strip():
                    log_error(16, i, comment, F"Column 'page_num' not found or is in the wrong column index")
            except IndexError:
                print("Key error")

            # if df[df.columns[7]].isnull().values.any():
            #     has_error = 1
            #     write_row[13] = write_row[13] + "There exists empty cell(s) in page_num column, please put conference page number for each reuse."

found_errors.to_csv("wp_validation_results.csv")
