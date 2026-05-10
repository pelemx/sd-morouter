import os
import sys
import io
import contextlib
import subprocess
import traceback
import shutil
import gradio as gr
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from modules import script_callbacks

API_KEY = "xshpdx298RGPCUU-cudahost"

def verify_auth(request: Request):
    key = request.headers.get("X-runpx-Key")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")
def check_and_launch_backup():
    """Checks if the backup API is on 6060; launches it if not."""
    port = 6060
    script_path = "/u01/vt_media/stable-diffusion-webui/backup_api.py"
    log_path = "/u01/vt_media/stable-diffusion-webui/backup_api.log"
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        is_running = s.connect_ex(('127.0.0.1', port)) == 0
    
    if not is_running:
        print(f"🚀 Launching Standalone Backup API on port {port}...")
        # Use shell=True to handle the background & and redirection logic
        cmd = f"nohup python3 {script_path} > {log_path} 2>&1 &"
        subprocess.Popen(cmd, shell=True)
    else:
        print(f"✅ Standalone Backup API already active on port {port}.")
def runpd_compute_api(demo: gr.Blocks, app: FastAPI):
    check_and_launch_backup()
    @app.post("/runpd/v1/pip")
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

    @app.post("/runpd/v1/compute")
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

    @app.post("/runpd/v1/upload")
    async def upload_file(request: Request, file: UploadFile = File(...), target_path: str = Form(...)):
        verify_auth(request)
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return {"status": "Success", "saved_to": target_path}
        except Exception as e:
            return {"status": "Error", "details": str(e)}

    @app.get("/runpd/v1/download")
    async def download_file(request: Request, file_path: str):
        verify_auth(request)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on HOSTRICH")
        return FileResponse(path=file_path, filename=os.path.basename(file_path))

script_callbacks.on_app_started(runpd_compute_api)
