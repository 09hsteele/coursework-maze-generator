PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Mazes;
CREATE TABLE Mazes (
    MazeID INTEGER PRIMARY KEY,
    Name TEXT,
    Public BOOLEAN NOT NULL DEFAULT 0,
    CreatorID INTEGER,
    FOREIGN KEY (CreatorID) REFERENCES Users(UserID)
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