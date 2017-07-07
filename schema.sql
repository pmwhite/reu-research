CREATE TABLE `StackTags` (
	`Id`	INTEGER NOT NULL UNIQUE,
	`TagName`	TEXT NOT NULL,
	`Count`	INTEGER NOT NULL,
	PRIMARY KEY(`Id`));

CREATE TABLE `StackComments` (
	`Id`	INTEGER NOT NULL UNIQUE,
	`PostId`	INTEGER NOT NULL,
	`Score`	INTEGER NOT NULL,
	`UserId`	INTEGER NOT NULL,
	PRIMARY KEY(`Id`));

CREATE TABLE `StackTagAssignments` (
	`PostId`	INTEGER NOT NULL,
	`TagId`	INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS "StackPosts" (
	`Id`	INTEGER NOT NULL UNIQUE,
	`PostTypeId`	INTEGER NOT NULL,
	`Score`	INTEGER NOT NULL,
	`OwnerUserId`	INTEGER,
	`AcceptedAnswerId`	INTEGER,
	`ParentId`	INTEGER,
	PRIMARY KEY(`Id`));

CREATE TABLE IF NOT EXISTS "StackUsers" (
	`Id`	INTEGER NOT NULL UNIQUE,
	`DisplayName`	TEXT NOT NULL,
	`Reputation`	INTEGER NOT NULL,
	`WebsiteUrl`	TEXT,
	`Age`	INTEGER,
	`Location`	TEXT,
	PRIMARY KEY(`Id`));

CREATE TABLE IF NOT EXISTS "TwitterFriendships" (
	`FromId`	INTEGER NOT NULL,
	`ToId`	INTEGER NOT NULL);

CREATE TABLE `GithubEdges` (
	`FromId`	INTEGER NOT NULL,
	`ToId`	INTEGER NOT NULL);

CREATE TABLE `StackEdges` (
	`FromId`	INTEGER NOT NULL,
	`ToId`	INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS "GithubContributions" (
	`UserId`	TEXT NOT NULL,
	`RepoId`	TEXT NOT NULL);

CREATE TABLE `ApiSearches` (
	`EntityId`	TEXT NOT NULL,
	`SearchType`	TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS "TwitterUsers" (
	`Id`	TEXT NOT NULL UNIQUE,
	`ScreenName`	TEXT NOT NULL,
	`Name`	TEXT,
	`Location`	TEXT,
	`Url`	TEXT,
	`Followers`	INTEGER NOT NULL,
	`Following`	INTEGER NOT NULL,
	PRIMARY KEY(`Id`));

CREATE TABLE IF NOT EXISTS "GithubRepos" (
	`Id`	TEXT NOT NULL UNIQUE,
	`OwnerId`	INTEGER NOT NULL,
	`OwnerLogin`	TEXT NOT NULL,
	`Name`	TEXT NOT NULL,
	`Language`	TEXT,
	`IsFork`	INTEGER NOT NULL,
	`Homepage`	INTEGER,
	PRIMARY KEY(`Id`));

CREATE TABLE IF NOT EXISTS "GithubUsers" (
	`Id`	TEXT NOT NULL UNIQUE,
	`Login`	TEXT NOT NULL,
	`Location`	TEXT,
	`Email`	TEXT,
	`Name`	TEXT,
	`WebsiteUrl`	TEXT,
	`Company`	TEXT,
	PRIMARY KEY(`Id`));

CREATE TABLE IF NOT EXISTS "Dict" (
	`Key`	TEXT NOT NULL UNIQUE,
	`Value`	TEXT NOT NULL,
	PRIMARY KEY(`Key`));

CREATE TABLE `TwitterTweets` (
	`Id`	TEXT NOT NULL UNIQUE,
	`UserId`	TEXT NOT NULL,
	`CreatedAt`	INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS "TwitterTagging" (
	`TweetId`	TEXT NOT NULL,
	`Tag`	INTEGER NOT NULL);

CREATE INDEX GithubLoginIndex ON GithubUsers (Login);
CREATE INDEX StackUsersNameIndex on StackUsers (DisplayName);
CREATE INDEX StackLocationIndex ON StackUsers (Location);
CREATE INDEX `StackEdgesFromIndex` ON `StackEdges` (`FromId` );
CREATE INDEX `StackEdgesToIndex` ON `GithubEdges` (`ToId` );
CREATE INDEX TwitterNameIndex ON TwitterUsers (ScreenName);
CREATE INDEX `EntitySearchesIndex` ON `ApiSearches` (`EntityId` );
CREATE INDEX StackPostsOwnerIndex ON StackPosts (OwnerUserId);
