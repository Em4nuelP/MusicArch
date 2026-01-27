from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.route("/last-folder", methods=["GET"])
def get_last_folder():
    config = load_config()
    return jsonify({
        "folder": config.get("last_folder", "")
    })

@app.route("/last-folder", methods=["POST"])
def set_last_folder():
    data = request.json
    config = load_config()
    config["last_folder"] = data.get("folder", "")
    save_config(config)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
