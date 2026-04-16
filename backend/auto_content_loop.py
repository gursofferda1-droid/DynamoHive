import traceback

from backend.orchestrator import Orchestrator


def start():

    print("🚀 FORCE START")
    print("🔥 ORCHESTRATOR READY")

    orch = Orchestrator()

    while True:

        print("🔁 LOOP TICK")

        try:
            orch.run_cycle()

        except Exception as e:
            print("[LOOP ERROR]", e)
            traceback.print_exc()

        time.sleep(15)
