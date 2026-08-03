import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, request, render_template
from app.config import Config
from app.agents.verification_agent import VerificationAgent


def create_app():
    app = Flask(__name__, template_folder=str(ROOT_DIR / 'templates'))
    app.config.from_object(Config)

    verification_agent = VerificationAgent()

    @app.route('/', methods=['GET'])
    def home():
        return render_template('index.html')

    @app.route('/verify', methods=['GET', 'POST'])
    def verify_document():
        if request.method == 'GET':
            return jsonify({
                "message": "Send a POST request to /verify with JSON data.",
                "example": {
                    "name": "Jane Doe",
                    "id": "123456",
                    "documents": ["id_card"],
                    "use_fake_data": True,
                },
            })

        document = request.get_json(silent=True) or {}
        confirmation = bool(document.get("confirmation"))
        if confirmation or document.get("confirm"):
            result = verification_agent.run_agent_loop(document, confirmation=True)
        else:
            result = verification_agent.run_agent_loop(document, confirmation=False)

        response = {
            "status": result.get("status", "pending"),
            "verified": result.get("is_verified", False) or result.get("status") == "verified",
            "message": result.get("message", "Verification completed."),
            "missing_documents": result.get("missing_documents", []),
            "trainee_id": document.get("id") or document.get("trainee_id") or document.get("id_number"),
        }
        return jsonify(response)

    @app.route('/upload', methods=['POST'])
    def upload_document():
        if 'file' not in request.files:
            return jsonify({"is_valid": False, "message": "No file was uploaded."}), 400

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return jsonify({"is_valid": False, "message": "No file was selected."}), 400

        filename = uploaded_file.filename or 'uploaded_document'
        file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        document = {
            "name": uploaded_file.filename,
            "id": "uploaded-file",
            "documents": [file_extension] if file_extension else ["unknown"],
            "use_fake_data": True,
        }

        result = verification_agent.verify_document(document)
        response = {
            "filename": filename,
            "file_type": file_extension,
            "status": result.get("status", "pending"),
            "verified": result.get("is_valid", False) and result.get("status") != "pending",
            "message": result.get("message", "Verification completed."),
            "missing_documents": result.get("missing_documents", []),
        }
        return jsonify(response)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)