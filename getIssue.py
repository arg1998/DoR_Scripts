import requests
import os
import re
from io import StringIO
import pandas as pd
import csv
import numpy as np
import math
from statsmodels.stats.inter_rater import fleiss_kappa
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

with open("final_result.csv", 'w', newline='') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(['issue_id', 'user', 'link', 'time', 'has_error', 'ready_to_inspect', 'comment'])

    issue_list = [267, 254, 253, 252, 251, 250, 240, 239, 238, 237, 201, 200, 199, 198, 197, 196, 195, 194,
                  193, 192, 191, 190, 189, 188, 187, 186, 185, 176, 175, 174, 173, 172, 171, 170, 169, 168,
                  167, 166, 165, 164, 163, 158, 157, 156, 155, 154, 153, 152, 151, 150, 149, 148, 147, 146,
                  145, 144, 143, 142, 141, 140, 139, 138, 137, 136, 135, 134, 133, 132, 131, 130, 129, 128,
                  127, 126, 125, 124, 123, 122, 121, 120]
    # issue_list = [2]

    final_kappa_result = []

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

        # initialize kappa dictionary
        cur_groups = {}

        # count how many submissions
        submission = 0

        for comment in result:
            link = re.findall(FILE_REGEX, comment['body'])

            if len(link) > 0:
                # initialize error
                has_error = 0

                # initialize process permission
                can_process = 1

                # initialize comment
                feedback = ""

                write_row = [i, comment['user']['login']]
                file_url = link[0]
                write_row.append(file_url)

                # record comment last update time
                update_time = comment['updated_at']
                write_row.append(update_time)

                # read csv into a pd DataFrame
                r_file = requests.get(file_url)
                try:
                    df = pd.read_csv(
                        StringIO(r_file.content.decode('latin-1'))
                    )
                except pd.errors.ParserError as err:
                    print('Parse error in issue ', i)
                    write_row.append(1)
                    write_row.append(0)
                    write_row.append("Parse error")

                    writer.writerow(write_row)
                    continue

                # pre-process the columns
                df.columns = [x.strip() for x in df.columns]

                # check if github id is filled in every row
                try:
                    if df['gh_id'].isnull().values.any():
                        has_error = 1
                        feedback = feedback + "Have empty gh_id. "
                except KeyError:
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "No column gh_id. "

                # check if reusing DOI is filled in every row
                try:
                    if df['paper_doi'].isnull().values.any():
                        has_error = 1
                        feedback = feedback + "Have empty paper_doi. "
                except KeyError:
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "No column paper_doi. "

                # check whether a reuse has reused_doi or alt_url
                try:
                    null_reused_doi = df[df['reused_doi'].isnull()].index.tolist()
                    null_alt_url = df[df['alt_url'].isnull()].index.tolist()

                    if len(np.intersect1d(null_reused_doi, null_alt_url)) != 0:
                        has_error = 1
                        feedback = feedback + "Have reuse with empty reused_doi and alt_url. "
                except KeyError:
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "No column reused_doi or alt_url. "

                # check whether reuse_type is identified
                try:
                    if df['reuse_type'].isnull().values.any():
                        has_error = 1
                        feedback = feedback + "Have empty reuse_type. "
                except KeyError:
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "No column reuse_type. "

                # check whether citation_number is correctly named
                try:
                    if df['citation_number'].isnull().values.any():
                        pass
                except KeyError:
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "Column citation_number named incorrectly"

                # dump rows with no paper_doi (reusing DOI)
                try:
                    df.dropna(axis=0, inplace=True, subset=['paper_doi'])
                except KeyError as err:
                    print(err)

                # Normalize the DOIs
                try:
                    df['paper_doi'] = [normalize_doi(x) for x in df['paper_doi']]
                except KeyError as err:
                    print('In issue ', i, ", paper_doi has something wrong")
                except AttributeError as err:
                    print("In issue ", i, ", paper_doi has wrong entry")
                    has_error = 1
                    can_process = 0
                    feedback = feedback + "Paper_doi has unnormal entries. "

                write_row.append(has_error)
                write_row.append(can_process)
                write_row.append(feedback)

                writer.writerow(write_row)

                if can_process:
                    submission += 1
                    # For each paper, check agreement
                    groups = df.groupby('paper_doi')

                    try:
                        for doi, group in groups:
                            unique_citation = np.unique(group['citation_number'])

                            if doi not in cur_groups:
                                index = unique_citation
                                index = set([normalize_index(x) for x in index])

                                cur_groups[doi] = pd.DataFrame(index=index, columns=['y', 'n'])

                            for artifact in unique_citation:
                                artifact = normalize_index(artifact)
                                if artifact not in cur_groups[doi].index:
                                    cur_groups[doi].loc[artifact, 'y'] = 1
                                    cur_groups[doi].loc[artifact, 'n'] = None
                                else:
                                    if np.isnan(cur_groups[doi].loc[artifact, 'y']):
                                        cur_groups[doi].loc[artifact, 'y'] = 1
                                    else:
                                        cur_groups[doi].loc[artifact, 'y'] += 1
                    except:
                        print(group['citation_number'])

        # put 'n' value for each row by submissions - |y|
        for key in list(cur_groups.keys()):
            for index, row in cur_groups[key].iterrows():
                row['n'] = submission - row['y']

        # kappa
        # kappas = []
        try:
            if len(cur_groups) > 1:
                for k, df in cur_groups.items():
                    kappa = min(1., round(fleiss_kappa(df.to_numpy(), 'uniform'), 2))
                    final_kappa_result.append((k, kappa))
            # elif len(cur_groups) == 1:
            #     for k, df in cur_groups.items():
            #         kappas.append((k, 1))
        except:
            pass

    # group
    plot_list = [['-1 <-> -0.75', 0], ['-0.75 <-> -0.5', 0], ['-0.5 <-> -0.25', 0], ['-0.25 <-> 0', 0],
                 ['0 <-> 0.25', 0], ['0.25 <-> 0.5', 0], ['0.5 <-> 0.75', 0], ['0.75 <-> 1', 0]]

    for item in final_kappa_result:
        if -1 <= item[1] < -0.75:
            plot_list[0][1] += 1
        elif -0.75 <= item[1] < -0.5:
            plot_list[1][1] += 1
        elif -0.5 <= item[1] < -0.25:
            plot_list[2][1] += 1
        elif -0.25 <= item[1] < 0:
            plot_list[3][1] += 1
        elif 0 <= item[1] < 0.25:
            plot_list[4][1] += 1
        elif 0.25 <= item[1] < 0.5:
            plot_list[5][1] += 1
        elif 0.5 <= item[1] < 0.75:
            plot_list[6][1] += 1
        elif 0.75 <= item[1] <= 1:
            plot_list[7][1] += 1

    x = [plot_list[i][0] for i in range(len(plot_list))]
    y = [plot_list[i][1] for i in range(len(plot_list))]

    plt.bar(x, y, width=0.4)

    plt.xlabel("kappa range")
    plt.ylabel("number of papers")
    plt.show()