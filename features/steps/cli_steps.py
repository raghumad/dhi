import pexpect
from behave import given, when, then
import sys

# Command to run the application. 
# This is currently Python, but can be switched to "./build/dhi" later.
import time

APP_COMMAND = f"{sys.executable} src/search.py --model models/model.gguf"

@given('the search engine is running')
def step_impl(context):
    # Initialize scenario metrics dict
    context.scenario_perf = {}
    
    context.process = pexpect.spawn(APP_COMMAND, encoding='utf-8', timeout=30)
    context.process.expect("Query >")

@when('I search for "{query}"')
def step_impl(context, query):
    context.query_start_time = time.time()
    context.process.sendline(query)

@then('the output should contain "{expected_text}"')
def step_impl(context, expected_text):
    index = context.process.expect([expected_text, pexpect.EOF, pexpect.TIMEOUT])
    
    # Calculate Latency
    latency = time.time() - context.query_start_time
    context.scenario_perf['latency_sec'] = latency
    
    if index != 0:
        print(f"\nCaptured Output:\n{context.process.before}")
        assert False, f"Expected '{expected_text}' not found in output."

@then('I can exit the application')
def step_impl(context):
    # Wait for the prompt to return after the previous answer
    context.process.expect("Query >")
    
    # Send exit
    context.process.sendline("exit")
    
    # Expect clean exit
    context.process.expect(pexpect.EOF)
    context.process.close()
    assert context.process.exitstatus == 0 or context.process.exitstatus is None
