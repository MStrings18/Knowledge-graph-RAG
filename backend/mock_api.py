from flask import Flask, request, jsonify
import sqlite3
from uuid import uuid4

app = Flask(__name__)

# Ensure the correct path to your mock_insurance.db
DB_PATH = os.getenv("MOCK_DB_PATH") or os.path.join(config.BASE_DIR, "mock_insurance.db")

def get_user_by_username(username):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT insurance_user_id, password FROM insurance_users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(f"[ERROR] Database query failed: {e}")
        return None

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"success": False, "message": "Username and password are required."}), 400

        user = get_user_by_username(username)
        if not user or user[1] != password:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        return jsonify({"success": True, "user_id": user[0]})
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@app.route("/change_credentials", methods=["POST"])
def change_credentials():
    data = request.json
    username = data.get("username")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not all([username, old_password, new_password]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    user = get_user_by_username(username)
    if not user or user[1] != old_password:
        return jsonify({"success": False, "message": "Old password incorrect."}), 401

    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("UPDATE insurance_users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to update password: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500

    return jsonify({"success": True, "reference_id": str(uuid4())})

@app.route("/update_policy", methods=["POST"])
def update_policy():
    data = request.json
    if 'user_id' not in data:
        return jsonify({"message": "user_id is required.", "success": False}), 400
    reference_id = str(uuid4())
    return jsonify({"reference_id": reference_id}), 200


@app.route("/file_claim", methods=["POST"])
def file_claim():
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "user_id is required."}), 400

    reference_id = str(uuid4())
    return jsonify({"success": True, "reference_id": reference_id})

@app.route("/policy_document/<reference_id>", methods=["GET"])
def get_policy_document(reference_id):
    return jsonify({
        "ref_id": reference_id,
        "content": "Mock PDF content of the policy document.",
        "generated_at": "2025-09-12T12:00:00"
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Endpoint not found."}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "message": "Internal server error."}), 500

if __name__ == "__main__":
    app.run(port=5000)
