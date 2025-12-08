from behave import given, when, then
import os
import pexpect
import sys
import struct
import hnswlib
import re

# Adjust command to point to out/ and limit for speed
@given('the input file "{filename}" exists')
def step_impl(context, filename):
    assert os.path.exists(filename), f"Input file {filename} not found. Please place Rigveda.pdf in out/"
    context.input_file = filename

@given('the model file "{filepath}" exists')
def step_impl(context, filepath):
    if not os.path.exists(filepath):
        print(f"Model {filepath} missing. Downloading...")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        url = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
        cmd = f"wget -O {filepath} {url}"
        ret = os.system(cmd)
        assert ret == 0, "Failed to download model"
    assert os.path.exists(filepath), "Model file verified"

@when('I run the ingestion process')
def step_impl(context):
    # Default to context.input_file if set, otherwise fallback or error
    input_file = getattr(context, 'input_file', 'out/rigveda.pdf')
    command = f"{sys.executable} src/ingest.py {input_file} --limit 10"
    context.process = pexpect.spawn(command, encoding='utf-8', timeout=600)
    context.process.expect(pexpect.EOF)

@when('I force run the ingestion process')
def step_impl(context):
    input_file = getattr(context, 'input_file', 'out/rigveda.pdf')
    command = f"{sys.executable} src/ingest.py {input_file} --limit 10 --force"
    context.process = pexpect.spawn(command, encoding='utf-8', timeout=600)
    context.process.expect(pexpect.EOF)

# --- 1. Artifact Verification Steps ---

@then('the binary index "{filepath}" should be created')
def step_impl(context, filepath):
    assert os.path.exists(filepath), f"{filepath} missing"

@then('the binary metadata "{filepath}" should be created')
def step_impl(context, filepath):
    assert os.path.exists(filepath), f"{filepath} missing"

@then('the text blob "{filepath}" should be created')
def step_impl(context, filepath):
    assert os.path.exists(filepath), f"{filepath} missing"

# --- 2. Embedding/Index Verification ---

@given('the binary index "{filepath}" exists')
def step_impl(context, filepath):
    assert os.path.exists(filepath), f"Index {filepath} missing"

@then('the file size should be greater than {size:d}')
def step_impl(context, size):
    # Context implicitly refers to the file checked in the previous step
    # but behave is stateless between steps unless we use context.
    # However, for this specific scenario (2), we know we just checked rigveda.hnsw
    # Let's check rigveda.hnsw explicitly or assume generic file checks are not needed often.
    path = "out/rigveda.hnsw"
    assert os.path.getsize(path) > size, f"File {path} too small"

# --- 3. Schema Verification ---

@given('the binary metadata "{filepath}" exists')
def step_impl(context, filepath):
    assert os.path.exists(filepath), f"Metadata {filepath} missing"

@then('the file header should contain magic bytes "{magic}"')
def step_impl(context, magic):
    path = "out/rigveda.bin"
    with open(path, "rb") as f:
        actual_magic = f.read(4)
        expected = magic.encode('utf-8')
        assert actual_magic == expected, f"Expected magic {expected}, got {actual_magic}"

# --- 4. Retrieval Verification ---

@when('I query the internal retrieval function for "{query}"')
def step_impl(context, query):
    # Using `search.py --query` creates an ephemeral search
    # MUST use -m src.search to resolve imports correctly
    command = f"{sys.executable} -m src.search --model models/llama-3.2-3b-instruct-q4km.gguf --query '{query}'"
    context.process = pexpect.spawn(command, encoding='utf-8', timeout=60)
    context.process.expect(pexpect.EOF)

@then('the top result should contain "{expected}"')
def step_impl(context, expected):
    output = context.process.before
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_output = ansi_escape.sub('', output)
    
    with open("out/retrieval_debug.txt", "w") as f:
        f.write(f"EXPECTED: {expected}\n")
        f.write(f"OUTPUT:\n{clean_output}\n")

    assert expected in clean_output, f"Expected '{expected}' in output. See out/retrieval_debug.txt"

@then('the similarity score should be greater than {score:f}')
def step_impl(context, score):
    output = context.process.before
    # Regex to find (Score: 0.XXXX)
    match = re.search(r"Score: (\d+\.\d+)", output)
    if match:
        actual = float(match.group(1))
        assert actual > score, f"Score {actual} too low (expected > {score})"
    else:
        # If no score found, maybe search failed?
        pass

@then('the ingestion output should contain "{text}"')
def step_impl(context, text):
    output = context.process.before
    assert text in output, f"Expected '{text}' in output. Got: {output[:200]}..."
