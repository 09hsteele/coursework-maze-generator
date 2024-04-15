import os
import pathlib

from PIL import Image
from dataclasses import dataclass
import sqlite3

from generator import validate_mask, MAX_MASK_SIZE, MaskError


class UserAlreadyExistsError(Exception):
    """raised when trying to add a user to the database with a username that
    already exists"""


class AuthenticationError(Exception):
    """raised when attempting to log in with an incorrect password"""


class UserNotFoundError(Exception):
    """raised when trying to log in with a username that can't be found"""


class MazeNotFoundError(Exception):
    """raised when trying to access info about a maze that cannot be found in the database"""


@dataclass
class MazeInfo:
    MazeID: int
    Name: str

    def get_shape_path(self):
        return pathlib.Path(f"static/mazes/maze_{self.MazeID}.png")

    def get_shape(self):
        return Image.open(self.get_shape_path()).convert("RGB")


@dataclass
class UserInfo:
    user_id: int
    username: str
    first_name: str
    last_name: str


class Database:
    def __init__(self, file_path: str, check_integrity: bool = False):
        self.connection = sqlite3.connect(file_path, check_same_thread=False)
        if check_integrity:
            self.check_mask_integrity()

    def check_mask_integrity(self) -> None:
        """
        checks if all masks that are stored in the database actually exit in storage
        and are all valid maze masks. i.e. they follow the following rules:
         - they only include these colours: (#FFFFFF, #000000, #FF00FF, #00FFFF)
         - there is only one isolated group of black pixels
         - all entrance/exit pixels are on the border of the image

        :raises: generator.MaskError or FileNotFoundError if it finds a problem
        """
        for maze in self.get_all_mazes():
            try:
                mask = maze.get_shape()
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Maze number {maze.MazeID} not found") from e
            try:
                if (size := os.stat(maze.get_shape_path()).st_size) > MAX_MASK_SIZE:
                    raise MaskError(f"File too big ({size})")
                validate_mask(mask)
                print(f"{maze.MazeID} good :)")
            except Exception as e:
                print(f"{maze.MazeID} bad >:(")
                print(repr(e))
        print("database maze check completed")

    def get_maze_from_id(self, maze_id):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes WHERE MazeID = (?);", (maze_id,))
        try:
            info = MazeInfo(*c.fetchone())
            return info
        except TypeError:
            raise MazeNotFoundError()
        finally:
            c.close()

    def get_all_mazes(self):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes;")
        mazes = [MazeInfo(MazeID, Name) for (MazeID, Name) in c.fetchall()]
        c.close()
        return mazes

    def add_new_maze(self, mask: Image.Image, name: str, public=False):
        c = self.connection.cursor()
        c.execute("""BEGIN TRANSACTION;""")
        c.execute("""INSERT INTO Mazes (Name) VALUES ((?));""", (name,))
        info = MazeInfo(c.lastrowid, name)
        mask.save(info.get_shape_path())
        c.execute("""COMMIT;""")
        c.close()

    def add_user(self, user_info: UserInfo, password_hash: bytes):
        c = self.connection.cursor()
        try:
            c.execute("""INSERT INTO Users (Username, FirstName, LastName, PasswordHash)
                      VALUES ((?), (?), (?), (?));""",
                      (user_info.username, user_info.first_name, user_info.last_name,
                       password_hash))
        except sqlite3.IntegrityError as e:
            raise UserAlreadyExistsError(f"User with username '{user_info.username}' already exists") from e
        finally:
            c.close()
            self.connection.commit()

    def get_user_from_username(self, username: str):
        c = self.connection.cursor()
        try:
            c.execute("""SELECT UserID, Username, FirstName, LastName FROM Users
                      WHERE Username = (?);""", (username,))
            return UserInfo(*c.fetchone())
        except TypeError:
            raise UserNotFoundError(f"User '{username}' does not exist")
        finally:
            c.close()

    def authenticate_user(self, username: str, password_hash: bytes):
        """raises an error if username or password are wrong
        otherwise returns the UserID of the user trying to log in"""
        c = self.connection.cursor()
        try:
            c.execute("""SELECT PasswordHash, UserID FROM Users WHERE Username = (?);""",
                      (username,))
            password_attempt, user_id = c.fetchone()
            if password_attempt == password_hash:
                return user_id
            else:
                raise AuthenticationError('Incorrect password')

        except TypeError:
            raise UserNotFoundError(f"User '{username}' does not exist")

        finally:
            c.close()

    def get_user(self, user_id) -> UserInfo:
        c = self.connection.cursor()
        c.execute("SELECT UserID, Username, FirstName, LastName FROM Users WHERE"
                  " UserID = (?);", (user_id,))
        data = c.fetchone()
        c.close()
        if data is None:
            raise UserNotFoundError(f"User {user_id} does not exist")

        return UserInfo(*data)

    def update_info(self, user_id: int, new_username: str = None, new_fname: str = None, new_lname: str = None):
        c = self.connection.cursor()
        try:
            c.execute("BEGIN TRANSACTION;")
            if new_username:
                c.execute("UPDATE Users SET Username=(?) WHERE UserID=(?);", (new_username, user_id))
            if new_fname:
                c.execute("UPDATE Users SET FirstName=(?) WHERE UserID=(?);", (new_fname, user_id))
            if new_lname:
                c.execute("UPDATE Users SET LastName=(?) WHERE UserID=(?);", (new_lname, user_id))
            c.execute("COMMIT;")
        except sqlite3.IntegrityError as e:
            c.execute("ROLLBACK;")
            raise UserAlreadyExistsError(f"User with username '{new_username}' already exists") from e
        finally:
            c.close()

    def update_password(self, user_id, new_password_hash):
        c = self.connection.cursor()
        c.execute("UPDATE Users SET PasswordHash = (?) WHERE UserID=(?)",
                  (new_password_hash, user_id))
        c.close()

    def delete_user(self, user_id: int):
        c = self.connection.cursor()
        c.execute("DELETE FROM Users WHERE UserID = (?)", (user_id,))


if __name__ == "__main__":
    db = Database("database.db")
    print(db.get_maze_from_id(0))
    print(db.get_all_mazes())
