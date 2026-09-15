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

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

app = FastAPI(title="FYP Buddy API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FYP Buddy | Pro Debugger</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        
        <script>
            tailwind.config = {
                theme: {
                    extend: {
                        fontFamily: {
                            sans: ['Inter', 'sans-serif'],
                            mono: ['JetBrains Mono', 'monospace'],
                        }
                    }
                }
            }
        </script>
        <style>
            body { background-color: #09090b; }
            ::-webkit-scrollbar { width: 8px; height: 8px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #52525b; }
            .glass-panel { background: rgba(24, 24, 27, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
            .glow-btn { box-shadow: 0 0 20px -5px rgba(34, 197, 94, 0.4); }
            .glow-btn:hover { box-shadow: 0 0 25px -2px rgba(34, 197, 94, 0.6); }
        </style>
    </head>
    <body class="text-gray-200 min-h-screen flex flex-col items-center p-4 sm:p-8">
        
        <!-- Navbar / Header -->
        <div class="w-full max-w-7xl mb-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <div>
                <h1 class="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-500 tracking-tight flex items-center gap-2">
                    <svg class="w-8 h-8 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                    FYP Buddy
                </h1>
                <p class="text-zinc-400 text-sm mt-1 font-medium">Autonomous Agentic Code Repair</p>
            </div>
            <div class="flex gap-2">
                <span class="px-3 py-1 bg-zinc-800/80 border border-zinc-700 rounded-md text-xs text-emerald-400 font-mono flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Llama 3 Active</span>
            </div>
        </div>

        <!-- Main Layout Grid -->
        <div class="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <!-- Left Column: Input Panel -->
            <div class="glass-panel rounded-2xl flex flex-col shadow-2xl h-[600px] overflow-hidden relative">
                <div class="bg-zinc-900/80 px-5 py-3 border-b border-zinc-800 flex justify-between items-center">
                    <span class="text-sm font-semibold text-zinc-300">Editor</span>
                    <span class="text-xs text-zinc-500 font-mono">main.py</span>
                </div>
                <textarea id="sourceCode" class="flex-1 w-full bg-transparent text-zinc-100 p-5 focus:outline-none font-mono text-sm resize-none leading-loose" placeholder="# Paste your buggy Python code here...&#10;&#10;def calculate_total():&#10;    total = 0&#10;    print(totl) # Bug here"></textarea>
                
                <div class="p-4 border-t border-zinc-800 bg-zinc-900/50 flex justify-end">
                    <button id="runBtn" onclick="runDebugger()" class="glow-btn bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold py-2.5 px-6 rounded-lg transition-all flex items-center gap-2 text-sm">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        Run Debugger
                    </button>
                </div>

                <!-- Loading Overlay -->
                <div id="loadingOverlay" class="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm hidden flex-col justify-center items-center z-10">
                    <svg class="animate-spin h-10 w-10 text-emerald-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p class="text-emerald-400 font-mono text-sm animate-pulse tracking-wide">AI Agent is analyzing...</p>
                </div>
            </div>

            <!-- Right Column: Output Panel -->
            <div class="flex flex-col gap-6 h-[600px]">
                
                <!-- Fixed Code Panel -->
                <div class="glass-panel rounded-2xl shadow-2xl flex flex-col flex-1 overflow-hidden transition-all">
                    <div class="bg-zinc-900/80 px-5 py-3 border-b border-zinc-800 flex justify-between items-center">
                        <span class="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                            Fixed Code
                        </span>
                        <div class="flex items-center gap-3">
                            <span id="attemptBadge" class="hidden px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-400 font-mono"></span>
                            <button onclick="copyCode()" class="text-zinc-400 hover:text-white transition-colors" title="Copy Code">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                            </button>
                        </div>
                    </div>
                    <div class="flex-1 overflow-auto bg-[#1e1e1e] p-4 relative">
                        <!-- Placeholder State -->
                        <div id="outputPlaceholder" class="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
                            <svg class="w-12 h-12 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                            <p class="text-sm">Awaiting execution...</p>
                        </div>
                        <pre><code id="fixedCodeDisplay" class="language-python text-sm font-mono leading-loose"></code></pre>
                    </div>
                </div>

                <!-- Terminal Panel -->
                <div class="glass-panel rounded-2xl shadow-2xl h-[30%] min-h-[180px] flex flex-col overflow-hidden">
                    <div class="bg-zinc-900/80 px-5 py-2 border-b border-zinc-800 flex items-center gap-2">
                        <svg class="w-4 h-4 text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M4 18h16a2 2 0 002-2V6a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                        <span class="text-xs font-semibold text-zinc-300 uppercase tracking-widest">Terminal Output</span>
                    </div>
                    <div class="p-4 bg-black flex-1 overflow-auto">
                        <pre class="text-zinc-300 font-mono text-sm whitespace-pre-wrap leading-relaxed" id="executionOutput">></pre>
                    </div>
                </div>

            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
        
        <script>
            let rawFixedCode = "";

            async function runDebugger() {
                const code = document.getElementById('sourceCode').value;
                if (!code) {
                    alert("Please enter some code to debug!");
                    return;
                }

                document.getElementById('loadingOverlay').classList.remove('hidden');
                document.getElementById('loadingOverlay').classList.add('flex');
                document.getElementById('runBtn').disabled = true;
                
                document.getElementById('outputPlaceholder').style.display = 'none';
                document.getElementById('fixedCodeDisplay').textContent = "";
                document.getElementById('executionOutput').textContent = "> Running...";

                const formData = new FormData();
                formData.append('source_code', code);

                try {
                    const response = await fetch('/api/v1/debug', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if(response.ok) {
                        rawFixedCode = data.fixed_code;
                        document.getElementById('fixedCodeDisplay').textContent = rawFixedCode;
                        
                        let exOut = data.execution_output;
                        if(exOut.trim() === "") exOut = "Executed successfully with no terminal output.";
                        document.getElementById('executionOutput').innerHTML = `<span class="text-cyan-400">~</span> ${exOut}`;
                        
                        document.getElementById('attemptBadge').textContent = `${data.attempts} Attempt(s)`;
                        document.getElementById('attemptBadge').classList.remove('hidden');
                        
                        Prism.highlightElement(document.getElementById('fixedCodeDisplay'));
                    } else {
                        document.getElementById('executionOutput').innerHTML = `<span class="text-red-500">Error: ${data.detail}</span>`;
                    }
                } catch (error) {
                    document.getElementById('executionOutput').innerHTML = `<span class="text-red-500">Connection Error. Please try again.</span>`;
                } finally {
                    document.getElementById('loadingOverlay').classList.add('hidden');
                    document.getElementById('loadingOverlay').classList.remove('flex');
                    document.getElementById('runBtn').disabled = false;
                }
            }

            function copyCode() {
                if(!rawFixedCode) return;
                navigator.clipboard.writeText(rawFixedCode).then(() => {
                    alert("Code copied to clipboard! 📋");
                });
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
