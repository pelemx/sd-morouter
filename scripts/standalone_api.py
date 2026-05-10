import os
import sys
import io
import contextlib
import subprocess
import traceback
import shutil
import uvicorn
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from threading import Thread

API_KEY = "xshpdx298RGPCUU-cudahost"

def verify_auth(request: Request):
    key = request.headers.get("X-runpx-Key")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")

# Create standalone FastAPI app
standalone_app = FastAPI(title="RUNPD Standalone API")

@standalone_app.post("/runpd/v1/pip")
async def install_package(request: Request):
    verify_auth(request)
    payload = await request.json()
    packages = payload.get("packages", [])
    results = {}
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            results[pkg] = "Success"
        except Exception as e:
            results[pkg] = f"Failed: {str(e)}"
    return {"status": "pip execution complete", "details": results}

@standalone_app.post("/runpd/v1/compute")
async def execute_compute_job(request: Request):
    verify_auth(request)
    payload = await request.json()
    code_string = payload.get("code", "")
    stdout_buffer = io.StringIO()
    error_output = ""
    
    with contextlib.redirect_stdout(stdout_buffer):
        try:
            exec(code_string, globals())
            status = "Completed"
        except Exception:
            error_output = traceback.format_exc()
            status = "Error"
            
    return {"status": status, "stdout": stdout_buffer.getvalue(), "error": error_output}

@standalone_app.post("/runpd/v1/upload")
async def upload_file(request: Request, file: UploadFile = File(...), target_path: str = Form(...)):
    verify_auth(request)
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "Success", "saved_to": target_path}
    except Exception as e:
        return {"status": "Error", "details": str(e)}

@standalone_app.get("/runpd/v1/download")
async def download_file(request: Request, file_path: str):
    verify_auth(request)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on HOSTRICH")
    return FileResponse(path=file_path, filename=os.path.basename(file_path))

@standalone_app.get("/health")
async def health_check():
    return {"status": "alive", "port": 6060, "service": "RUNPD Standalone"}

def run_standalone_server():
    """Run standalone server on port 6060"""
    uvicorn.run(standalone_app, host="0.0.0.0", port=6060, log_level="info")

def start_backup_server():
    """Start server in background thread"""
    thread = Thread(target=run_standalone_server, daemon=True)
    thread.start()
    print("🚀 RUNPD Standalone API started on http://0.0.0.0:6060")

if __name__ == "__main__":
    # For testing standalone
    run_standalone_server()
