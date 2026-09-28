import os, sqlite3
from contextlib import closing
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
LIMIT = 15          # max questions per quiz
SECS_PER_Q = 40     # timer = 40 seconds x number of questions
DIFFS = ["Easy", "Medium", "Hard"]


def query(sql, args=(), one=False, write=False):
    """Run one parameterized SQL statement and return rows."""
    with closing(sqlite3.connect(DB)) as c:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        cur = c.execute(sql, args)
        rows = cur.fetchall()
        if write:
            c.commit()
        return (rows[0] if rows else None) if one else rows


def init_db():
    with closing(sqlite3.connect(DB)) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, is_admin INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL, topic TEXT NOT NULL, difficulty TEXT NOT NULL,
            question TEXT NOT NULL, option_a TEXT NOT NULL, option_b TEXT NOT NULL,
            option_c TEXT NOT NULL, option_d TEXT NOT NULL, correct_answer TEXT NOT NULL,
            explanation TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS results(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            category TEXT NOT NULL, topic TEXT NOT NULL, difficulty TEXT NOT NULL,
            score INTEGER NOT NULL, total INTEGER NOT NULL, percentage REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id));
        """)
        c.commit()


def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrap


def admin_required(f):
    @wraps(f)
    @login_required
    def wrap(*a, **k):
        # checked in the database, not only in the session
        u = query("SELECT is_admin FROM users WHERE id=?", (session["user_id"],), one=True)
        if not u or not u["is_admin"]:
            abort(403)
        return f(*a, **k)
    return wrap


def user_stats(uid):
    return query("SELECT COUNT(*) n, AVG(percentage) avg, MAX(percentage) best FROM results WHERE user_id=?",
                 (uid,), one=True)


# ---------- auth ----------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        e = request.form.get("email", "").strip().lower()
        p = request.form.get("password", "")
        if not u or not e or not p:
            flash("All fields are required.", "error")
        elif p != request.form.get("confirm", ""):
            flash("Passwords do not match.", "error")
        elif len(p) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif query("SELECT id FROM users WHERE username=? OR email=?", (u, e), one=True):
            flash("Username or email already exists.", "error")
        else:
            query("INSERT INTO users(username,email,password) VALUES(?,?,?)",
                  (u, e, generate_password_hash(p)), write=True)
            flash("Account created. Please login.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = query("SELECT * FROM users WHERE username=?", (request.form.get("username", "").strip(),), one=True)
        if u and check_password_hash(u["password"], request.form.get("password", "")):
            session.clear()
            session.update(user_id=u["id"], username=u["username"], email=u["email"], is_admin=u["is_admin"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- student pages ----------
def subject_cards():
    return query("SELECT subject, COUNT(DISTINCT topic) topics, COUNT(*) total FROM questions "
                 "GROUP BY subject ORDER BY subject")


@app.route("/dashboard")
@login_required
def dashboard():
    recent = query("SELECT * FROM results WHERE user_id=? ORDER BY date DESC, id DESC LIMIT 5", (session["user_id"],))
    return render_template("dashboard.html", stats=user_stats(session["user_id"]), recent=recent,
                           subjects=subject_cards())


@app.route("/quizzes")
@login_required
def quizzes():
    return render_template("quizzes.html", subjects=subject_cards())


@app.route("/topics/<subject>")
@login_required
def topics(subject):
    rows = query("SELECT topic, COUNT(*) total, SUM(difficulty='Easy') easy, SUM(difficulty='Medium') medium, "
                 "SUM(difficulty='Hard') hard FROM questions WHERE subject=? GROUP BY topic ORDER BY topic", (subject,))
    if not rows:
        flash("No questions available.", "error")
        return redirect(url_for("quizzes"))
    return render_template("topics.html", subject=subject, topics=rows)


@app.route("/quiz/<subject>/<topic>/<difficulty>", methods=["GET", "POST"])
@login_required
def quiz(subject, topic, difficulty):
    if difficulty not in DIFFS + ["Mixed"]:
        abort(404)
    back = redirect(url_for("topics", subject=subject))
    if request.method == "POST":
        ids = session.pop("quiz_ids", None)
        if not ids or session.pop("quiz_key", None) != [subject, topic, difficulty]:
            flash("Quiz session expired. Please start again.", "error")
            return back
        rows = {r["id"]: r for r in query(
            f"SELECT * FROM questions WHERE id IN ({','.join('?' * len(ids))})", ids)}
        review, score = [], 0
        for i in ids:                      # keeps original order
            r = rows.get(i)
            if not r:
                continue
            ans = request.form.get(f"q{i}")
            ok = ans == r["correct_answer"]
            score += ok
            review.append({"q": r, "answer": ans, "ok": ok})
        total = len(review)
        pct = round(score * 100 / total, 1) if total else 0
        query("INSERT INTO results(user_id,category,topic,difficulty,score,total,percentage) VALUES(?,?,?,?,?,?,?)",
              (session["user_id"], subject, topic, difficulty, score, total, pct), write=True)
        return render_template("result.html", review=review, score=score, total=total, pct=pct,
                               subject=subject, topic=topic, difficulty=difficulty)
    sql, args = "SELECT * FROM questions WHERE subject=? AND topic=?", [subject, topic]
    if difficulty != "Mixed":
        sql += " AND difficulty=?"
        args.append(difficulty)
    rows = query(sql + " ORDER BY RANDOM() LIMIT ?", args + [LIMIT])
    if not rows:
        flash("No questions available for this selection.", "error")
        return back
    session["quiz_ids"] = [r["id"] for r in rows]
    session["quiz_key"] = [subject, topic, difficulty]
    return render_template("quiz.html", questions=rows, subject=subject, topic=topic,
                           difficulty=difficulty, seconds=SECS_PER_Q * len(rows))


@app.route("/history")
@login_required
def history():
    rows = query("SELECT * FROM results WHERE user_id=? ORDER BY date DESC, id DESC", (session["user_id"],))
    return render_template("history.html", rows=rows)


@app.route("/analytics")
@login_required
def analytics():
    uid = session["user_id"]
    by_subject = query("SELECT category, AVG(percentage) avg, COUNT(*) n FROM results WHERE user_id=? "
                       "GROUP BY category ORDER BY avg DESC", (uid,))
    by_topic = query("SELECT category, topic, AVG(percentage) avg, COUNT(*) n FROM results WHERE user_id=? "
                     "GROUP BY category, topic ORDER BY avg ASC", (uid,))
    return render_template("analytics.html", by_subject=by_subject, by_topic=by_topic,
                           weakest=by_topic[0] if by_topic else None)


@app.route("/leaderboard")
@login_required
def leaderboard():
    rows = query("SELECT u.username, AVG(r.percentage) avg, COUNT(*) n FROM results r JOIN users u ON u.id=r.user_id "
                 "GROUP BY u.id ORDER BY avg DESC, n DESC LIMIT 10")
    return render_template("leaderboard.html", rows=rows)


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", stats=user_stats(session["user_id"]))


# ---------- admin ----------
@app.route("/admin")
@admin_required
def admin():
    stats = query("SELECT COUNT(*) total, COUNT(DISTINCT subject) subjects, COUNT(DISTINCT subject||'/'||topic) topics, "
                  "COALESCE(SUM(difficulty='Easy'),0) easy, COALESCE(SUM(difficulty='Medium'),0) medium, "
                  "COALESCE(SUM(difficulty='Hard'),0) hard FROM questions", one=True)
    recent = query("SELECT * FROM questions ORDER BY id DESC LIMIT 5")
    return render_template("admin.html", stats=stats, subjects=subject_cards(), recent=recent)


@app.route("/admin/questions")
@admin_required
def admin_questions():
    s, t, d, kw = (request.args.get(k, "").strip() for k in ("subject", "topic", "difficulty", "search"))
    sql, args = "SELECT * FROM questions WHERE 1=1", []
    for col, val in (("subject", s), ("topic", t), ("difficulty", d)):
        if val:
            sql += f" AND {col}=?"
            args.append(val)
    if kw:
        sql += " AND (question LIKE ? OR explanation LIKE ?)"
        args += [f"%{kw}%"] * 2
    rows = query(sql + " ORDER BY id DESC", args)
    return render_template("admin_questions.html", rows=rows, f=dict(subject=s, topic=t, difficulty=d, search=kw),
                           subjects=[r[0] for r in query("SELECT DISTINCT subject FROM questions ORDER BY 1")],
                           topics=[r[0] for r in query("SELECT DISTINCT topic FROM questions ORDER BY 1")])


def read_question_form():
    g = lambda k: request.form.get(k, "").strip()
    d = {k: g(k) for k in ("subject", "topic", "difficulty", "question", "option_a", "option_b",
                           "option_c", "option_d", "explanation")}
    d["correct"] = g("correct")
    return d


def validate(d, qid=0):
    need = ("subject", "topic", "question", "option_a", "option_b", "option_c", "option_d")
    if any(not d[k] for k in need):
        return "Please fill in every required field."
    if d["difficulty"] not in DIFFS:
        return "Choose a valid difficulty."
    if d["correct"] not in ("a", "b", "c", "d"):
        return "Choose the correct answer."
    if query("SELECT id FROM questions WHERE subject=? AND topic=? AND LOWER(question)=LOWER(?) AND id!=?",
             (d["subject"], d["topic"], d["question"], qid), one=True):
        return "This question already exists in that topic."


def question_form_page(d, title, qid=0):
    if request.method == "POST":
        err = validate(d, qid)
        if err:
            flash(err, "error")
        else:
            vals = [d[k] for k in ("subject", "topic", "difficulty", "question", "option_a", "option_b",
                                   "option_c", "option_d")] + [d["option_" + d["correct"]], d["explanation"]]
            if qid:
                query("UPDATE questions SET subject=?,topic=?,difficulty=?,question=?,option_a=?,option_b=?,"
                      "option_c=?,option_d=?,correct_answer=?,explanation=? WHERE id=?", vals + [qid], write=True)
                flash("Question updated successfully.", "success")
            else:
                query("INSERT INTO questions(subject,topic,difficulty,question,option_a,option_b,option_c,option_d,"
                      "correct_answer,explanation) VALUES(?,?,?,?,?,?,?,?,?,?)", vals, write=True)
                flash("Question added successfully.", "success")
            return redirect(url_for("admin_questions"))
    return render_template("question_form.html", q=d, title=title, diffs=DIFFS,
                           subjects=[r[0] for r in query("SELECT DISTINCT subject FROM questions")])


@app.route("/admin/questions/add", methods=["GET", "POST"])
@admin_required
def add_question():
    d = read_question_form() if request.method == "POST" else {"difficulty": "Easy"}
    return question_form_page(d, "Add question")


@app.route("/admin/questions/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_question(question_id):
    row = query("SELECT * FROM questions WHERE id=?", (question_id,), one=True)
    if not row:
        abort(404)
    if request.method == "POST":
        d = read_question_form()
    else:
        d = dict(row)
        d["correct"] = next((c for c in "abcd" if row["option_" + c] == row["correct_answer"]), "")
    return question_form_page(d, "Edit question", question_id)


@app.route("/admin/questions/<int:question_id>/delete", methods=["POST"])
@admin_required
def delete_question(question_id):
    query("DELETE FROM questions WHERE id=?", (question_id,), write=True)
    flash("Question deleted.", "success")
    return redirect(url_for("admin_questions"))


@app.errorhandler(403)
def e403(e):
    return render_template("error.html", code=403, msg="You don't have permission to open this page."), 403


@app.errorhandler(404)
def e404(e):
    return render_template("error.html", code=404, msg="We couldn't find that page."), 404


init_db()
if __name__ == "__main__":
    app.run(debug=True)
