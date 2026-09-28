import sqlite3

username = input("Enter username to make admin: ").strip()
conn = sqlite3.connect("database.db")
try:
    cur = conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    conn.commit()
    if cur.rowcount:
        print(f"{username} is now a Quizora administrator. Logout and login again.")
    else:
        print("No such user. Register first, then run this again.")
finally:
    conn.close()
