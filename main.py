from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import requests
import json
import random
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------
# REQUEST MODELS
# -----------------------------
class ExplanationRequest(BaseModel):
    question: str
    correct: str
    selected: str


# FRONTEND
# -----------------------------
@app.get("/")
def serve_frontend():
    return FileResponse("static/static.html")


# -----------------------------
# GET RANDOM DATABASE QUESTION
# -----------------------------
@app.get("/random_question")
def random_question():

    conn = sqlite3.connect("coding_practice.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM quiz_questions
        ORDER BY RANDOM()
        LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if not row:
        raise HTTPException(404, "No questions found")

    return {
        "id": row[0],
        "category": row[1],
        "difficulty": row[2],
        "question_text": row[3],
        "option_a": row[4],
        "option_b": row[5],
        "option_c": row[6],
        "option_d": row[7],
        "correct_option": row[8]
    }


# -----------------------------
# AI GENERATED QUESTION
# -----------------------------
@app.get("/generate_ai_question")
def generate_ai_question():

    prompt = """
Generate ONE Python multiple choice question.

Return ONLY valid JSON.

Format:
{
  "category": "Python",
  "difficulty": "Easy",
  "question_text": "What does len() do?",
  "option_a": "Adds numbers",
  "option_b": "Returns length",
  "option_c": "Deletes variables",
  "option_d": "Opens files",
  "correct_option": "B"
}

Rules:
- Must be beginner friendly
- Only Python questions
- 4 options
- correct_option must be A B C or D
- Return ONLY JSON
"""

    groq_key = os.getenv("GROQ_API_KEY")
    
    try:
        # Try cloud API first (Groq) if key exists
        if groq_key:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                },
                timeout=40
            )
            response.raise_for_status()
            data = response.json()
            ai_text = data["choices"][0]["message"]["content"].strip()
            print(f"[CLOUD] Using Groq API")
        else:
            # Fallback to local Ollama
            response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "deepseek-coder:6.7b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=40
            )
            response.raise_for_status()
            data = response.json()
            ai_text = data["response"].strip()
            print(f"[LOCAL] Using Ollama")

        question = json.loads(ai_text)
        
        # Validate all required fields
        required = [
            "category", "difficulty", "question_text",
            "option_a", "option_b", "option_c", "option_d", "correct_option"
        ]
        for field in required:
            if field not in question:
                raise Exception(f"Missing field: {field}")
        
        # ========================
        # SAVE AI QUESTION TO DATABASE
        # ========================
        conn = sqlite3.connect("coding_practice.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quiz_questions
            (
                category,
                difficulty,
                question_text,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_option
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question["category"],
            question["difficulty"],
            question["question_text"],
            question["option_a"],
            question["option_b"],
            question["option_c"],
            question["option_d"],
            question["correct_option"]
        ))

        conn.commit()
        conn.close()
        # ========================

        return question

    except Exception as e:

        print("AI FAILED:", str(e))

        # FALLBACK TO DATABASE
        conn = sqlite3.connect("coding_practice.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM quiz_questions
            ORDER BY RANDOM()
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(500, "AI failed and no DB questions found")

        return {
            "id": row[0],
            "category": row[1],
            "difficulty": row[2],
            "question_text": row[3],
            "option_a": row[4],
            "option_b": row[5],
            "option_c": row[6],
            "option_d": row[7],
            "correct_option": row[8]
        }



# -----------------------------
# EXPLAIN ANSWER
# -----------------------------
@app.post("/explain_answer")
def explain_answer(payload: ExplanationRequest):
    question = payload.question
    correct = payload.correct
    selected = payload.selected
    
    prompt = f"""You are a helpful Python tutor. Explain clearly to a beginner.

Question: {question}
Correct Answer: {correct}
User chose: {selected}

Explain in simple language why {correct} is correct and why {selected} is wrong. Be encouraging.

Rules:
- Maximum 70 words
- Very simple English
- No markdown, no bullet points
- Be encouraging"""

    groq_key = os.getenv("GROQ_API_KEY")
    
    try:
        # Try cloud API first (Groq) if key exists
        if groq_key:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 300
                },
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            explanation = data["choices"][0]["message"]["content"].strip()
            print(f"[CLOUD] Using Groq API for explanation")
        else:
            # Fallback to local Ollama
            response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3.1:8b",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.6,
                    "max_tokens": 300
                },
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            explanation = data["response"].strip()
            print(f"[LOCAL] Using Ollama for explanation")
        
        return {"explanation": explanation}

    except Exception as e:
        print("Explanation AI FAILED:", str(e))
        return {
            "explanation": "Sorry, I couldn't generate an explanation right now. Please try again."
        }