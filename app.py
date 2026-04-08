from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect('database.db')

    conn.execute('''CREATE TABLE IF NOT EXISTS student(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reg TEXT,
                    name TEXT,
                    dept TEXT,
                    cgpa REAL,
                    result TEXT
                    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS subjects(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reg TEXT,
                    subject TEXT,
                    marks INTEGER,
                    credit INTEGER
                    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    password TEXT
                    )''')

    # Default Login
    user = conn.execute("SELECT * FROM users WHERE username='adi_saini6066'").fetchone()
    if not user:
        conn.execute("INSERT INTO users VALUES (NULL,?,?)", ("adi_saini6066","Aditya63"))

    conn.commit()
    conn.close()

init_db()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        # Check if username already exists
        existing_user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        
        if existing_user:
            conn.close()
            return "Username already exists! Try another."
        
        # Insert the new user into the database
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return redirect('/login')
        
    return render_template("register.html")


# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            error = "Invalid Username or Password"

    return render_template("login.html", error=error)

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- HOME ----------



@app.route('/', methods=['GET','POST'])
def index():
    if 'user' not in session:
        return redirect('/login')

    cgpa = None
    result = None

    if request.method == 'POST':
        reg = request.form['reg']
        name = request.form['name']
        dept = request.form['dept']

        total_points = 0
        total_credits = 0
        fail = False

        conn = sqlite3.connect('database.db')

        #  Dynamic subjects loop
        for key in request.form:
            if key.startswith("marks"):
                i = key.replace("marks","")

                sub = request.form.get(f"sub{i}")
                marks = int(request.form.get(f"marks{i}", 0))
                credit = int(request.form.get(f"credit{i}", 1))

                if marks < 40:
                    fail = True

                grade_point = marks / 10
                total_points += grade_point * credit
                total_credits += credit

                conn.execute(
                    "INSERT INTO subjects VALUES (NULL,?,?,?,?)",
                    (reg, sub, marks, credit)
                )

        # CGPA + Result
        cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
        result = "Fail" if fail else "Pass"

        conn.execute(
            "INSERT INTO student VALUES (NULL,?,?,?,?,?)",
            (reg, name, dept, cgpa, result)
        )

        conn.commit()
        conn.close()

    return render_template("index.html", cgpa=cgpa, result=result)

# ---------- RECORDS ----------
@app.route('/records')
def records():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    students = conn.execute("SELECT * FROM student").fetchall()
    conn.close()

    return render_template("records.html", students=students)

# ---------- SEARCH ----------
@app.route('/search', methods=['GET','POST'])
def search():
    if 'user' not in session:
        return redirect('/login')

    student = None
    subjects = []

    if request.method == 'POST':
        reg = request.form['reg']

        conn = sqlite3.connect('database.db')
        student = conn.execute(
            "SELECT * FROM student WHERE reg=?",
            (reg,)
        ).fetchone()

        subjects = conn.execute(
            "SELECT * FROM subjects WHERE reg=?",
            (reg,)
        ).fetchall()

        conn.close()

        # Save last search for PDF
        session['last_search'] = reg

    return render_template("search.html", student=student, subjects=subjects)

# ---------- PDF ----------
@app.route('/download')
def download():
    if 'user' not in session:
        return redirect('/login')

    reg = session.get('last_search')

    if not reg:
        return "No student selected!"

    conn = sqlite3.connect('database.db')
    student = conn.execute("SELECT * FROM student WHERE reg=?", (reg,)).fetchone()
    subjects = conn.execute("SELECT * FROM subjects WHERE reg=?", (reg,)).fetchall()
    conn.close()

    doc = SimpleDocTemplate("result.pdf")
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"Name: {student[2]}", styles['Normal']))
    content.append(Paragraph(f"Reg: {student[1]}", styles['Normal']))
    content.append(Paragraph(f"Dept: {student[3]}", styles['Normal']))
    content.append(Paragraph(f"CGPA: {student[4]}", styles['Normal']))
    content.append(Paragraph(f"Result: {student[5]}", styles['Normal']))

    content.append(Paragraph("<br/>Subjects:", styles['Normal']))

    for s in subjects:
        content.append(
            Paragraph(f"{s[2]} - Marks: {s[3]} | Credit: {s[4]}", styles['Normal'])
        )

    doc.build(content)

    return send_file("result.pdf", as_attachment=True)

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)