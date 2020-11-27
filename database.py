import sqlite3

from flask import g
import datetime, binascii, os
from werkzeug.security import check_password_hash, generate_password_hash

DBNAME = "database.db"
def get_db():
    db = sqlite3.connect(
                    DBNAME,
                    detect_types=sqlite3.PARSE_DECLTYPES
    )
    db.row_factory = lambda c, r: dict([(col[0], r[idx]) for idx, col in enumerate(c.description)])
    return db

def query_db(query, args=(), one=False):
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    db.commit()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def db_initial():
    query_db("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE, user_name TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, date DATETIME, color CHAR(6) NOT NULL, currency INT NOT NULL, win INTEGER, total INTEGER)")
    query_db("CREATE TABLE IF NOT EXISTS login_history(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, userid INTEGER REFERENCES users(id) NOT NULL, date DATETIME NOT NULL)")
    query_db("CREATE TABLE IF NOT EXISTS chat_log(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT REFERENCES users(user_name) NOT NULL, message TEXT NOT NULL, date DATETIME NOT NULL, color TEXT not NULL)")
    query_db("CREATE TABLE IF NOT EXISTS quiz(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, active BIT, result BIT, name INTEGER NOT NULL, date DATETIME, pool INTEGER)")
    query_db("CREATE TABLE IF NOT EXISTS quiz_bets(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, quiz_id INTEGER REFERENCES quiz(id), user_id INTEGER REFERENCES users(id), bet INTEGER, choice BIT)")
    u = query_db("SELECT * FROM users WHERE user_name='emre'")
    if len(u) == 0:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query_db("INSERT INTO users (user_name, password_hash, date, color, currency, win, total) VALUES ( ? , ?, ?, ?, ?, 0, 0);", ("emre", generate_password_hash("123"), now, str(binascii.b2a_hex(os.urandom(3)))[2:-1], 5000, ))

