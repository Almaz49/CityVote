PRAGMA foreign_keys = 0;

CREATE TABLE sqlitestudio_temp_table AS SELECT *
                                          FROM Clubs;

DROP TABLE Clubs;

CREATE TABLE Clubs (
    id                          INTEGER PRIMARY KEY
                                        NOT NULL
                                        UNIQUE,
    name                        TEXT    NOT NULL
                                        UNIQUE,
    description                 TEXT,
    father_group                INTEGER,
    tg_bot                      TEXT,
    channel_link                TEXT,
    conditions_of_entry         TEXT,
    questions_for_the_candidate TEXT,
    duration_add_variants       INTEGER DEFAULT (2),
    duration_first_stage        INTEGER DEFAULT (2),
    duration_final              INTEGER DEFAULT (1),
    duration_confirmation       INTEGER DEFAULT (1),
    threshold_in_voices         REAL    DEFAULT (5),
    threshold_in_percent        REAL    DEFAULT (1),
    lang                        TEXT,
    FOREIGN KEY (
        father_group
    )
    REFERENCES Clubs (id)
);

INSERT INTO Clubs (
                      id,
                      name,
                      description,
                      father_group,
                      tg_bot,
                      channel_link,
                      conditions_of_entry,
                      questions_for_the_candidate,
                      duration_add_variants,
                      duration_first_stage,
                      duration_final,
                      duration_confirmation,
                      threshold_in_voices,
                      threshold_in_percent
                  )
                  SELECT id,
                         name,
                         description,
                         father_group,
                         tg_bot,
                         channel_link,
                         conditions_of_entry,
                         questions_for_the_candidate,
                         duration_add_variants,
                         duration_first_stage,
                         duration_final,
                         duration_confirmation,
                         threshold_in_voices,
                         threshold_in_percent
                    FROM sqlitestudio_temp_table;

DROP TABLE sqlitestudio_temp_table;

PRAGMA foreign_keys = 1;

PRAGMA foreign_keys = 0;

CREATE TABLE sqlitestudio_temp_table AS SELECT *
                                          FROM Members;

DROP TABLE Members;

CREATE TABLE Members (
    id              INTEGER PRIMARY KEY
                            NOT NULL
                            UNIQUE,
    club_id         INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    proxy           INTEGER,
    number_of_votes REAL,
    description     TEXT,
    resume          TEXT,
    info_level      TEXT,
    token           INTEGER REFERENCES Tokens (id),
    ban_expires_at  TEXT,
    lang            TEXT,
    FOREIGN KEY (
        club_id
    )
    REFERENCES Clubs (id),
    FOREIGN KEY (
        user_id
    )
    REFERENCES Users (id),
    FOREIGN KEY (
        proxy
    )
    REFERENCES Members (id),
    UNIQUE (
        club_id,
        user_id
    )
);

INSERT INTO Members (
                        id,
                        club_id,
                        user_id,
                        proxy,
                        number_of_votes,
                        description,
                        resume,
                        info_level,
                        token,
                        ban_expires_at
                    )
                    SELECT id,
                           club_id,
                           user_id,
                           proxy,
                           number_of_votes,
                           description,
                           resume,
                           info_level,
                           token,
                           ban_expires_at
                      FROM sqlitestudio_temp_table;

DROP TABLE sqlitestudio_temp_table;

PRAGMA foreign_keys = 1;
