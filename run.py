import os
import sys
import subprocess

def check_and_install_dependencies():
    print("Checking dependencies...")
    try:
        import fastapi
        import uvicorn
        import networkx
        import sklearn
        print("[OK] All dependencies found.")
    except ImportError as e:
        missing_pkg = str(e).split("'")[-2]
        print(f"[WARN] Dependency '{missing_pkg}' is missing. Installing required libraries...")
        # Resolve python path
        python_path = sys.executable
        try:
            subprocess.check_call([python_path, "-m", "pip", "install", "fastapi", "uvicorn", "networkx", "scikit-learn"])
            print("[OK] Dependencies installed successfully.")
        except Exception as install_err:
            print(f"[ERROR] Failed to install dependencies: {install_err}")
            print("Please run: pip install fastapi uvicorn networkx scikit-learn")
            sys.exit(1)

def run():
    check_and_install_dependencies()
    
    print("\n" + "="*50)
    print("  DRISHTI — KSP SCRB INTELLIGENCE PLATFORM")
    print("="*50)
    print("  Starting local server...")
    print("  API Base Address:   http://127.0.0.1:8000/api")
    print("  Web Portal Address: http://127.0.0.1:8000/")
    print("="*50 + "\n")
    
    import uvicorn
    # Start server
    # We use "backend.app:app" string style for uvicorn so reload works
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    run()
