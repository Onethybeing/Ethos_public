import subprocess
import time
import sys
import os
import signal
import threading

def stream_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        if line:
            print(f"[{prefix}] {line.strip()}")

def run_system():
    print("🚀 Starting Narrative Memory System...")
    
    # Start Backend
    print("📦 Starting Backend (FastAPI on port 8001)...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Start Frontend
    print("🎨 Starting Frontend (Vite)...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=os.path.join(os.getcwd(), "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Stream logs in threads
    t1 = threading.Thread(target=stream_output, args=(backend.stdout, "BACKEND"), daemon=True)
    t2 = threading.Thread(target=stream_output, args=(frontend.stdout, "FRONTEND"), daemon=True)
    t1.start()
    t2.start()
    
    print("\n✅ System Running!")
    print("   👉 Frontend: http://localhost:5173")
    print("   👉 API Docs: http://localhost:8001/docs")
    print("\nPress Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
            # Check if processes are alive
            if backend.poll() is not None:
                print("❌ Backend failed!")
                break
            if frontend.poll() is not None:
                print("❌ Frontend failed!")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)

if __name__ == "__main__":
    run_system()
