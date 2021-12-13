###
### config file used in other scripts
###

# >>> your personal Github API token
TOKEN = "" 

# REGEX pattern for detecting csv files in the comment section
FILE_PATTERN = '\[.*\]\((https:\/\/github.com\/bhermann\/DoR\/files\/.*)\)'


# >>> add issue id in the list
# EXAMPLE:
# issues from (#243 - #249) and  (#294 - #318)
#             (ma   - mg  )      (ca   - cz)
ISSUE_LIST = list(range(243, 250)) + list(range(294, 319))

# >>> comments IDs (as string values) to ignore from processing
# EXAMPLE: 
IGNORED_COMMENTS = ["973784087", "974563006", "974566997", "974579019"]

# >>> set to false if you don't want to see __IGNORED_COMMENT__ flags in the output file
REPORT_IGNORED_COMMENTS = True

# minimum number of columns that the CSV files should contain
MIN_REQUIRED_COL_COUNT = 8

# expected number of papers in each working package 
WP_SIZE = 10
