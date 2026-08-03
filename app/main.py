from flask import Flask, jsonify, request
from app.config import Config
from app.agents.verification_agent import VerificationAgent


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    verification_agent = VerificationAgent()

    @app.route('/verify', methods=['POST'])
    def verify_document():
        document = request.get_json(silent=True) or {}
        result = verification_agent.verify_document(document)
        return jsonify(result)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)