from PIL import Image
from dataclasses import dataclass
import sqlite3


@dataclass
class MazeInfo:
    MazeID: int
    Name: str

    def get_shape(self):
        return Image.open(f"static/maze_{self.MazeID}.png")


class Database:
    def __init__(self, file_path: str):
        self.connection = sqlite3.connect(file_path, check_same_thread=False)

    def get_maze_from_id(self, maze_id):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes WHERE MazeID = (?);", (maze_id,))
        return MazeInfo(*c.fetchone())

    def get_all_mazes(self):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes")
        return [MazeInfo(MazeID, Name) for (MazeID, Name) in c.fetchall()]


if __name__ == "__main__":
    db = Database("database.db")
    print(db.get_maze_from_id(0))
    print(db.get_all_mazes())
