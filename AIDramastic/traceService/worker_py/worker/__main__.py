"""允许 python -m worker 启动。"""

from worker.main import main

if __name__ == "__main__":
    raise SystemExit(main())
