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

We used the GitHub GraphQL API to obtain the GitHub datasets. This repository
does not contain API keys for either Twitter or GitHub, so you need to find
those yourself; the documentation for each API is helpful in creating them.
Once you have the keys, you will need to create a `keys.py` file with the
following structure:

```
GITHUB_KEY="..."
TWITTER_CONSUMER_KEY=r"..."
TWITTER_CONSUMER_SECRET=r"..."
TWITTER_ACCESS_TOKEN_KEY=r"..."
TWITTER_ACCESS_TOKEN_SECRET=r"..."
```

The API modules import this file, so they will not work unless you have created
it.

There is also a StackOverflow module for scraping SO data. StackOverflow
provides a data dump which is kept pretty well up to date. You can find the
data dump [here](https://archive.org/details/stackexchange). Put each of the
dump files into a `data` folder in the repositories directory.

We used an SQLite database to store all scraped and requested data; each
modules which uses a database should take a database connection as a parameter,
so you should be able to put the database wherever you want.

## Questions and Contributions

If you'd like to contribute somehow to this repository, you are welcome to; I
don't care too much for comments, so most of my code doesn't have comments
(except for docstrings), but you're welcome to have comments in pull requested
code.

Questions are welcome! Use the issue tracker for questions or problems. I doubt
I will get much traffic on this repository, so feel free to ask as much as you
want.
