# Developer De-anonymization

This repository contains code and documentation for my REU Research project at
Wright State University. The goal of this project is *de-anonymizing and
unifying GitHub, StackOverflow, and Twitter users*. Given a user on one of
these three networks, we attempt to identify the same user's accounts on the
other two networks.

Social sites often provide data to advertising companies to allow them to serve
more relevant ads to users. To protect their user's privacy concerns, these
sites will anonymize the data so that individual users cannot be identified.
Ideally, advertisers should be dealing only with relevant information about
their target audience, and not the individuals themselves.

De-anonymization is the process of using background information, such as
network structure or a small number of "seed" users, to extract the identity of
individuals from an anonymized set of data.

This project deals specifically with three very common networks for software
developers and programmers. While previous research on de-anonymization has
used Twitter as a dataset, StackOverflow and GitHub are currently unexplored. I
expect the probability of getting good results is increased significantly
because of the large user overlap between the sites.

The point of the sites that this project focuses on is that everything on them
is publicly and easily accessible. Very little attempt is made to hide a users
activity on these sites. Discovering usernames of individuals is no hard feat;
thus, categorizing the goal of this project as "de-anonymization" may be a
stretch. Perhaps a more appropriate term would be "unification" of users. Note
that we will not be using usernames or "identity information" to perform the
de-anonymization except as a evalidation tool.

## Outside resources

Not provided in this repository are my the API keys I used when obtaining data.
I used version 3 of the GitHub API (v4 is dramatically different from v3);
anyone can make 500 requests to the API per hour, but if you use an API key,
the rate is increased to 5000 req/hr. Twitter requires API keys to make any
requests at all.

The keys needed to be placed in a file title `keys.py` like the following:

```
GITHUB_KEY="github key"

TWITTER_API=r"twitter client key"
TWITTER_SECRET=r"twitter secret key"
```

We need not use an API to obtain StackOverflow data; StackExchange provides
public data dump files every few months
[here](https://archive.org/details/stackexchange). There are a lot of files for
other networks on StackExchange, but the ones we are interested in are the
stackoverflow posts,comments, and tags files.

## Database Population

An SQLite database is treated as a persistent data structure so that programs
do not have to constantly request web APIs for the same data every time they
are run. There are some rules that are followed to maintain consistency of the
data in the database.

Most of the times a user is accessed from a web API, it is placed into the
database. If you access a users connections (Github contributors or Twitter
friends), either all of them are added to the database or none of them are.
This allows programs to tell if a users connections have are complete or not;
if some connections are present, all of them are, and there is no need to
request an API to refresh anything.
