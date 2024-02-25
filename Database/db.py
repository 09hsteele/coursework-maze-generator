import sqlite3

class Database:
    def __init__(self, db_filepath: str):
        self.con = sqlite3.connect(db_filepath)

    def setup(self):
        print("setup db")