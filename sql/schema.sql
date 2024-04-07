PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Mazes;
CREATE TABLE Mazes (
    MazeID INTEGER PRIMARY KEY,
    Name TEXT
);

DROP TABLE IF EXISTS Users;
CREATE TABLE Users (
    UserID INTEGER PRIMARY KEY,
    Username TEXT UNIQUE NOT NULL,
    FirstName TEXT NOT NULL,
    LastName TEXT,
    PasswordHash BLOB NOT NULL
    -- TODD: Validate Username, PasswordHash
);

-- CREATE TABLE History (
--     Timestamp INTEGER NOT NULL,
--     UserID INTEGER,
--     MazeID INTEGER,
--     Seed INTEGER,
--     FOREIGN KEY (UserID) REFERENCES Users(UserID),
--     FOREIGN KEY (MazeID) REFERENCES Mazes(MazeID)
-- );

-- CREATE TABLE Users (
--     UserID INTEGER UNIQUE NOT NULL,
--     Username TEXT UNIQUE NOT NULL,
--     FirstName TEXT,
--     LastName TEXT,
--     EmailAddress TEXT,
--     PasswordHash BLOB,
--     PRIMARY KEY(UserID)
-- );
