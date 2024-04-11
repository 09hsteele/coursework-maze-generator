from PIL import Image
from dataclasses import dataclass
import sqlite3


@dataclass
class MazeInfo:
    MazeID: int
    Name: str

    def get_shape(self):
        return Image.open(f"static/mazes/maze_{self.MazeID}.png")


@dataclass
class UserInfo:
    user_id: int
    username: str
    first_name: str
    last_name: str


class UserAlreadyExistsError(Exception):
    """raised when trying to add a user to the database with a username that
    already exists"""


class AuthenticationError(Exception):
    """raised when attempting to log in with an incorrect password"""


class UserNotFoundError(Exception):
    """raised when trying to log in with a username that can't be found"""


class Database:
    def __init__(self, file_path: str):
        self.connection = sqlite3.connect(file_path, check_same_thread=False)

    def get_maze_from_id(self, maze_id):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes WHERE MazeID = (?);", (maze_id,))
        info = MazeInfo(*c.fetchone())
        c.close()
        return info

    def get_all_mazes(self):
        c = self.connection.cursor()
        c.execute("SELECT MazeID, Name FROM Mazes;")
        mazes = [MazeInfo(MazeID, Name) for (MazeID, Name) in c.fetchall()]
        c.close()
        return mazes

    def add_user(self, user_info: UserInfo, password_hash: bytes):
        try:
            c = self.connection.cursor()
            c.execute("""INSERT INTO Users (Username, FirstName, LastName, PasswordHash)
                      VALUES ((?), (?), (?), (?));""",
                      (user_info.username, user_info.first_name, user_info.last_name,
                       password_hash))
        except sqlite3.IntegrityError as e:
            raise UserAlreadyExistsError(f"User with username '{user_info.username}' already exists")
        finally:
            c.close()
            self.connection.commit()

    def get_user_from_username(self, username: str):
        try:
            c = self.connection.cursor()
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
        try:
            c = self.connection.cursor()
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
            raise UserAlreadyExistsError(f"User with username '{new_username}' already exists")
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
