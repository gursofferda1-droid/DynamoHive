from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading
import time

from backend.orchestrator import Orchestrator
from backend.metrics_engine import get_system_metrics


# -------------------------
# APP
# -------------------------

app = FastAPI()

# -------------------------
# GLOBAL ORCHESTRATOR
# -------------------------

orchestrator = Orchestrator()

LATEST_DATA = []


# -------------------------
# BACKGROUND LOOP
# -------------------------

def run_loop():

    global LATEST_DATA

    print("🚀 FORCE START")
    print("🔥 ORCHESTRATOR READY")

    while True:
        try:
            print("🔁 LOOP TICK")

            data = orchestrator.run_cycle()

            if isinstance(data, list):
                LATEST_DATA = data

        except Exception as e:
            print("❌ LOOP ERROR:", e)

        time.sleep(20)


# -------------------------
# STARTUP
# -------------------------

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()


# -------------------------
# ROOT
# -------------------------

@app.get("/")
def root():
    return {
        "status": "DynamoHive running",
        "items": len(LATEST_DATA)
    }


# -------------------------
# INTEL FEED
# -------------------------

@app.get("/intel")
def get_intel():

    if not LATEST_DATA:
        return JSONResponse({
            "status": "warming up",
            "data": []
        })

    return JSONResponse(LATEST_DATA)


# -------------------------
# METRICS
# -------------------------

@app.get("/metrics")
def metrics():
    return JSONResponse(get_system_metrics())


# -------------------------
# HEALTH
# -------------------------

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
