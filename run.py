import webbrowser
import threading
import time
import uvicorn

def open_browser():
    time.sleep(1.2)
    print("Opening web app dashboard in browser: http://127.0.0.1:8000/ ...")
    webbrowser.open("http://127.0.0.1:8000/")

if __name__ == "__main__":
    print("=================================================================")
    print(" Starting Inventory Reorder Prediction Web App (FastAPI + UI) ")
    print("=================================================================")
    print("Web UI Dashboard : http://127.0.0.1:8000/")
    print("Swagger API Docs : http://127.0.0.1:8000/docs")
    print("=================================================================")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
