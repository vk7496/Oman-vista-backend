import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "Backend is running 🚀"})

@app.route("/map")
def map_service():
    return jsonify({"map": "Map service placeholder 🌍"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway پورت خودش رو میده
    app.run(host="0.0.0.0", port=port)
