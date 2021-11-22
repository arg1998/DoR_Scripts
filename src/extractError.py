import requests
import os
import re
from io import StringIO
import pandas as pd
import csv
import numpy as np
import math
import matplotlib.pyplot as plt

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


# personal token, change it
token = "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"

# file regression
FILE_REGEX = '\[.*\]\((https:\/\/github.com\/bhermann\/DoR\/files\/.*)\)'
# FILE_REGEX = '\[.*\]\((https:\/\/github.com\/XiaoLing941212\/DoR-CSC510\/files\/.*)\)'

with open("hw3_comment_regrade_hw3.csv", 'w', newline='') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(['issue_id', 'user', 'link', 'time', 'has_error', 'fb_parse', 'fb_gh_id', 'fb_paper_doi',
                     'fb_reuse_type', 'fb_comment', 'fb_citation_number', 'fb_reused_doi', 'fb_alt_url', 'fb_page_num',
                     'fb_extra'])

    # add issue id in the list
    # issue_list = [267, 254, 253, 252, 251, 250, 240, 239, 238, 237, 201, 200, 199, 198, 197, 196, 195, 194,
    #               193, 192, 191, 190, 189, 188, 187, 186, 185, 176, 175, 174, 173, 172, 171, 170, 169, 168,
    #               167, 166, 165, 164, 163, 158, 157, 156, 155, 154, 153, 152, 151, 150, 149, 148, 147, 146,
    #               145, 144, 143, 142, 141, 140, 139, 138, 137, 136, 135, 134, 133, 132, 131, 130, 129, 128,
    #               127, 126, 125, 124, 123, 122, 121, 120, 119, 118, 117, 116, 115, 114, 113, 112, 111, 110,
    #               109, 108, 107, 106, 105, 104, 103, 101, 100, 99, 98]
    issue_list = [153]

    for i in issue_list:
        print("current in issue", i)
        query_url = f"https://api.github.com/repos/bhermann/DoR/issues/{i}/comments"
        # query_url = f"https://api.github.com/repos/XiaoLing941212/DoR-CSC510/issues/{i}/comments"

        params = {
            "state": "open",
        }
        headers = {'Authorization': f'token {token}'}
        r = requests.get(query_url, headers=headers, params=params)

        result = r.json()

        # loop comment in the current issue
        for comment in result:
            link = re.findall(FILE_REGEX, comment['body'])

            if len(link) > 0:
                # print(link)
                write_row = ["" for _ in range(15)]
                # initialize error
                has_error = 0

                # record if index error
                index_error = 0

                # record github issue id, user information and url
                write_row[0] = i
                write_row[1] = comment['user']['login']
                file_url = link[0]
                write_row[2] = file_url

                # record comment last update time
                update_time = comment['updated_at']
                hours = int(update_time[11:13]) - 4
                if hours == -1:
                    hours = 23
                elif hours == -2:
                    hours = 22
                elif hours == -3:
                    hours = 21
                elif hours == -4:
                    hours = 20

                update_time = update_time[:11] + str(hours) + update_time[13:]
                write_row[3] = update_time

                # check 1. if uploaded file can be parsed into Pandas dataframe.
                r_file = requests.get(file_url)
                try:
                    df = pd.read_csv(
                        StringIO(r_file.content.decode('latin-1')), low_memory=False
                    )
                except pd.errors.ParserError as err:
                    has_error = 1
                    print('Parse error in issue ', i)
                    write_row[5] = "Parse error, please check your file format."
                    write_row[4] = str(has_error)
                    writer.writerow(write_row)
                    continue

                df.columns = [x.strip() for x in df.columns]
                df.columns = [x.lower() for x in df.columns]

                # check 2. if gh_id is named correctly, and no empty cell in gh_id
                try:
                    if "gh_id" not in df.columns[0]:
                        has_error = 1
                        write_row[6] = write_row[6] + "Column title 'gh_id' is not named correctly or not in the correct index. "

                    if df[df.columns[0]].isnull().values.any():
                        has_error = 1
                        write_row[6] = write_row[6] + "There exists empty cell(s) in gh_id column, please fill your GitHub id in it."
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 3. if paper_doi is named correctly, no empty cell in paper_doi, and paper_doi is in correct format
                try:
                    if "paper_doi" != df.columns[1].strip():
                        has_error = 1
                        write_row[7] = write_row[7] + "Column title 'paper_doi' is not named correctly or not in the correct index. "

                    if df[df.columns[1]].isnull().values.any():
                        has_error = 1
                        write_row[7] = write_row[7] + "There exists empty cell(s) in paper_doi column, please put paper doi in it. "

                    unique_paper_doi = []
                    for index, row in df.iterrows():
                        if row['paper_doi'] not in unique_paper_doi:
                            unique_paper_doi.append(row['paper_doi'])

                    if len(unique_paper_doi) > 11:
                        has_error = 1
                        write_row[7] = write_row[7] + "Your paper_doi shows more than 10 papers. Please check if you copy paper_doi correctly. "

                    for _, row in df.iterrows():
                        temp_content = str(row[df.columns[1]]).strip()
                        if not temp_content == "nan":
                            if not temp_content.startswith("http") and not temp_content.startswith("10."):
                                print("content: ", temp_content)
                                has_error = 1
                                write_row[7] = write_row[7] + "Paper doi should start with either http(s):// or 10.xxxxx, please fix it."
                                break
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 4. if reuse_type is named correctly, and no empty cell in reuse_type
                try:
                    if "reuse_type" != df.columns[2].strip():
                        has_error = 1
                        write_row[8] = write_row[8] + "Column title 'reuse_type' is not named correctly or not in the correct index. "

                    if df[df.columns[2]].isnull().values.any():
                        has_error = 1
                        write_row[8] = write_row[8] + "There exists empty cell(s) in reuse_type column, please put reuse type in it."
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 5. if comment is named correctly
                try:
                    if "comment" != df.columns[3].strip():
                        has_error = 1
                        write_row[9] = write_row[9] + "Column title 'comment' is not named correctly or not in the correct index."
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 6. if citation_number is named correctly
                try:
                    if "citation_number" != df.columns[4].strip():
                        has_error = 1
                        write_row[10] = write_row[10] + "Column title 'citation_number' is not named correctly or not in the correct index."
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 7. if reused_doi is named correctly, and if format of doi is correct
                try:
                    if "reused_doi" != df.columns[5].strip():
                        has_error = 1
                        write_row[11] = write_row[11] + "Column title 'reused_doi' is not named correctly or not in the correct index. "

                    for _, row in df.iterrows():
                        temp_content = str(row[df.columns[5]]).strip()
                        if not temp_content == "nan" and not temp_content == "":
                            if not temp_content.startswith("http") and not temp_content.startswith("10."):
                                has_error = 1
                                write_row[11] = write_row[11] + "Reused doi should start with either http(s):// or 10.xxxxx, please fix it."
                                break
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 8. if alt_url is named correctly
                try:
                    if "alt_url" != df.columns[6].strip():
                        has_error = 1
                        write_row[12] = write_row[12] + "Column title 'alt_url' is not named correctly or not in the correct index. "
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 9. whether reused_doi or alt_url is filled
                try:
                    for _, row in df.iterrows():
                        temp_content = str(row[df.columns[5]]).strip()
                        if temp_content == "nan" or temp_content == "":
                            compare_content = str(row[df.columns[6]]).strip()

                            if compare_content == "nan" or compare_content == "":
                                has_error = 1
                                write_row[11] = write_row[11] + "Both reused_doi and alt_url are empty, please fill at least one."
                                write_row[12] = write_row[12] + "Both reused_doi and alt_url are empty, please fill at least one."
                                break
                except IndexError:
                    print("Key error")
                    index_error = 1

                # check 10. whether page_num is named correctly and is filled
                try:
                    if "page_num" != df.columns[7].strip():
                        has_error = 1
                        write_row[13] = write_row[13] + "Column title 'page_num' is not named correctly or not in the correct index. "
                except IndexError:
                    print("Key error")
                    index_error = 1

                # if df[df.columns[7]].isnull().values.any():
                #     has_error = 1
                #     write_row[13] = write_row[13] + "There exists empty cell(s) in page_num column, please put conference page number for each reuse."

                # check 11. if entire csv has index error.
                if index_error == 1:
                    has_error = 1
                    write_row[14] = write_row[14] + "You format has big problems. Please check correct format and modify your result."

                write_row[4] = str(has_error)

                writer.writerow(write_row)
