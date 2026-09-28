import json
import os
import sqlite3


DATABASE = "database.db"
QUESTION_BANK_FOLDER = "question_bank"

QUESTION_FILES = [
    "c_questions.json",
    "python_questions.json",
    "dbms_questions.json",
    "sql_questions.json",
    "aptitude_questions.json",
    "reasoning_questions.json"
]


def load_questions():
    all_questions = []

    for filename in QUESTION_FILES:
        file_path = os.path.join(
            QUESTION_BANK_FOLDER,
            filename
        )

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:
                questions = json.load(file)

                if not isinstance(questions, list):
                    print(
                        f"❌ {filename} must contain a JSON list."
                    )
                    continue

                all_questions.extend(questions)

                print(
                    f"📘 {filename}: "
                    f"{len(questions)} questions loaded"
                )

        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")

        except json.JSONDecodeError as error:
            print(
                f"❌ Invalid JSON in {filename}: {error}"
            )

    return all_questions


def seed_database():
    questions = load_questions()

    print()
    print(
        f"Total questions found in JSON files: "
        f"{len(questions)}"
    )
    print()

    if not questions:
        print("No new questions found in the JSON files.")
        print("The existing database has NOT been changed.")
        return

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    added = 0
    skipped = 0
    invalid = 0

    required_fields = [
        "subject",
        "topic",
        "difficulty",
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_answer",
        "explanation"
    ]

    for item in questions:

        # Make sure every question contains all required fields.
        if not all(field in item for field in required_fields):
            invalid += 1
            print(
                "⚠️ Skipped an invalid question because "
                "one or more fields are missing."
            )
            continue

        subject = item["subject"].strip()
        topic = item["topic"].strip()
        difficulty = item["difficulty"].strip()
        question = item["question"].strip()

        option_a = item["option_a"].strip()
        option_b = item["option_b"].strip()
        option_c = item["option_c"].strip()
        option_d = item["option_d"].strip()

        correct_answer = item["correct_answer"].strip()
        explanation = item["explanation"].strip()

        if difficulty not in [
            "Easy",
            "Medium",
            "Hard"
        ]:
            invalid += 1
            print(
                f"⚠️ Invalid difficulty skipped: "
                f"{question}"
            )
            continue

        valid_answers = [
            option_a,
            option_b,
            option_c,
            option_d
        ]

        if correct_answer not in valid_answers:
            invalid += 1
            print(
                f"⚠️ Correct answer does not match "
                f"an option: {question}"
            )
            continue

        # Check whether the question already exists.
        cursor.execute(
            """
            SELECT id
            FROM questions
            WHERE subject = ?
              AND topic = ?
              AND question = ?
            """,
            (
                subject,
                topic,
                question
            )
        )

        existing_question = cursor.fetchone()

        if existing_question:
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO questions (
                subject,
                topic,
                difficulty,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                explanation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject,
                topic,
                difficulty,
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                explanation
            )
        )

        added += 1

    connection.commit()
    connection.close()

    print()
    print("========================================")
    print("       QUIZORA QUESTION SEEDER")
    print("========================================")
    print(f"Questions added   : {added}")
    print(f"Questions skipped : {skipped}")
    print(f"Invalid questions : {invalid}")
    print(f"Questions read    : {len(questions)}")
    print("========================================")
    print()
    print("🌱 Quizora question bank update complete!")


if __name__ == "__main__":
    seed_database()