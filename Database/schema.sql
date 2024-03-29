CREATE TABLE IF NOT EXISTS Template (
    MazeID INTEGER AUTOINCREMENT NOT NULL,
    Name VARCHAR(20) NOT NULL,
    CategoryID INTEGER,

    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID),
    PRIMARY KEY (MazeID)
);

CREATE TABLE IF NOT EXISTS Category (
    CategoryID INTEGER AUTOINCREMENT NOT NULL,
    Name VARCHAR(20) NOT NULL,
    Description VARCHAR(128)
);

