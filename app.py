from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import csv
import os
import json
import webview

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'expenses.db'

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        amount REAL NOT NULL,
                        date TEXT NOT NULL,
                        category TEXT NOT NULL,
                        description TEXT,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )''')
    conn.commit()
    conn.close()

init_db()

# Database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

# Home
@app.route('/', methods=['GET'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    search_query = request.args.get('search')
    if search_query:
        cursor.execute("SELECT * FROM expenses WHERE user_id=? AND title LIKE ?", (session['user_id'], f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM expenses WHERE user_id=?", (session['user_id'],))

    expenses = cursor.fetchall()

    total_amount = sum(expense[2] for expense in expenses)

    # Data for graph
    categories = {}
    for expense in expenses:
        category = expense[4]
        amount = expense[2]
        if category in categories:
            categories[category] += amount
        else:
            categories[category] = amount

    labels = list(categories.keys())
    values = list(categories.values())

    conn.close()

    return render_template('index.html', expenses=expenses, total_amount=total_amount, labels=labels, values=values)

# Add expense
@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    amount = float(request.form['amount'])
    date = request.form['date']
    category = request.form['category']
    description = request.form.get('description', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO expenses (title, amount, date, category, description, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                   (title, amount, date, category, description, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Edit expense
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        date = request.form['date']
        category = request.form['category']
        description = request.form.get('description', '')

        cursor.execute('''UPDATE expenses
                          SET title=?, amount=?, date=?, category=?, description=?
                          WHERE id=? AND user_id=?''',
                       (title, amount, date, category, description, id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    cursor.execute('SELECT * FROM expenses WHERE id=? AND user_id=?', (id, session['user_id']))
    expense = cursor.fetchone()
    conn.close()

    if expense:
        return render_template('edit.html', expense=expense)
    else:
        return redirect(url_for('index'))

# Delete expense
@app.route('/delete/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id=? AND user_id=?', (id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Download CSV
@app.route('/download')
def download_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT title, amount, date, category, description FROM expenses WHERE user_id=?', (session['user_id'],))
    expenses = cursor.fetchall()
    conn.close()

    csv_file = 'expenses.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Amount', 'Date', 'Category', 'Description'])
        writer.writerows(expenses)

    return send_file(csv_file, as_attachment=True)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid Credentials")

    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Username already exists")

    return render_template('register.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Run app inside Desktop Windows
if __name__ == '__main__':
    webview.create_window('Personal Expense Tracker', app, width=1200, height=800)
    webview.start()
