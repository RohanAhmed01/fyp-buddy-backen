import os
import re
import subprocess
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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


# Root route taake browser ya Vercel par kholnay se 404 na aaye
@app.get("/")
def read_root():
    return {
        "status": "success",
        "message": "FYP Buddy API is live and running smoothly!"
    }


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
