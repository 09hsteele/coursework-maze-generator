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
class UserInfo:
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None


@dataclass
class MazeInfo:
    MazeID: int
    Name: str | None = None
    Creator: UserInfo | None = None
    Public: bool | None = None

    def get_shape_path(self):
        return pathlib.Path(f"static/mazes/maze_{self.MazeID}.png")

    def get_shape(self):
        return Image.open(self.get_shape_path()).convert("RGB")


class Database:
    def __init__(self, file_path: str, check_integrity: bool = False):
        self.connection = sqlite3.connect(file_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys = ON;")
        if check_integrity:
            self.check_mask_integrity()

    def __del__(self):
        self.connection.close()

    def check_mask_integrity(self) -> None:
        r"""
        checks if all masks that are stored in the database actually exist in storage
        and are all valid maze masks. i.e. they follow the following rules:
         - they only include these colours: (``#FFFFFF``, ``#000000``, ``#FF00FF``, ``#00FFFF``)
         - there is only one isolated group of black pixels
         - all entrance/exit pixels are on the border of the image
         - are not larger than :data:`generator.MAX_MASK_SIZE` bytes

        :raises: :class:`generator.MaskError` or FileNotFoundError if it finds a problem
        """
        for maze in self.get_public_mazes():
            try:
                mask = maze.get_shape()
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Maze number {maze.MazeID} not found") from e
            try:
                if (size := os.stat(maze.get_shape_path()).st_size) > MAX_MASK_SIZE:
                    raise MaskError(f"File too big ({size})")
                validate_mask(mask)
                print(f"{maze.MazeID}:{maze.Name} good :)")
            except Exception as e:
                print(f"{maze.MazeID}:{maze.Name} bad >:(")
                print(repr(e))
        print("database maze check completed")

    def get_maze_from_id(self, maze_id: int) -> MazeInfo:
        c = self.connection.execute("SELECT Name, CreatorID, Public FROM Mazes WHERE MazeID = (?);", (maze_id,))
        try:
            name, creator_id, public = c.fetchone()
            info = MazeInfo(maze_id, name, self.get_user(creator_id), public)
            return info
        except TypeError:
            raise MazeNotFoundError()
        finally:
            self.connection.commit()

    def get_public_mazes(self) -> list[MazeInfo]:
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name, CreatorID FROM Mazes WHERE Public=1 ORDER BY Name;")
        mazes = [MazeInfo(MazeID, Name, self.get_user(CreatorID), True) for (MazeID, Name, CreatorID) in c.fetchall()]
        c.close()
        self.connection.commit()
        return mazes

    def get_mazes_by_user(self, user: UserInfo) -> list[MazeInfo] | None:
        if user is None:
            return None
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name, Public FROM Mazes WHERE CreatorID=(?) ORDER BY Name;", (str(user.user_id),))
        mazes = [MazeInfo(MazeID, Name, user, public) for (MazeID, Name, public) in c.fetchall()]
        c.close()
        self.connection.commit()
        return mazes

    def add_new_maze(self, mask: Image.Image, name: str, creator: UserInfo, public: bool = False) -> MazeInfo:
        c = self.connection.cursor()
        c.execute("""BEGIN TRANSACTION;""")
        c.execute("""INSERT INTO Mazes (Name, Public, CreatorID) VALUES ((?), (?), (?));""",
                  (name, public, creator.user_id))
        info = MazeInfo(c.lastrowid, name, creator, public)
        mask.save(info.get_shape_path())
        c.execute("""COMMIT;""")
        c.close()
        self.connection.commit()
        return info

    def delete_maze(self, maze: MazeInfo):
        c = self.connection.cursor()
        c.execute("""DELETE FROM Mazes WHERE MazeID = (?);""", (maze.MazeID,))
        pathlib.Path.unlink(maze.get_shape_path())
        c.close()
        self.connection.commit()

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
            self.connection.commit()

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
            self.connection.commit()

    def get_user(self, user_id) -> UserInfo:
        c = self.connection.cursor()
        c.execute("SELECT UserID, Username, FirstName, LastName FROM Users WHERE"
                  " UserID = (?);", (user_id,))
        data = c.fetchone()
        c.close()
        self.connection.commit()
        if data is None:
            raise UserNotFoundError(f"User {user_id} does not exist")

        return UserInfo(*data)

    def update_info(self, user_id: int, new_username: str = None, new_firstname: str = None, new_lastname: str = None):
        c = self.connection.cursor()
        try:
            c.execute("BEGIN TRANSACTION;")
            if new_username:
                c.execute("UPDATE Users SET Username=(?) WHERE UserID=(?);", (new_username, user_id))
            if new_firstname:
                c.execute("UPDATE Users SET FirstName=(?) WHERE UserID=(?);", (new_firstname, user_id))
            if new_lastname:
                c.execute("UPDATE Users SET LastName=(?) WHERE UserID=(?);", (new_lastname, user_id))
            c.execute("COMMIT;")
        except sqlite3.IntegrityError as e:
            c.execute("ROLLBACK;")
            raise UserAlreadyExistsError(f"User with username '{new_username}' already exists") from e
        finally:
            c.close()
            self.connection.commit()

    def update_password(self, user_id, new_password_hash):
        c = self.connection.cursor()
        c.execute("UPDATE Users SET PasswordHash = (?) WHERE UserID=(?)",
                  (new_password_hash, user_id))
        c.close()
        self.connection.commit()

    def delete_user(self, user_id: int):
        c = self.connection.cursor()

        # delete all mazes owned by this user
        for maze in self.get_mazes_by_user(self.get_user(user_id)):
            #  need to loop through mazes instead of executing sql because files also need to be deleted
            self.delete_maze(maze)

        # remove the user from the database
        c.execute("DELETE FROM Users WHERE UserID = (?)", (user_id,))
        c.close()
        self.connection.commit()


if __name__ == "__main__":
    db = Database("database.db")
    print(db.get_maze_from_id(0))
    print(db.get_public_mazes())
