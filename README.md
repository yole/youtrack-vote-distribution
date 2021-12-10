# youtrack-vote-distribution

Scripts to analyze the distribution of votes in YouTrack issues.

Usage:
* Follow the instructions at https://www.jetbrains.com/help/youtrack/devportal/authentication-with-permanent-token.html to obtain a YouTrack permanent token
* Save the token to `~/.youtrack_token`
* Run `python3 -m pip install requests` if you don't have the requests module installed.
* Run `python3 youtrack-vote-distribution.py <server> [month] <issue-ID>` to get vote distribution by time for a single issue.
* Run `python3 youtrack-vote-distribution.py <server> report <report-file> <query>` to build a report of recently most voted issues.

