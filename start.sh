#!/bin/bash

echo "Installing dependencies..."
pip install flask flask-cors flask-bcrypt flask-jwt-extended openai python-dotenv

if [ ! -f "database.sqlite" ]; then
    echo "Creating database..."
    sqlite3 database.sqlite <<EOF
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    skills TEXT DEFAULT '[]',
    experience TEXT DEFAULT '[]',
    languages TEXT DEFAULT '[]',
    FOREIGN KEY (user_id) REFERENCES users (id)
);
EOF
    echo "Database created successfully"
fi

echo "Starting the server..."
python backend1.py &
SERVER_PID=$!

echo "Waiting for server to start..."
sleep 3

echo "Opening Workly in your browser..."
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    open http://127.0.0.1:5003
elif [ "$(uname)" == "Linux" ]; then
    # Linux
    xdg-open http://127.0.0.1:5003 || sensible-browser http://127.0.0.1:5003 || firefox http://127.0.0.1:5003
else
    # Windows
    start http://127.0.0.1:5003 || explorer "http://127.0.0.1:5003"
fi

echo "Workly platform is now running!"

wait $SERVER_PID