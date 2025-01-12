CREATE TABLE IF NOT EXISTS `Votes` (
	`id` integer primary key NOT NULL UNIQUE,
	`creator` INTEGER NOT NULL,
	`vote_type` TEXT NOT NULL DEFAULT usual,
	`title` TEXT NOT NULL,
	`text` TEXT DEFAULT 'null',
	`active` INTEGER DEFAULT '1',
	`club_id` INTEGER NOT NULL,
	`result` INTEGER,
	`link_id` INTEGER,
	time_create TEXT,
    time_start    TEXT,
    starter       INTEGER REFERENCES Members (id), 
    time_finish_1 TEXT,
    finisher_1            REFERENCES Members (id),
    time_close    TEXT,
    closer        INTEGER REFERENCES Members (id),
FOREIGN KEY(`creator`) REFERENCES `Members`(`id`),
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`),
FOREIGN KEY(`result`) REFERENCES `Variants`(`id`),
FOREIGN KEY(`link_id`) REFERENCES `Links`(`id`)
);
CREATE TABLE IF NOT EXISTS `Variants` (
	`id` integer primary key NOT NULL UNIQUE,
	`vote_id` INTEGER NOT NULL,
	`author` INTEGER NOT NULL,
	`title` TEXT NOT NULL,
	`text` TEXT,
	`time_create` TEXT,
	`link_id` INTEGER,
	variant_status TEXT,
UNIQUE (vote_id, title),
FOREIGN KEY(`vote_id`) REFERENCES `Votes`(`id`),
FOREIGN KEY(`author`) REFERENCES `Members`(`id`),
FOREIGN KEY(`link_id`) REFERENCES `Links`(`id`)
);
CREATE TABLE IF NOT EXISTS `Links` (
	`id` integer primary key NOT NULL UNIQUE,
	`link_href` TEXT NOT NULL,
	`link_title` TEXT,
	`link_text` TEXT,
	`member_id` INTEGER,
	`vote_id` INTEGER,
	`variant_id` INTEGER,
	`user_id` INTEGER,
	`club_id` INTEGER,
FOREIGN KEY(`member_id`) REFERENCES `Members`(`id`),
FOREIGN KEY(`vote_id`) REFERENCES `Votes`(`id`),
FOREIGN KEY(`variant_id`) REFERENCES `Variants`(`id`),
FOREIGN KEY(`user_id`) REFERENCES `Users`(`id`),
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`)
);
CREATE TABLE IF NOT EXISTS `Users` (
	`id` integer primary key NOT NULL UNIQUE,
	`tg_id` INTEGER UNIQUE,
	`tg_phone_number` INTEGER,
	`tg_first_name` TEXT,
	`tg_last_name` TEXT,
	`first_name` TEXT,
	`middle_name` TEXT,
	`last_name` TEXT,
	`bithday` TEXT,
	`birth_year` INTEGER,
	`photo` TEXT,
	`email` TEXT,
FOREIGN KEY(`id`) REFERENCES `Users`(`id`)
);
CREATE TABLE IF NOT EXISTS `Clubs` (
	`id` integer primary key NOT NULL UNIQUE,
	`name` TEXT NOT NULL UNIQUE,
	`description` TEXT,
	`link_id` INTEGER,
	`father_group` INTEGER,
	`tg_bot` TEXT,
FOREIGN KEY(`link_id`) REFERENCES `Links`(`id`),
FOREIGN KEY(`father_group`) REFERENCES `Clubs`(`id`)
);
CREATE TABLE IF NOT EXISTS `Members` (
	`id` integer primary key NOT NULL UNIQUE,
	`club_id` INTEGER NOT NULL,
	`user_id` INTEGER NOT NULL,
	`proxy` INTEGER,
	`number_of_votes` REAL,
	`desciption` TEXT,
	`link_id` INTEGER,
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`),
FOREIGN KEY(`user_id`) REFERENCES `Users`(`id`),
FOREIGN KEY(`delegate`) REFERENCES `Members`(`id`),
FOREIGN KEY(`link_id`) REFERENCES `Links`(`id`),
FOREIGN KEY (delegate) REFERENCES Members (id),
UNIQUE (club_id, user_id)
);
CREATE TABLE IF NOT EXISTS `Tokens` (
	`id` integer primary key NOT NULL,
	`token` TEXT NOT NULL UNIQUE,
	`club_id` INTEGER NOT NULL,
	`creator` INTEGER,
	`status` INTEGER,
	`validity` TEXT,
	`time_of_action` TEXT,
	`number_of_possible` INTEGER DEFAULT '1',
	`sity` TEXT,
	`district` TEXT,
	`street` TEXT,
	`house` TEXT,
	`entrance` INTEGER,
	`apartment` INTEGER,
	`telephon_number` TEXT,
	`first_name` TEXT,
	`lust_name` TEXT,
	`polling_station` INTEGER,
	`lot` INTEGER,
	`number_in_lot` INTEGER,
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`),
FOREIGN KEY(`creator`) REFERENCES `Members`(`id`)
);
CREATE TABLE IF NOT EXISTS `Registrations` (
	`id` integer primary key NOT NULL UNIQUE,
	`member_id` INTEGER NOT NULL,
	`token_id` INTEGER,
	`registrator` INTEGER,
	`status` TEXT,
	time_reg    TEXT,
FOREIGN KEY(`member_id`) REFERENCES `Members`(`id`),
FOREIGN KEY(`token_id`) REFERENCES `Tokens`(`id`),
FOREIGN KEY(`registrator`) REFERENCES `Members`(`id`)
);
CREATE TABLE IF NOT EXISTS `Status` (
	`id` integer primary key NOT NULL UNIQUE,
	`member_id` INTEGER NOT NULL,
	`status` TEXT,
FOREIGN KEY(`member_id`) REFERENCES `Members`(`id`),
UNIQUE (member_id, status)
);
CREATE TABLE IF NOT EXISTS Elections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT
                          UNIQUE,
    member_id     INTEGER REFERENCES Members (id),
    variant_id    INTEGER REFERENCES Variants (id),
    election_time TEXT,
    status        TEXT
);
CREATE TABLE IF NOT EXISTS Trusts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT
                       UNIQUE,
    member_id  INTEGER REFERENCES Members (id) 
                       NOT NULL,
    proxy_id   INTEGER REFERENCES Members (id) 
                       NOT NULL,
    trust_time TEXT    NOT NULL
);
