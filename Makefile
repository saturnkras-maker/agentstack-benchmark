.PHONY: help test compile doctor local-model-check demo-local demo-local-once demo-local-auto demo-local-auto-once serve

PYTHON ?= python3
PYTHONPATH ?= src
HOST ?= 127.0.0.1
UI_PORT ?= 8088
AGENT_PORT ?= 8765
RUNS_DIR ?= artifacts/runs
RUN_ID ?= offline-demo-run
DOCTOR_ARGS ?=
LOCAL_MODEL_ARGS ?=
DEMO_ARGS ?=
SERVE_ARGS ?=

APP = PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m agentstack_benchmark.cli
# Explicit commands exposed by aliases for docs/tests:
# - agentstack_benchmark.cli doctor
# - agentstack_benchmark.cli demo-local
# - --agent-mode auto-local-model

help:
	@echo "AgentStack Benchmark local MVP commands"
	@echo "  make doctor                 # readiness JSON: ports, URLs, local-model status"
	@echo "  make demo-local             # start offline demo agent + browser UI"
	@echo "  make demo-local-once        # non-blocking offline smoke"
	@echo "  make local-model-check      # loopback local model autodetect"
	@echo "  make demo-local-auto        # try local model, fallback to offline demo"
	@echo "  make demo-local-auto-once   # non-blocking auto-local-model smoke"
	@echo "  make serve                  # serve existing artifacts at local UI"
	@echo "  make test                   # run unittest suite"
	@echo "  make compile                # compile Python sources"

test:
	$(APP) --help >/dev/null
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

compile:
	$(PYTHON) -m compileall -q src examples tests

doctor:
	$(APP) doctor --host $(HOST) --ui-port $(UI_PORT) --agent-port $(AGENT_PORT) $(DOCTOR_ARGS)

local-model-check:
	$(APP) local-model-check $(LOCAL_MODEL_ARGS)

demo-local:
	$(APP) demo-local --host $(HOST) --ui-port $(UI_PORT) --agent-port $(AGENT_PORT) --runs-dir $(RUNS_DIR) --run-id $(RUN_ID) $(DEMO_ARGS)

demo-local-once:
	$(APP) demo-local --host $(HOST) --ui-port $(UI_PORT) --agent-port $(AGENT_PORT) --runs-dir $(RUNS_DIR) --run-id $(RUN_ID) --once $(DEMO_ARGS)

demo-local-auto:
	$(APP) demo-local --agent-mode auto-local-model --host $(HOST) --ui-port $(UI_PORT) --agent-port $(AGENT_PORT) --runs-dir $(RUNS_DIR) --run-id $(RUN_ID) $(DEMO_ARGS)

demo-local-auto-once:
	$(APP) demo-local --agent-mode auto-local-model --host $(HOST) --ui-port $(UI_PORT) --agent-port $(AGENT_PORT) --runs-dir $(RUNS_DIR) --run-id $(RUN_ID) --once $(DEMO_ARGS)

serve:
	$(APP) serve --host $(HOST) --port $(UI_PORT) --runs-dir $(RUNS_DIR) $(SERVE_ARGS)
