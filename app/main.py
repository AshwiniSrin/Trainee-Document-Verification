import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

        document = request.get_json(silent=True)
        logger.info("Verification request received")
        logger.info(document)

        if not document:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received.",
            }), 400

        confirmation = bool(
            document.get("confirmation") or document.get("confirm", False)
        )

        try:
            result = verification_agent.run_agent_loop(
                document,
                confirmation=confirmation,
            )
        except Exception as exc:
            logger.exception("Verification request failed")
            return jsonify({
                "status": "error",
                "message": str(exc),
            }), 500

        logger.info(result)

        response = {
            **result,
            "trainee_id": document.get("trainee_id")
            or document.get("id")
            or document.get("id_number"),
        }

        status_code = 200
        if response.get("status") == "pending":
            status_code = 202
        elif response.get("status") == "rejected":
            status_code = 400

        return jsonify(response), status_code

    @app.route('/upload', methods=['POST'])
    def upload_document():
        if 'file' not in request.files:
            return jsonify({"is_valid": False, "message": "No file was uploaded."}), 400

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return jsonify({"is_valid": False, "message": "No file was selected."}), 400

        filename = uploaded_file.filename or 'uploaded_document'
        file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        inferred_documents = []
        lowered_name = filename.lower()
        if 'resume' in lowered_name or ' cv' in lowered_name or lowered_name.endswith(' re.pdf') or lowered_name.endswith(' re.docx') or lowered_name.endswith(' re.txt'):
            inferred_documents = ['resume']
        elif 'aadhaar' in lowered_name or 'aadhar' in lowered_name or 'uid' in lowered_name:
            inferred_documents = ['aadhaar']
        elif 'pan' in lowered_name or 'permanent' in lowered_name:
            inferred_documents = ['pan']
        elif 'degree' in lowered_name or 'certificate' in lowered_name or 'marksheet' in lowered_name or 'transcript' in lowered_name or 'diploma' in lowered_name:
            inferred_documents = ['degree_certificate']
        elif file_extension:
            inferred_documents = [file_extension]
        else:
            inferred_documents = ['unknown']

        document = {
            "name": uploaded_file.filename,
            "trainee_id": "TR001",
            "documents": inferred_documents,
        }

        result = verification_agent.run_agent_loop(document)
        response = {
            "filename": filename,
            "file_type": file_extension,
            "documents": inferred_documents,
            **result,
        }
        status_code = 200
        if response.get("status") == "pending":
            status_code = 202
        elif response.get("status") == "rejected":
            status_code = 400
        return jsonify(response), status_code

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)