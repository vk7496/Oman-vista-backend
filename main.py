from flask import Flask, jsonify
import os

# ساخت اپلیکیشن Flask
app = Flask(__name__)

# روت اصلی (تست سلامت سرور)
@app.route("/")
def home():
    return jsonify({"message": "Backend is running 🚀"})

# روت نمونه برای نقشه (بعداً می‌تونیم کاملش کنیم)
@app.route("/map")
def map_page():
    return jsonify({"map": "Map service placeholder 🌍"})

# ران کردن اپلیکیشن روی Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway خودش PORT می‌ده
    app.run(host="0.0.0.0", port=port)
