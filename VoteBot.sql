CREATE TABLE IF NOT EXISTS `Votings` (
	`id` integer primary key NOT NULL UNIQUE,
	`creator` INTEGER NOT NULL,
	`voting_type` TEXT NOT NULL DEFAULT 'usual',
	`title` TEXT NOT NULL,
	`text` TEXT DEFAULT 'null',
	`club_id` INTEGER NOT NULL,
	`result` INTEGER,
	`time_create` TEXT,
    `time_start`    TEXT,
    `time_completed`    TEXT,
	`voting_status`   TEXT,
FOREIGN KEY(`creator`) REFERENCES `Members`(`id`),
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`),
FOREIGN KEY(`result`) REFERENCES `Variants`(`id`)
);
CREATE TABLE IF NOT EXISTS `Variants` (
	`id` integer primary key NOT NULL UNIQUE,
	`voting_id` INTEGER NOT NULL,
	`author` INTEGER NOT NULL,
	`title` TEXT NOT NULL,
	`text` TEXT,
	`time_create` TEXT,
	`variant_status` TEXT,
	`directly_votes` REAL,
    `proxy_votes`    REAL,
    `empty_votes`    REAL,
UNIQUE (voting_id, title),
FOREIGN KEY(`voting_id`) REFERENCES `Votings`(`id`),
FOREIGN KEY(`author`) REFERENCES `Members`(`id`)
);
CREATE TABLE IF NOT EXISTS `Links` (
	`id` integer primary key NOT NULL UNIQUE,
	`link_href` TEXT NOT NULL,
	`link_title` TEXT,
	`link_text` TEXT,
	`object_type` TEXT,
	`object_id` INTEGER
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
    `tg_username`     TEXT,
    `username`        TEXT    UNIQUE,
	`tg_available`       TEXT
);
CREATE TABLE IF NOT EXISTS `Clubs` (
	`id` integer primary key NOT NULL UNIQUE,
	`name` TEXT NOT NULL UNIQUE,
	`description` TEXT,
	`father_group` INTEGER,
	`tg_bot` TEXT,
	`channel_link`        TEXT,
    `conditions_of_entry` TEXT,
    `questions_for_the_candidate` TEXT,
    `duration_add_variants`       INTEGER DEFAULT (2),
    `duration_first_stage`        INTEGER DEFAULT (2),
    `duration_final`              INTEGER DEFAULT (1),
    `duration_confirmation`       INTEGER DEFAULT (1),
FOREIGN KEY(`father_group`) REFERENCES `Clubs`(`id`)
);
CREATE TABLE IF NOT EXISTS `Members` (
	`id` integer primary key NOT NULL UNIQUE,
	`club_id` INTEGER NOT NULL,
	`user_id` INTEGER NOT NULL,
	`proxy` INTEGER,
	`number_of_votes` REAL,
	`description` TEXT,
	`resume`     TEXT,
FOREIGN KEY(`club_id`) REFERENCES `Clubs`(`id`),
FOREIGN KEY(`user_id`) REFERENCES `Users`(`id`),
FOREIGN KEY(`proxy`) REFERENCES `Members`(`id`),
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
	`number_of_possible` INTEGER DEFAULT 1,
	`sity` TEXT,
	`district` TEXT,
	`street` TEXT,
	`house` TEXT,
	`entrance` INTEGER,
	`apartment` INTEGER,
	`telephone_number` TEXT,
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
	`object_type` TEXT,
	`object_id` INTEGER NOT NULL,
	`token_id` INTEGER,
	`registrator` INTEGER,
	`status` TEXT,
	`time_reg`    TEXT,
FOREIGN KEY(`token_id`) REFERENCES `Tokens`(`id`),
FOREIGN KEY(`registrator`) REFERENCES `Members`(`id`)
);
CREATE TABLE IF NOT EXISTS `Status` (
	`id` integer primary key NOT NULL UNIQUE,
	`member_id` INTEGER NOT NULL,
	`status` TEXT,
FOREIGN KEY(`member_id`) REFERENCES `Members`(`id`),
UNIQUE (`member_id`, `status`)
);
CREATE TABLE IF NOT EXISTS `Elections` (
    `id`            INTEGER PRIMARY KEY AUTOINCREMENT
                          UNIQUE,
    `member_id`     INTEGER REFERENCES `Members` (`id`),
    `variant_id`    INTEGER REFERENCES `Variants` (`id`),
    `time_election` TEXT,
    `status`        TEXT
);
CREATE TABLE IF NOT EXISTS `Trusts` (
    `id`         INTEGER PRIMARY KEY AUTOINCREMENT
                       UNIQUE,
    `member_id`  INTEGER REFERENCES `Members` (`id`)
                       NOT NULL,
    `proxy_id`   INTEGER REFERENCES `Members` (`id`)
                       NOT NULL,
    `time_trust` TEXT    NOT NULL
);
CREATE TABLE TgChats (
    `id`      INTEGER PRIMARY KEY AUTOINCREMENT
                    UNIQUE
                    NOT NULL,
    `club_id` INTEGER REFERENCES `Clubs` (`id`),
    `tg_id`   INTEGER,
    `name`    TEXT,
	`channel_type` TEXT,
    `invite_link` TEXT,
	`available`    TEXT,
	`info_level`   TEXT,
	UNIQUE (`club_id`, `tg_id`)
);