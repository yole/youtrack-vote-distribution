import requests, os, sys, collections, time, urllib.parse
from datetime import datetime

token_path = os.path.expanduser("~/.youtrack-token")
if not os.path.exists(token_path):
    print("Please follow the instructions at https://www.jetbrains.com/help/youtrack/devportal/authentication-with-permanent-token.html to obtain a YouTrack permanent token")
    print("and save the token to the .youtrack_token file in your home directory.")
    sys.exit(1)

if len(sys.argv) < 3:
    print("Usage:")
    print("  Vote distribution by time: python3 youtrack-vote-distribution.py <server> [month] <issue ID>")
    print("  Recently top voted issues: python3 youtrack-vote-distribution.py <server> report <output file> <query>")
    sys.exit(1)

YOUTRACK_API = sys.argv[1] + '/api'

token = open(token_path).readline().strip()
headers = {
    'Authorization': 'Bearer ' + token,
    'Accept': 'application/json'
}

def youtrack_request(request):
    while True:
        try:
            time.sleep(2)
            return requests.get(YOUTRACK_API + request, headers=headers).json()
        except requests.exceptions.ConnectionError as e:
            print(e)
            time.sleep(10)

def collect_vote_timestamps(issue_id):
    vote_timestamps = {}
    r = youtrack_request(f'/issues/{issue_id}/activities?fields=timestamp,author(login),added,removed,category&categories=VotersCategory')
    for vote in r:
        voter = vote['author']['login']
        if vote['added']:
            vote_timestamps[voter] = datetime.fromtimestamp(vote['timestamp'] // 1000)
        else:
            if voter in vote_timestamps: del vote_timestamps[voter]
    return vote_timestamps

def collect_vote_timestamps_recursive(issue_id):
    result = collect_vote_timestamps(issue_id)
    link_types = youtrack_request(f'/issues/{issue_id}/links?fields=linkType(name),issues(idReadable)')
    for link_type in link_types:
        if link_type['linkType']['name'] == 'Duplicate':
            for issue in link_type['issues']:
                duplicate_id = issue['idReadable']
                issue_details = youtrack_request(f'/issues/{duplicate_id}?fields=reporter(login),created')
                result[issue_details['reporter']['login']] = datetime.fromtimestamp(issue_details['created'] // 1000)
                result.update(collect_vote_timestamps(duplicate_id))
    return result

def distribution_per_year(votes, include_month = False):
    distro = collections.Counter()
    for voter, date in votes.items():
        key = f'{date.year}.{date.month}' if include_month else date.year
        distro[key] += 1
    return list(distro.items())

def extract_custom_field(issue, name):
    for f in issue['customFields']:
        if f['projectCustomField']['field']['name'] == name:
            value = f['value']
            return value['name'] if value else 'Unspecified'

def query_issues(query):
    result = []
    issues = youtrack_request(f'/issues?fields=idReadable,summary,votes,customFields(projectCustomField(field(name)),value(name))&$top=500&query={query} order by:votes')
    for issue in issues:
        issue_id = issue['idReadable']
        subsystem = extract_custom_field(issue, 'Subsystem')
        result.append((issue_id, issue['summary'], issue['votes'], subsystem))
    return result

def top_voted_issues_per_subsystem(issues):
    this_year = datetime.now().year
    top_per_subsystem = {}
    for issue_id, summary, votes, subsystem in issues:
        vote_distribution = distribution_per_year(collect_vote_timestamps_recursive(issue_id))
        votes_this_year = 0
        for year, votes in vote_distribution:
            if year == this_year: votes_this_year = votes
        if not votes_this_year: continue
        print(f'{issue_id} {summary}: {votes_this_year}')

        if subsystem not in top_per_subsystem:
            top_per_subsystem[subsystem] = []
        top_per_subsystem[subsystem].append((issue_id, summary, votes_this_year))
    for list in top_per_subsystem.values():
        list.sort(key=lambda i: -i[2])
    return top_per_subsystem

issue_id = sys.argv[2]
if issue_id == 'report':
    report_file = open(sys.argv[3], "w")
    issues = query_issues(' '.join([urllib.parse.quote_plus(arg) for arg in sys.argv[4:]]))
    top_per_subsystem = top_voted_issues_per_subsystem(issues)
    subsystems = list(top_per_subsystem.keys())
    subsystems.sort()
    for subsystem in subsystems:
        issues = top_per_subsystem[subsystem]
        print(f"## Subsystem: {subsystem}", file=report_file)
        print("| Issue | Votes |", file=report_file)
        print("| --- | --- |", file=report_file)
        for issue_id, summary, votes in issues:
            print(f"| {issue_id} | {votes} |", file=report_file)
        print("", file=report_file)
else:
    include_month = False
    if issue_id == 'month':
        issue_id = sys.argv[3]
        include_month = True
    print(distribution_per_year(collect_vote_timestamps_recursive(issue_id), include_month))
