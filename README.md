# Quizora — Smart Quiz & Learning Platform
Flask + SQLite + HTML/CSS/JavaScript. No AI/ML: recommendations are rule-based.

## Run
1. Install Python 3, open this folder in VS Code, open a terminal.
2. (Optional) `python -m venv venv` and activate it.
3. `pip install -r requirements.txt`
4. `python app.py` then open http://127.0.0.1:5000
5. Register an account, stop Flask (Ctrl+C), run `python make_admin.py`, enter your username.
6. `python app.py` again, logout and login: **Question Admin** appears in the sidebar.

## Notes
- Data lives in `database.db` (SQLite), created automatically. Questions are added in Question Admin; subjects/topics on student pages come from SQL queries.
- Quiz: up to 15 random questions (`ORDER BY RANDOM() LIMIT 15`); timer = 40 s × questions. Question IDs are stored in the session so grading uses the same set.
- Themes: CSS variables + `data-theme` + localStorage.
- Recommendation: topic with the lowest average percentage in your results.
- Deployment: set `SECRET_KEY` as an environment variable.

## How to explain Quizora in viva
Frontend: HTML/CSS/JS. Backend: Flask routes. Database: SQLite. Auth: sessions + hashed passwords. Questions: CRUD by admin. Randomization: SQL RANDOM(). Analytics: SQL AVG/GROUP BY. Recommendation: weakest topic by average. Themes: CSS variables + localStorage.
