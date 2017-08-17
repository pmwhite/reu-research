# Social Network De-anonymization Framework

This repository contains code and scripts that came out of my REU internship
project at Wright State University. The focus of the project was on
de-anonymizing Twitter and Github datasets, but this repository also some
scripts for working with StackOverflow because SO was originally part of the
project's scope.

## Coding style

I'm a strong believer in functional programming, so I tended to avoid classes
in this code. Instead, you'll see a lot of `namedtuple`s used as data
containers. Another oddity is that I've extracted common functionality into
tuples of functions (similar to Haskell typeclasses, except you need to pass
them explicitly as parameters). This may not be the best solution, but I
decided not to fuss to much about it.

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
