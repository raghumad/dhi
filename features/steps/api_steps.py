import json
import urllib.request
from behave import given, when, then

@given('the API is running at "{url}"')
def step_impl(context, url):
    context.api_url = url
    # Verify health
    try:
        with urllib.request.urlopen(f"{url}/health") as response:
            assert response.status == 200
    except Exception as e:
        assert False, f"API check failed: {e}. Is Uvicorn running?"

@when('I send a POST request to "{endpoint}" with payload:')
def step_impl(context, endpoint):
    url = f"{context.api_url}{endpoint}"
    # Parse to ensure valid JSON, then dump to string, then encode to bytes
    payload_dict = json.loads(context.text)
    data = json.dumps(payload_dict).encode('utf-8')
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            context.response_code = response.status
            context.response_body = json.load(response)
    except urllib.error.HTTPError as e:
        context.response_code = e.code
        context.response_body = json.load(e)
    except Exception as e:
        assert False, f"Request failed: {e}"

@then('the response status code should be {status_code:d}')
def step_impl(context, status_code):
    assert context.response_code == status_code, \
        f"Expected {status_code}, got {context.response_code}. Body: {context.response_body}"

@then('the response should contain "{key}"')
def step_impl(context, key):
    assert key in context.response_body, \
        f"Key '{key}' not found in response. Body: {context.response_body}"
