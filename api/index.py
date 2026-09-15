import os
import re
import subprocess
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import uvicorn

# OpenRouter API Key yahan daalein
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

app = FastAPI(title="FYP Buddy API", version="1.1")

# CORS ko sab ke liye open kar diya hai taake production mein masla na ho
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route ab JSON ke bajaye khoobsurat UI (Website) dikhayega
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FYP Buddy - Autonomous Debugger</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    </head>
    <body class="bg-gray-900 text-white font-sans min-h-screen p-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-4xl font-bold text-green-400 mb-2">FYP Buddy</h1>
            <p class="text-gray-400 mb-8">Autonomous Python Self-Healing Debugger</p>

            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-300 mb-2">Paste Buggy Python Code:</label>
                <textarea id="sourceCode" rows="6" class="w-full bg-gray-800 text-gray-100 rounded-lg p-4 focus:ring-2 focus:ring-green-400 focus:outline-none border border-gray-700 font-mono text-sm" placeholder="print(x)"></textarea>
            </div>
            
            <button id="runBtn" onclick="runDebugger()" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-6 rounded-lg transition-colors">
                🚀 Run Autonomous Debugger
            </button>
            
            <p id="loading" class="text-yellow-400 mt-4 hidden animate-pulse">Debugging in progress... Please wait.</p>

            <div id="outputSection" class="mt-10 hidden space-y-6">
                <div>
                    <h2 class="text-xl font-semibold text-green-400 mb-2">Fixed Code:</h2>
                    <div class="bg-gray-800 rounded-lg border border-gray-700">
                        <pre><code id="fixedCodeDisplay" class="language-python text-sm"></code></pre>
                    </div>
                </div>
                <div>
                    <h2 class="text-xl font-semibold text-blue-400 mb-2">Execution Terminal:</h2>
                    <div class="bg-black p-4 rounded-lg border border-gray-700">
                        <pre class="text-yellow-400 font-mono text-sm whitespace-pre-wrap" id="executionOutput"></pre>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
        
        <script>
            async function runDebugger() {
                const code = document.getElementById('sourceCode').value;
                if (!code) {
                    alert("Please enter some code to debug!");
                    return;
                }

                document.getElementById('loading').classList.remove('hidden');
                document.getElementById('outputSection').classList.add('hidden');
                document.getElementById('runBtn').disabled = true;

                const formData = new FormData();
                formData.append('source_code', code);

                try {
                    const response = await fetch('/api/v1/debug', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if(response.ok) {
                        document.getElementById('fixedCodeDisplay').textContent = data.fixed_code;
                        document.getElementById('executionOutput').textContent = data.execution_output;
                        
                        Prism.highlightElement(document.getElementById('fixedCodeDisplay'));
                        document.getElementById('outputSection').classList.remove('hidden');
                    } else {
                        alert("Error: " + data.detail);
                    }
                } catch (error) {
                    alert("Connection Error.");
                } finally {
                    document.getElementById('loading').classList.add('hidden');
                    document.getElementById('runBtn').disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

class DebugResponse(BaseModel):
    fixed_code: str
    explanation: str
    execution_output: str
    status: str
    attempts: int

def extract_python_code(text):
    match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    return match.group(1).strip() if match else text

def run_code_safely(code_string):
    with open("/tmp/temp_exec.py", "w", encoding="utf-8") as f:
        f.write(code_string)

    try:
        result = subprocess.run(
            ["python", "/tmp/temp_exec.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "Execution Error: Timeout (Infinite loop detected)"
    finally:
        if os.path.exists("/tmp/temp_exec.py"):
            os.remove("/tmp/temp_exec.py")

@app.post("/api/v1/debug", response_model=DebugResponse)
async def run_debugger(
        source_code: Optional[str] = Form(None),
        error_message: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None)
):
    try:
        code_to_debug = source_code
        if file:
            content = await file.read()
            code_to_debug = content.decode("utf-8")

        if not code_to_debug:
            raise HTTPException(status_code=400, detail="No source code or file provided.")

        current_code = code_to_debug
        current_error = error_message
        execution_result = ""
        max_attempts = 3
        attempt = 0
        final_explanation = ""

        while attempt < max_attempts:
            attempt += 1

            prompt = (
                "You are FYP Buddy, an autonomous Python self-healing debugger.\n"
                "Analyze the code and any execution errors, then fix it completely.\n"
                "Provide the corrected code inside a python markdown block (```python ... ```), followed by an explanation.\n\n"
                f"Original Code:\n{current_code}\n\n"
                f"Previous Error Context (if any):\n{current_error}"
            )

            # Using OpenRouter's free Llama 3 model
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "system",
                     "content": "You are FYP Buddy, an autonomous self-healing Python code debugger."},
                    {"role": "user", "content": prompt}
                ]
            )

            llm_response = response.choices[0].message.content
            final_explanation = llm_response
            current_code = extract_python_code(llm_response)

            execution_result = run_code_safely(current_code)

            if "Error" not in execution_result and "Exception" not in execution_result and "Traceback" not in execution_result:
                break
            else:
                current_error = execution_result

        status = "success" if "Error" not in execution_result and "Exception" not in execution_result and "Traceback" not in execution_result else "failed"

        return DebugResponse(
            fixed_code=current_code,
            explanation=final_explanation,
            execution_output=execution_result,
            status=status,
            attempts=attempt
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
