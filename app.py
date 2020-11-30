from flask import Flask, render_template, request, redirect, jsonify, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from tempfile import mkdtemp
import sqlite3, datetime
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, apology, is_comment_inapporiate
import os,binascii,threading,time
from database import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'GetRektMur4tReyiz#'
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DBNAME = "database.db"
START_CURRENCY = 5000
BONUS = 200
REGISTERS = {}
QUIZ = [
    ["Monday 363 Quiz" ,0,14],
    ["Tuesday 373 Quiz" ,1,10],
    ["Thursday 373 Quiz" ,3,10],
    ["Thursday 363 Quiz" ,3,14]
    ]


chatlog = None
N = 20
db_initial()
current_poll = [0, 0]
pool = 0
current_poll_name = None
polling_active = True
waiting = []

class choose_poll(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def terminate(self):
        self._running = False

    def run(self):
        global polling_active
        global current_poll_name
        global current_poll
        global pool
        while polling_active:
            if current_poll_name == None:
                row = query_db("SELECT * FROM quiz WHERE active = 1")
                if len(row) > 1:
                    end_poll()
                elif len(row) == 1:
                    pool = 0
                    current_poll = [0,0]
                    row2 = query_db("SELECT * FROM quiz_bets WHERE quiz_id = ?", (row[0]["id"],))
                    for i in range(len(row2)):
                        pool += int(row2[i]["bet"])
                        current_poll[int(row2[i]["choice"])] += 1
                        current_poll_name = int(row[0]["name"])
                    continue
                today = datetime.datetime.today().weekday()
                hour = datetime.datetime.now().hour + 3
                flag = True
                for i in range(len(QUIZ)):
                    if (today == QUIZ[i][1] and hour < QUIZ[i][2]) or today < QUIZ[i][1]:
                        current_poll_name = i
                        flag = False
                        break
                if flag:
                    current_poll_name = 0
                start_poll(current_poll_name)
            else:
                today = datetime.datetime.today().weekday()
                hour = datetime.datetime.now().hour
                if (hour + 3>= QUIZ[current_poll_name][2] and today == QUIZ[current_poll_name][1]):
                    end_poll()
                    current_poll_name = None
            time.sleep(2)
thread1 = choose_poll()

def start_poll(poll):
    global pool
    global current_poll
    global current_poll_name
    current_poll = [0, 0]
    pool = 0
    current_poll_name = poll
    query_db("INSERT INTO quiz (active, name, pool) VALUES (1, ?, ?)", (poll, pool, ))

def end_poll():
    row = query_db("SELECT * FROM quiz WHERE active = 1")
    global waiting
    global current_poll
    if len(row) != 0:
        waiting.append([int(row[0]["id"]),int(row[0]["name"]), pool, current_poll])
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query_db("UPDATE quiz SET active = 0, date = ?, pool = ? WHERE active = 1", (now ,pool))
def reward(pollid, result):
    row = query_db("SELECT * FROM quiz_bets WHERE quiz_id = ?;", (pollid, ))
    num = [0,0]
    for r in row:
        if r["choice"] == 1:
            num[1] += 1
        else:
            num[0] += 1
    localratio = (num[not result] + 1) /  (num[0] + num[1] + 1) + 1.1
    query_db("UPDATE quiz SET result= ? WHERE id = ?", (result, pollid, ))
    rows = query_db("SELECT * FROM quiz_bets WHERE quiz_id = ? and choice = ?", (pollid, result, ))
    for row in rows:
        query_db("UPDATE users SET currency = currency + ? , win = win + 1 WHERE id = ?", (row["bet"] * localratio, row["user_id"], ))

@app.route("/bet", methods=["POST"])
@login_required
def bet():
    try:
        bet = int(request.form.get("amount"))
        choice = int(request.form.get("choice"))
        userid = session.get("user_id")
        currency = session.get("currency")
    except:
        return render_template("error.html", message="Aga yanlis isler kovaliyorsun, yapma")
    if currency < bet:
        return render_template("error.html", message="You don't have enough money")
    row = query_db("SELECT id FROM quiz WHERE active = 1")
    if len(row) != 1:
        return render_template("error.html", message="Something happened")
    rows = query_db("SELECT id FROM quiz_bets WHERE user_id = ? AND quiz_id = ?", (userid, row[0]["id"], ))
    if len(rows) != 0:
        return render_template("error.html", message="You have already played")
    current_poll[choice] += 1
    query_db("INSERT INTO quiz_bets (quiz_id, user_id, bet, choice) VALUES (?, ?, ?, ?)", (row[0]["id"], userid, bet, choice, ))
    currency -= bet
    global pool
    pool += bet
    session["currency"] = currency
    query_db("UPDATE users SET currency = ?, total = total + 1 WHERE id = ?", (currency, userid, ))
    return render_template("error.html", message="Your bet is taken")

@app.route("/mybetjson")
@login_required
def mybetjson():
    userid = session.get("user_id")
    row = query_db("SELECT id FROM quiz WHERE active = 1")
    rows = query_db("SELECT choice, bet FROM quiz_bets WHERE user_id = ? AND quiz_id = ?", (userid, row[0]["id"], ))
    return jsonify(rows)


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        if session.get("user_id") is not None:
            return render_template("index.html", login=True, username=session.get("user_name"), currency=session.get("currency"), win=session.get("win"), total=session.get("total"))
        else:
            return render_template("index.html", login=False)
    if request.method == "POST":
        if session.get("user_id") is not None:
            user_name = session.get("user_name")
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #db.execute("UPDATE users SET sport = ?, date = ? WHERE user_name = ?;", (sport, now, user_name,))
            return redirect("/")
        else:
            return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    user_name = request.form.get("username")
    password = request.form.get("password")
    password2 = request.form.get("password2")
    if not password or not password2 or len(str(password)) > 15 or password != password2:
        return render_template("error.html", message="Invalid password or they do not match")
    if not user_name or is_comment_inapporiate(user_name) or len(user_name) > 15 or "all" == user_name or "root" == user_name:
        return render_template("error.html", message="Invalid username")
    row = query_db("SELECT * FROM users WHERE user_name = ?", (user_name,))
    if len(row) != 0:
        return render_template("error.html", message="This username is used")
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query_db("INSERT INTO users (user_name, password_hash, date, color, currency, win, total) VALUES ( ? , ?, ?, ?, ?, 0, 0);", (user_name, generate_password_hash(password), now, str(binascii.b2a_hex(os.urandom(3)))[2:-1], START_CURRENCY, ))
    row = query_db("SELECT * FROM users WHERE user_name = ?", (user_name,))
    session["user_id"] = row[0]["id"]
    session["user_name"] = user_name
    session["color"] = row[0]["color"]
    session["currency"] = row[0]["currency"]
    session["win"] = row[0]["win"]
    session["total"] = row[0]["total"]
    return render_template("success.html", message="Successfully registered")

@app.route("/list", methods=["GET"])
def list():
    return render_template("list.html")



@app.route("/searchjson", methods=["GET"])
def searchjson():
    q = "%" + str(request.args.get("q")) + "%"
    rows = query_db("SELECT user_name, currency, win, total FROM users WHERE user_name LIKE ? ORDER BY currency DESC, win DESC, total DESC LIMIT ? ;", (q, N, ))
    for i in range(len(rows)):
        rows[i]["rank"] = i + 1
    return jsonify(rows)

@app.route("/search", methods=["GET"])
def search():
    return render_template("search.html")

@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        username = session["user_name"]
        color = session["color"]
        message = request.form.get("message")
        if message and color and username:
            if not is_comment_inapporiate(message):
                global chatlog
                if session.get("user_name") == "emre":
                    command = message.split()
                    if command[0] == "/clear":
                        try:
                            variable = command[1]
                            if variable == "all":
                                query_db("DELETE FROM chat_log;")
                            else:
                                try:
                                    val = int(command[2])
                                    query_db("DELETE FROM chat_log Where username = ? order by id desc limit ?;", (variable, val, ))
                                except:
                                    query_db("DELETE FROM chat_log Where username = ?;", (variable,))
                        finally:
                            global chatlog
                    elif command[0] == "/bet":
                        betid = int(command[1])
                        result = int(command[2])
                        reward(betid, result)
                        username = "root"
                        message = "Rewards are given " + betid + " " + result
                    elif command[0] == "/waiting":
                        global waiting
                        username = "root"
                        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if len(waiting) == 0:
                            row = query_db("SELECT * FROM quiz WHERE active=0 and pool !=0 ORDER BY id DESC;")
                            if(len(row)!= 0):
                                waiting.append([int(row[0]["id"]),int(row[0]["name"]), 1, row[0]["pool"]])
                        for i in range(len(waiting)):
                            message = str(waiting[0]) + " " + str(waiting[1]) + " " + str(waiting[2]) + " " + str(waiting[3])
                            query_db("INSERT INTO chat_log (username, color, message, date) VALUES ( ? , ?, ?, ?);", (username, color, message, now, ))
                        message = "All waiting bets are listed"
                    elif command[0] == "/polling":
                        i = int(command[1])
                        global polling_active
                        message = ""
                        if i != polling_active:
                            if i == 0:
                                polling_active = 0
                            else:
                                polling_active = 1
                                thread1 = choose_poll()
                        message += str(polling_active)

                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                query_db("INSERT INTO chat_log (username, color, message, date) VALUES ( ? , ?, ?, ?);", (username, color, message, now, ))
                rows = query_db("SELECT * FROM (SELECT username, message, date, color FROM chat_log order by id DESC limit ?) ORDER BY date ASC;", (N,))
                chatlog = jsonify(rows)
    return render_template('chat.html')


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id") is not None:
            return redirect("/")
        return render_template("login.html")
    if request.method == "POST":
        user_name = request.form.get("username")
        password = request.form.get("password")
        if not user_name or user_name == "":
            return render_template("error.html", message="Invalid username")
        row = query_db("SELECT * FROM users WHERE user_name = ?", (user_name,))
        if len(row) != 1 or not check_password_hash(row[0]["password_hash"], password):
            return render_template("error.html", message="Invalid username or password", redirect="login")
        form = '%Y-%m-%d %H:%M:%S'
        now = datetime.datetime.now().strftime(form)
        query_db("INSERT INTO login_history (userid, date) VALUES (?, ?)", (row[0]["id"], now,  ))
        session["currency"] = row[0]["currency"]
        if (datetime.datetime.strptime(now, form) -datetime.datetime.strptime(row[0]["date"], form)).days >= 1:
            query_db("UPDATE users SET date = ?, currency = ? WHERE user_name = ?;", (now, row[0]["currency"] + BONUS, user_name ))
            session["currency"] = row[0]["currency"] + BONUS
        session["user_id"] = row[0]["id"]
        session["user_name"] = user_name
        session["color"] = row[0]["color"]
        session["win"] = row[0]["win"]
        session["total"] = row[0]["total"]
        return render_template("error.html", message="Logged in")

@app.route("/logout")
def logout():
    session.clear()
    return render_template("error.html", message="Logged out")

@app.route("/chatjson")
def chatjson():
    if session.get("user_id") == None:
        return None
    global chatlog
    if chatlog == None:
        rows = query_db("SELECT * FROM (SELECT username, message, date, color FROM chat_log order by id DESC limit ?) ORDER BY date ASC;", (N,))
        chatlog = jsonify(rows)
    return chatlog

@app.route("/betjson")
def betjson():
    d = {}
    global current_poll_name
    if current_poll_name != None:
        cp = current_poll_name
        d = {"name" : QUIZ[current_poll_name][0],
             "untill": QUIZ[current_poll_name][2],
             "yes" : current_poll[1],
             "no" : current_poll[0],
             "pool": pool
             }
    return jsonify([d])

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
thread1.start()
if __name__ == '__main__':
    app.run(threaded=True, port=5000)


