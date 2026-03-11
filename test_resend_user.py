import resend, os
from dotenv import load_dotenv
load_dotenv()

resend.api_key = os.getenv('RESEND_API_KEY', '')
print(f'Resend key present: {bool(resend.api_key)}')
print(f'Resend key prefix: {resend.api_key[:8] if resend.api_key else None}')

try:
    print("Attempting to send email...")
    result = resend.Emails.send({
        'from': 'onboarding@resend.dev',
        'to': 'bathmarajahsoobothanan@gmail.com',
        'subject': '416Homes Agent — Live Test',
        'html': '<h1>Resend is working</h1><p>Agent can send real emails.</p>'
    })
    print(f'Send result: {result}')
    # In some versions of resend library, it might be an object, not a dict
    if hasattr(result, 'get'):
        print(f'Email ID: {result.get("id")}')
    elif hasattr(result, 'id'):
        print(f'Email ID: {result.id}')
    else:
        print(f'Result: {result}')
except Exception as e:
    print(f'Send failed: {e}')
