import queue
import random
import subprocess
import threading
import time
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
PYTHON_EXE = WORKDIR / ".venv" / "Scripts" / "python.exe"
TARGET_SCRIPT = WORKDIR / "auto_register.py"
STOP_COMMANDS = {"stop", "quit", "exit", "停止"}
SUCCESS_DELAY_MIN_SECONDS = 2.0
SUCCESS_DELAY_MAX_SECONDS = 5.0
FAILURE_DELAY_MIN_SECONDS = 8.0
FAILURE_DELAY_MAX_SECONDS = 15.0


def start_input_listener(stop_queue: "queue.Queue[str]") -> None:
    def _reader() -> None:
        while True:
            try:
                user_input = input().strip().lower()
            except EOFError:
                stop_queue.put("eof")
                return

            if user_input in STOP_COMMANDS:
                stop_queue.put(user_input)
                return

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()


def main() -> None:
    if not PYTHON_EXE.exists():
        raise FileNotFoundError(f"Python executable not found: {PYTHON_EXE}")
    if not TARGET_SCRIPT.exists():
        raise FileNotFoundError(f"Target script not found: {TARGET_SCRIPT}")

    stop_queue: queue.Queue[str] = queue.Queue()
    start_input_listener(stop_queue)
    stop_requested = False
    stop_command = ""

    print("循环执行已启动。输入 stop、quit、exit 或 停止，将在当前这轮执行完成后停止。")

    run_count = 0
    while True:
        if stop_requested:
            print(f"已按指令停止: {stop_command}")
            break

        run_count += 1
        print(f"\n第 {run_count} 次执行开始: {TARGET_SCRIPT.name}")
        result = subprocess.run(
            [str(PYTHON_EXE), str(TARGET_SCRIPT)],
            cwd=str(WORKDIR),
            check=False,
        )

        if result.returncode != 0:
            print(f"脚本执行失败，返回码: {result.returncode}")
            delay_seconds = random.uniform(
                FAILURE_DELAY_MIN_SECONDS,
                FAILURE_DELAY_MAX_SECONDS,
            )
            print(f"失败退避，等待 {delay_seconds:.1f} 秒后再试。")
        else:
            print("脚本执行完成。")
            delay_seconds = random.uniform(
                SUCCESS_DELAY_MIN_SECONDS,
                SUCCESS_DELAY_MAX_SECONDS,
            )
            print(f"下一轮将在 {delay_seconds:.1f} 秒后开始。")

        while not stop_queue.empty():
            stop_command = stop_queue.get_nowait()
            stop_requested = True

        if stop_requested:
            continue

        time.sleep(delay_seconds)


if __name__ == "__main__":
    main()
