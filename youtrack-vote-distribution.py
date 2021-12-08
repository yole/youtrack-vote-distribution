import requests, os, sys, collections, time
from datetime import datetime

YOUTRACK_API = 'https://youtrack.jetbrains.com/api'

token_path = os.path.expanduser("~/.youtrack-token")
if not os.path.exists(token_path):
    print("Please follow the instructions at https://www.jetbrains.com/help/youtrack/devportal/authentication-with-permanent-token.html to obtain a YouTrack permanent token")
    print("and save the token to the .youtrack_token file in your home directory.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python3 youtrack-vote-distribution.py <issue ID>")
    sys.exit(1)

token = open(token_path).readline().strip()
headers = {
    'Authorization': 'Bearer perm:' + token,
    'Accept': 'application/json'
}

def collect_vote_timestamps(issue_id):
    vote_timestamps = {}
    r = requests.get(f'{YOUTRACK_API}/issues/{issue_id}/activities?fields=timestamp,author(login),added,removed,category&categories=VotersCategory', headers=headers).json()
    for vote in r:
        voter = vote['author']['login']
        if vote['added']:
            vote_timestamps[voter] = datetime.fromtimestamp(vote['timestamp'] // 1000)
        else:
            if voter in vote_timestamps: del vote_timestamps[voter]
    return vote_timestamps

def collect_vote_timestamps_recursive(issue_id):
    result = collect_vote_timestamps(issue_id)
    link_types = requests.get(f'{YOUTRACK_API}/issues/{issue_id}/links?fields=linkType(name),issues(idReadable)', headers=headers).json()
    for link_type in link_types:
        if link_type['linkType']['name'] == 'Duplicate':
            for issue in link_type['issues']:
                duplicate_id = issue['idReadable']
                issue_details = requests.get(f'{YOUTRACK_API}/issues/{duplicate_id}?fields=reporter(login),created', headers=headers).json()
                result[issue_details['reporter']['login']] = datetime.fromtimestamp(issue_details['created'] // 1000)
                result.update(collect_vote_timestamps(duplicate_id))
    return result

def distribution_per_year(votes):
    distro = collections.Counter()
    for voter, date in votes.items():
        distro[date.year] += 1
    return list(distro.items())

def extract_custom_field(issue, name):
    for f in issue['customFields']:
        if f['projectCustomField']['field']['name'] == name:
            value = f['value']
            return value['name'] if value else 'Unspecified'

def query_issues(query):
    result = []
    issues = requests.get(f'{YOUTRACK_API}/issues?fields=idReadable,summary,votes,customFields(projectCustomField(field(name)),value(name))&$top=20&query={query} order by:votes', headers=headers).json()
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

        if subsystem not in top_per_subsystem:
            top_per_subsystem[subsystem] = []
        top_per_subsystem[subsystem].append((issue_id, summary, votes_this_year))
    for list in top_per_subsystem.values():
        list.sort(key=lambda i: -i[2])
    return top_per_subsystem

issue_id = sys.argv[1]
if issue_id == 'report':
    issues = query_issues(' '.join(sys.argv[2:]))
    top_per_subsystem = top_voted_issues_per_subsystem(issues)
    for subsystem, issues in top_per_subsystem.items():
        print(f"Subsystem: {subsystem}")
        for issue_id, summary, votes in issues:
            print(f"{issue_id} {summary}: {votes}")
        print("")
else:
    print(distribution_per_year(collect_vote_timestamps_recursive(issue_id)))
