# LLM Integration Guide

This guide explains how to run the trainee document verification app, connect it to an LLM, and test the flow locally.

## 1. Project Overview

The app is a small Flask service with three main pieces:

- VerificationAgent: validates the incoming payload and prepares the request.
- DocumentVerifier: performs a basic sanity check before sending data to the LLM.
- LLMClient: sends the document information to an OpenAI-compatible endpoint.

## 2. Prerequisites

Before you start, make sure you have:

- Python 3.10 or newer
- A terminal with PowerShell
- An API key for an OpenAI-compatible provider

## 3. Create and Activate a Virtual Environment

From the project folder, run:

```powershell
cd "c:\Users\RSMDH-LPT-GEN-15\Downloads\Trainee Document Verification\trainee-document-verification-agent"
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 4. Install Dependencies

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If Flask still shows compatibility issues, install the matching versions:

```powershell
.\.venv\Scripts\python.exe -m pip install "Flask==2.0.1" "Werkzeug==2.0.2" "Jinja2==3.0.3" "itsdangerous==2.0.1"
```

## 5. Configure the Environment File

Open the file [.env](.env) and set these values:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

The app also reads these fallback names:

```env
API_KEY=your_api_key_here
API_URL=https://api.openai.com/v1
```

## 6. Run the App

Start the Flask server with:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe app\main.py
```

The app will run at:

```text
http://127.0.0.1:5000/
```

## 7. Test the API

The app exposes the verification endpoint at:

```text
http://127.0.0.1:5000/verify
```

### Option A: Use the built-in test page

Open:

```text
http://127.0.0.1:5000/
```

Click the button to send a sample request.

### Option B: Use the Python test script

Run:

```powershell
.\.venv\Scripts\python.exe test_request.py
```

### Option C: Send a manual request with curl

```powershell
curl -X POST http://127.0.0.1:5000/verify -H "Content-Type: application/json" -d "{\"name\":\"Jane Doe\",\"id\":\"123456\",\"documents\":[\"id_card\"],\"use_fake_data\":true}"
```

## 8. Example Request Payload

```json
{
  "name": "Jane Doe",
  "id": "123456",
  "documents": ["id_card"],
  "use_fake_data": true
}
```

## 9. Fake Data Mode

If you want to test the workflow without calling a real LLM, set the field `use_fake_data` to `true`.

In that case, the app returns a demo response and does not require the API call to succeed.

## 10. How the LLM Integration Works

1. The Flask route receives a JSON body.
2. The VerificationAgent validates the document payload.
3. The DocumentVerifier checks for obvious fake values.
4. The LLMClient builds a prompt and sends it to the OpenAI-compatible endpoint.
5. The response is parsed and returned as JSON.

## 11. Troubleshooting

### Import errors

If Python cannot find the app package, run:

```powershell
$env:PYTHONPATH="."
```

### Flask/Werkzeug errors

If you see import errors from Flask, reinstall the compatible versions:

```powershell
.\.venv\Scripts\python.exe -m pip install "Flask==2.0.1" "Werkzeug==2.0.2" "Jinja2==3.0.3" "itsdangerous==2.0.1"
```

### 404 or 405 errors

- Use the correct path: `/verify`
- Make sure the request is a POST request
- Make sure the app is still running

## 12. Next Steps

If you want to improve the LLM behavior further, you can:

- change the model in `.env`
- switch to a different OpenAI-compatible endpoint
- add richer prompts for document validation
- add a frontend form for manual document entry
