import os
import time
import uuid
from urllib import request, error
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ============================================================================
# SECURITY CONFIGURATION - SET IN VERCEL DASHBOARD
# ============================================================================
# Only ONE exact key is accepted: "kaiiddo-jkjbhu"
# Set "MAGICSTUDIO_API_KEY" environment variable in Vercel: Settings > Environment Variables
# ============================================================================
API_KEY = "kaiidoo-4fX9mL2nQpR8tUv7wAyBzC3dE5gHjK6l"

# Constants for MagicStudio API
BOUNDARY = "----WebKitFormBoundarycvwCppQ0clsuCAAN"

# ============================================================================
# CORE IMAGE GENERATION LOGIC (Ported from your script)
# ============================================================================
def build_body(prompt: str) -> bytes:
    """Build multipart/form-data body exactly like the browser."""
    anon_id = str(uuid.uuid4())
    client_id = uuid.uuid4().hex + uuid.uuid4().hex
    ts = str(time.time())

    def part(name: str, value: str) -> str:
        return f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'

    body = (
        part("prompt", prompt)
        + part("output_format", "bytes")
        + part("user_profile_id", "null")
        + part("anonymous_user_id", anon_id)
        + part("request_timestamp", ts)
        + part("user_is_subscribed", "false")
        + part("client_id", client_id)
        + f"--{BOUNDARY}--\r\n"
    )
    return body.encode("utf-8")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": f"multipart/form-data; boundary={BOUNDARY}",
    "origin": "https://magicstudio.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://magicstudio.com/ai-art-generator/",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}

def generate_image(prompt: str) -> bytes:
    """Call MagicStudio API and return raw JPEG bytes."""
    url = "https://ai-api.magicstudio.com/api/ai-art-generator"
    data = build_body(prompt)

    req = request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with request.urlopen(req) as resp:
            content_type = resp.headers.get("content-type", "")
            if "image/jpeg" in content_type or "image/jpg" in content_type:
                return resp.read()
            else:
                error_body = resp.read().decode() if hasattr(resp, 'read') else "Unknown error"
                raise RuntimeError(f"API returned: {content_type} - {error_body}")
    except error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, 'read') else str(e)
        raise RuntimeError(f"HTTP {e.code}: {error_body}") from None
    except Exception as e:
        raise RuntimeError(f"Request failed: {str(e)}") from None

# ============================================================================
# API AUTHENTICATION & PROMPT EXTRACTION
# ============================================================================
def extract_api_key() -> str:
    """Extract API key from request (header, query, or form)."""
    # Check Authorization header (supports "Bearer key" and "key" formats)
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header:
        if auth_header.lower().startswith('bearer '):
            return auth_header[7:].strip()
        return auth_header
    
    # Check query parameter (GET)
    api_key = request.args.get('api_key', '').strip()
    if api_key:
        return api_key
    
    # Check form parameter (POST)
    return request.form.get('api_key', '').strip()

def extract_prompt() -> str:
    """Extract prompt from request (GET, POST form, or POST JSON)."""
    if request.method == 'GET':
        return request.args.get('prompt', '').strip()
    
    if request.method == 'POST':
        # Try form data first
        prompt = request.form.get('prompt', '').strip()
        if prompt:
            return prompt
        
        # Try JSON body
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data and isinstance(json_data, dict):
                    return json_data.get('prompt', '').strip()
            except:
                pass
    
    return ''

# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.route('/api/generate', methods=['GET', 'POST'])
def generate_api():
    """Main API endpoint - returns image directly on success."""
    
    # BLOCK REQUESTS WITHOUT VALID API KEY
    api_key = extract_api_key()
    if api_key != API_KEY:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Invalid or missing API key. The key must be exactly: kaiiddo-jkjbhu',
            'provided_key': api_key[:5] + '...' if api_key else 'none',
            'authentication_methods': [
                'Authorization: kaiiddo-jkjbhu',
                'Authorization: Bearer kaiiddo-jkjbhu',
                '?api_key=kaiiddo-jkjbhu (GET)',
                'api_key=kaiiddo-jkjbhu (POST)'
            ]
        }), 401

    # Extract and validate prompt
    prompt = extract_prompt()
    if not prompt:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Missing required parameter: prompt',
            'example': 'prompt=golden cat'
        }), 400

    # Generate and return image
    try:
        jpeg_bytes = generate_image(prompt)
        
        # Return DIRECT IMAGE RESPONSE (best for API)
        return Response(
            jpeg_bytes,
            mimetype='image/jpeg',
            headers={
                'Content-Disposition': 'inline; filename="generated_image.jpg"',
                'X-Prompt': prompt,
                'X-API-Status': 'success'
            }
        )
        
    except RuntimeError as e:
        return jsonify({
            'error': 'API Generation Failed',
            'message': str(e),
            'prompt': prompt
        }), 502
    except Exception as e:
        return jsonify({
            'error': 'Internal Error',
            'message': 'An unexpected error occurred.',
            'detail': str(e) if app.debug else 'Contact administrator.'
        }), 500

@app.route('/')
def index():
    """API documentation."""
    return jsonify({
        'name': 'MagicStudio AI Art API',
        'version': '1.0.0',
        'authentication': {
            'required': True,
            'only_accepted_key': 'kaiiddo-jkjbhu',
            'methods': [
                'Header: Authorization: kaiiddo-jkjbhu',
                'Header: Authorization: Bearer kaiiddo-jkjbhu',
                'GET Param: ?api_key=kaiiddo-jkjbhu',
                'POST Param: api_key=kaiiddo-jkjbhu'
            ]
        },
        'endpoint': {
            'path': '/api/generate',
            'methods': ['GET', 'POST'],
            'parameters': {
                'prompt': 'Text description (required)'
            }
        },
        'examples': {
            'curl': 'curl -H "Authorization: kaiiddo-jkjbhu" "https://your-domain/api/generate?prompt=golden cat" --output image.jpg',
            'postman': 'Set Header: Authorization = kaiiddo-jkjbhu, Body: form-data with prompt field'
        }
    })

# ============================================================================
# VERCEL SERVERLESS ENTRY POINT
# ============================================================================
# Vercel automatically detects the Flask app and creates a serverless function
# No additional handler code needed when using this structure

# Local development
if __name__ == '__main__':
    print(f"Starting server with API_KEY: {API_KEY[:5]}...")
    print("Test: http://localhost:5000/api/generate?api_key=kaiiddo-jkjbhu&prompt=hello")
    app.run(debug=True, host='0.0.0.0', port=5000)
