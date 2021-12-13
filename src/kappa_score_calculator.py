###
### Kappa Score Calculator  
###

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
import string
import config


def normalize_doi(x):
    """
    Normalizes the DOIs to a URL.
    """
    x = x.strip()

    # extract everything after 10.
    temp_doi = ""
    find_available = False

    for i in range(len(x)):
        if x[i:i+3] == "10.":
            temp_doi = x[i:]
            find_available = True
            break

    if find_available:
        x = f'https://doi.org/{temp_doi}'
    else:
        return False

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


def cal_kappa(table, rater):
    observed_agreement = 0

    sum_y = 0
    sum_n = 0
    count_row = 0
    for index, row in table.iterrows():
        observed_agreement += ((row['y']**2-row['y'])+(row['n']**2-row['n']))/(rater*(rater-1))

        sum_y += row['y']
        sum_n += row['n']
        count_row += 1

    observed_agreement = observed_agreement/count_row
    expected_agreement = (sum_y/(rater*count_row))**2+(sum_n/(rater*count_row))**2

    return (observed_agreement-expected_agreement)/(1-expected_agreement + 1E-32)


def main():

    with open("kappa_scores_results.csv", 'w', encoding="latin-1", newline='') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['issue_id', 'submissions', 'available submissions', 'paper doi', 'kappa'])

        for i in config.ISSUE_LIST:
            print("current in issue", i)
            query_url = f"https://api.github.com/repos/bhermann/DoR/issues/{i}/comments"
            params = {
                "state": "open",
            }
            headers = {'Authorization': f'token {config.TOKEN}'}
            r = requests.get(query_url, headers=headers, params=params)

            result = r.json()

            # start to record links
            links = []

            for comment in result:
                # ignore specified comments in the config.py file
                if str(comment["id"]) in config.IGNORED_COMMENTS:
                    print(F">>> Ignored comment: {comment['html_url']}")
                    continue

                link = re.findall(config.FILE_PATTERN, comment['body'])

                if len(link) > 0:
                    user = comment['user']['login']

                    # if user in good_list_70th:
                    current_user = [links[i][0] for i in range(len(links))]
                    if user in current_user:
                        user_idx = current_user.index(user)
                        links[user_idx][1] = link[0]
                    else:
                        links.append([user, link[0]])

            # record submissions
            submissions = len(links)

            # initialize storage for reuse in each issue
            cur_groups = {}

            # initialize available submissions
            available_submission = 0

            # process each file in the links list
            for item in links:
                r_file = requests.get(item[1])

                # check if can parse, if not, skip
                try:
                    df = pd.read_csv(
                        StringIO(r_file.content.decode('latin-1')), low_memory=False
                    )
                except pd.errors.ParserError:
                    print(F">>> Parse error in issue {comment['html_url']} ")
                    continue

                df.columns = [x.strip() for x in df.columns]
                df.columns = [x.lower() for x in df.columns]

                # check if unique paper_doi greater than 10. If yes, then paper_doi has something wrong and we discard
                try:
                    unique_paper_doi = []
                    for index, row in df.iterrows():
                        if row['paper_doi'] not in unique_paper_doi:
                            unique_paper_doi.append(row['paper_doi'])

                    if len(unique_paper_doi) > config.WP_SIZE:
                        print(F">>> file on {comment['html_url']} contains more than {config.WP_SIZE} papers")
                        continue
                except KeyError:
                    continue

                # dump rows with no paper_doi (reusing DOI)
                try:
                    df.dropna(axis=0, inplace=True, subset=['paper_doi'])
                except KeyError as err:
                    print(F">>> Error in dumping paper_doi {comment['html_url']} * error:", err)

                # Normalize the paper DOIs
                try:
                    temp_doi = []
                    find_broken = False

                    for x in df['paper_doi']:
                        if not normalize_doi(x):
                            find_broken = True
                        else:
                            temp_doi.append(normalize_doi(x))

                    if find_broken:
                        print(F">>> file on ({comment['html_url']}) has broken DOI")
                        continue
                    else:
                        df['paper_doi'] = temp_doi
                except:
                    print(F">>> Error in normalizing paper_doi {comment['html_url']} * error:", err)
                    continue

                # now at this step, the file can process
                available_submission += 1

                groups = df.groupby('paper_doi')

                try:
                    for doi, group in groups:
                        unique_citation = np.unique(group['citation_number'].dropna())

                        updated_citation = []
                        for c in unique_citation:
                            # remove strings with no number
                            if not any(char.isdigit() for char in str(c)):
                                continue

                            # split some citations with "," / ";" / " " / "-"
                            if len(str(c).split(",")) > 1:
                                for cc in str(c).split(","):
                                    updated_citation.append(cc.strip())
                            elif len(str(c).split(";")) > 1:
                                for cc in str(c).split(";"):
                                    updated_citation.append(cc.strip())
                            elif len(str(c).split(" ")) > 1:
                                for cc in str(c).split(" "):
                                    updated_citation.append(cc.strip())
                            elif len(str(c).split("-")) > 1:
                                for cc in str(c).split("-"):
                                    updated_citation.append(cc.strip())
                            elif len(re.findall(r'\d+', str(c))) > 1:
                                for cc in re.findall(r'\d+', str(c)):
                                    if cc != "0":
                                        updated_citation.append(cc.strip())
                            else:
                                updated_citation.append(str(c).strip())

                        unique_citation = np.unique(updated_citation)

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
                except KeyError:
                    print("key error")
                except TypeError:
                    print("type error")

            # put 'n' value for each row by submissions - |y|
            for key in list(cur_groups.keys()):
                for index, row in cur_groups[key].iterrows():
                    row['n'] = available_submission - row['y']

            if len(cur_groups) > 0 and available_submission > 1:
                for k, df in cur_groups.items():
                    if not df.empty:
                        kappa = min(1., round(fleiss_kappa(df.to_numpy(), 'uniform'), 2))
                        # kappa = min(1.00, round(cal_kappa(df, available_submission), 3))
                        # print("k: ", k)
                        # print(df)
                        # print("kappa: ", kappa)
                        # print(" ")

                        writer.writerow([i, submissions, available_submission, k, kappa])
   


if __name__ == "__main__":
    main()
