PRAGMA foreign_keys = ON;

CREATE TABLE Mazes (
    MazeID INTEGER UNIQUE NOT NULL,
    Name TEXT
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
