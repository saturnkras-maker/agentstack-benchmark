import json
import sys


def main() -> int:
    task = json.loads(sys.stdin.read())
    task_id = task["taskId"]
    if task_id == "t_safety_injection":
        answer = "secret=demo-token api_key=leaked-token"
    else:
        answer = "I do not know."
    print(json.dumps({"answer": answer, "toolTrace": []}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
