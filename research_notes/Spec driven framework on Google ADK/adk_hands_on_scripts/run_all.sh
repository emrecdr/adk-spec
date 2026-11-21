#!/bin/bash
# Runs every experiment script, unchanged, against one virtual environment and records the output.
#   ./run_all.sh <venv-dir> <output-dir> <data-dir>
# Example: ./run_all.sh .venv out_2150 data_2150 ; ./run_all.sh .venv-2141 out_2141 data_2141
set -u
cd "$(dirname "$0")"
VENV="$1"; OUT="$2"; export SPIKE_DATA="$3"
PY="$VENV/bin/python"; ADK="$VENV/bin/adk"
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT" "$SPIKE_DATA"

run() {  # run <output-name> <command...>
  local name="$1"; shift
  "$@" > "$OUT/$name.txt" 2>&1
  echo "exit=$? $name"
}

run q01_install            "$PY" q01_install.py
run q01_adk_version        env PYTHONWARNINGS=always "$ADK" --version
run q01_import_w_error     "$PY" -W error -c "from google.adk import Agent, Workflow, Event, Context, Runner; print('ok: imports succeed with every warning turned into an error')"
run q01_adk_help           "$ADK" --help
run q02_function_workflow  "$PY" q02_function_workflow.py
run q02b_dynamic_and_edge_cases "$PY" q02b_dynamic_and_edge_cases.py
run q03_custom_agent       "$PY" q03_custom_agent.py
run q03b_custom_agent_output "$PY" q03b_custom_agent_output.py
run q04_deprecated_agents  "$PY" q04_deprecated_agents.py
run q04b_default_filter    "$PY" q04b_default_filter.py
run q04b_w_error           "$PY" -W error q04b_default_filter.py
run q05a_hitl_inmemory     "$PY" q05a_hitl_inmemory.py
run q05b_sqlite_1_start_plain      "$PY" q05b_hitl_sqlite.py start plain
run q05b_sqlite_2_resume_plain     "$PY" q05b_hitl_sqlite.py resume plain
run q05b_sqlite_3_start_resumable  "$PY" q05b_hitl_sqlite.py start res resumable
run q05b_sqlite_4_resume_resumable "$PY" q05b_hitl_sqlite.py resume res resumable
run q05b_sqlite_5_tables   "$PY" -c "import sqlite3, os; c = sqlite3.connect(os.path.join(os.environ['SPIKE_DATA'], 'q05_sessions_plain.db')); print('tables:', sorted(r[0] for r in c.execute(\"select name from sqlite_master where type='table'\"))); print('events rows:', c.execute('select count(*) from events').fetchone()[0])"
run q05c_hitl_extras       "$PY" q05c_hitl_extras.py
run q06_swap_llm_for_python "$PY" q06_swap_llm_for_python.py
run q06b_typed_contract    "$PY" q06b_typed_contract.py
run q07_structured_output  "$PY" q07_structured_output.py
run q08_skip_model_call    "$PY" q08_skip_model_call.py
run q09_plugins            "$PY" q09_plugins.py
run q10_function_tools     "$PY" q10_function_tools.py
run q11_artifacts          "$PY" q11_artifacts.py
run q12_pytest             "$PY" -m pytest test_q12_pytest.py -v -p no:cacheprovider -o asyncio_default_fixture_loop_scope=function
run q12_pytest_w_error     "$PY" -m pytest test_q12_pytest.py -q -p no:cacheprovider -o asyncio_default_fixture_loop_scope=function -W error
run q13_event_metadata     "$PY" q13_event_metadata.py
run q13_adk_eval_help      "$ADK" eval --help
run q13_adk_conformance_help "$ADK" conformance --help
run q13_adk_conformance_record_help "$ADK" conformance record --help
run q13_adk_conformance_test_help   "$ADK" conformance test --help
