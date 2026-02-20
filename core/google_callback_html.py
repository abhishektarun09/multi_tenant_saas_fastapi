def google_callback_html(access_token, base_url):

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Authentication Successful</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {{
            margin: 0;
            background-color: #f4f6f9;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .wrapper {{
            max-width: 700px;
            margin: 80px auto;
            padding: 0 20px;
        }}

        .card {{
            background: #ffffff;
            padding: 32px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}

        h2 {{
            margin-top: 0;
            color: #111827;
        }}

        p {{
            color: #374151;
            font-size: 14px;
            line-height: 1.6;
        }}

        .info-box {{
            margin-top: 16px;
            padding: 14px;
            background: #f0f7ff;
            border: 1px solid #c7defa;
            border-radius: 6px;
            font-size: 13px;
            color: #1e3a8a;
        }}

        textarea {{
            width: 100%;
            margin-top: 12px;
            padding: 10px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 13px;
            font-family: monospace;
            background: #f9fafb;
            resize: none;
        }}

        .btn {{
            display: inline-block;
            margin-top: 16px;
            padding: 10px 16px;
            background: #2563eb;
            color: #ffffff;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            border: none;
            cursor: pointer;
        }}

        .btn-secondary {{
            background: #6b7280;
            margin-left: 8px;
        }}

        .note {{
            margin-top: 16px;
            font-size: 12px;
            color: #b91c1c;
        }}

        .footer {{
            margin-top: 24px;
            font-size: 12px;
            color: #6b7280;
        }}
    </style>

    <script>
    function copyToken() {{
        const textarea = document.getElementById("token");
        textarea.select();
        textarea.setSelectionRange(0, 99999);
        document.execCommand("copy");
        alert("Access token copied to clipboard");
    }}
    </script>

    </head>
    <body>

    <div class="wrapper">
        <div class="card">

            <h2>Authentication Successful</h2>

            <p>
                Your identity has been verified and an access token has been issued.
                This token contains your authenticated permissions and can be used to
                authorize requests to the API.
            </p>

            <div class="info-box">
                <strong>Why am I seeing this page?</strong><br>
                This project focuses on backend API functionality and does not include
                a frontend application to handle OAuth redirects. In a production
                environment, you would be redirected back to a client application that
                securely stores and uses this token. This page is provided to
                demonstrate the authentication flow for testing purposes.
                <br><br>
                <strong>Next step:</strong> Open the API documentation, click
                <em>Authorize</em>, and paste the access token below to authenticate
                your requests.
            </div>

            <p><strong>Access Token</strong></p>

            <textarea id="token" rows="6" readonly>{access_token}</textarea>

            <br>

            <button class="btn" onclick="copyToken()">Copy Token</button>
            <a class="btn btn-secondary" href="{base_url}/docs">
                Go to API Docs
            </a>

            <p class="note">
                This token grants access to protected organizational resources.
                Keep it confidential and do not share it publicly.
            </p>

            <div class="footer">
                Multi-Tenant Project Management API • RBAC Enabled • Demo Environment
            </div>

        </div>
    </div>

    </body>
    </html>
    """

    return html