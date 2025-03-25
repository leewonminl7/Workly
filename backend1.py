from flask import Flask, request, jsonify, send_from_directory
import os
import sqlite3
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from dotenv import load_dotenv
import json


load_dotenv()

app = Flask(__name__, static_folder="frontend")
CORS(app)
bcrypt = Bcrypt(app)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "supersecret")
jwt = JWTManager(app)

DATABASE = "database.sqlite"

# Database
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    return conn

# Initialise database tables
def init_db():
    with get_db() as db:
        # Users table 
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User_profiles table 
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                skills TEXT DEFAULT '[]',
                experience TEXT DEFAULT '[]',
                languages TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor = db.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if "updatedAt" not in columns:
            print("⚠️ 'updatedAt' column missing. Adding it now...")
            db.execute("ALTER TABLE users ADD COLUMN updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            db.commit()
            print("'updatedAt' column added successfully!")
            
        db.commit()
    
    print("Database initialized successfully!")

init_db()

# Serve Frontend
@app.route("/")
def serve_frontend():
    if os.path.exists(os.path.join(app.static_folder, "index.html")):
        return send_from_directory(app.static_folder, "index.html")
    return "Frontend not found. Please ensure 'index.html' is in the 'frontend' folder.", 404

@app.route("/<path:path>")
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)

# Sign up
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    with get_db() as db:
        # Check if the user already exists
        existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if existing_user:
            # Redirect to login
            return jsonify({"error": "User already exists", "redirect": "login"}), 400 

        # Insert new user
        db.execute("""
            INSERT INTO users (name, email, password, createdAt, updatedAt)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (name, email, hashed_password))

        # New user's ID
        user_id = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]

        # Empty profile for the user
        db.execute("""
            INSERT INTO user_profiles (user_id, skills, experience, languages)
            VALUES (?, '[]', '[]', '[]')
        """, (user_id,))

        db.commit()

    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201

# Login
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email, password = data["email"], data["password"]

    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 400

    user_id = user["id"]

    with get_db() as db:
        profile = db.execute("SELECT skills, experience, languages FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()

    # Use default values 
    skills = json.loads(profile["skills"]) if profile and profile["skills"] else []
    experience = json.loads(profile["experience"]) if profile and profile["experience"] else []
    languages = json.loads(profile["languages"]) if profile and profile["languages"] else []

    token = create_access_token(identity={"id": user["id"], "name": user["name"], "email": user["email"]})
    
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "profile": {
                "skills": skills,
                "experience": experience,
                "languages": languages
            }
        }
    })

# Save profile data
@app.route("/profile", methods=["POST"])
def save_profile():
    data = request.get_json()

    user_id = data.get("user_id")
    skills = json.dumps(data.get("skills", []))  
    experience = json.dumps(data.get("experience", []))  
    languages = json.dumps(data.get("languages", []))  

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    with get_db() as db:
        existing_profile = db.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()

        if existing_profile:
            db.execute(
                "UPDATE user_profiles SET skills = ?, experience = ?, languages = ? WHERE user_id = ?",
                (skills, experience, languages, user_id),
            )
        else:
            db.execute(
                "INSERT INTO user_profiles (user_id, skills, experience, languages) VALUES (?, ?, ?, ?)",
                (user_id, skills, experience, languages),
            )
        db.commit()

    return jsonify({"message": "Profile data saved successfully"}), 201

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5003)