.PHONY: replay-latest replay-diff reconcile-broker status health live-dry-run manifest preflight gated-live next-run

replay-latest:
	@echo "Running replay check on latest pack..."
	@python regimeflex/scripts/replay_latest.py

# Usage:
#   make replay-diff OLD=replays/replay_20251019_1917Z.json NEW=replays/replay_20251020_1917Z.json
replay-diff:
	@echo "Comparing replay packs:"
	@echo "  OLD = $(OLD)"
	@echo "  NEW = $(NEW)"
	@python3 regimeflex/scripts/replay_diff.py "$(OLD)" "$(NEW)"

reconcile-broker:
	@echo "Reconciling internal positions vs broker (latest replay vs Alpaca)..."
	@python3 regimeflex/scripts/reconcile_broker.py

status:
	@echo "Building RegimeFlex status dashboard from latest replay..."
	@python3 regimeflex/scripts/status_dashboard.py

health:
	@python3 regimeflex/scripts/health_check.py

live-dry-run:
	@echo "Running RegimeFlex in DRY-RUN mode (no orders will be sent)..."
	@REGIMEFLEX_DRY_RUN=1 python3 regimeflex/scripts/run_offline_from_config.py

incidents:
	@echo "Showing incidents for today:"
	@ls -1 logs/incidents 2>/dev/null | grep `date +%Y-%m-%d` || echo "No incident file for today."
	@echo "------"
	@if [ -f logs/incidents/`date +%Y-%m-%d`_incidents.jsonl ]; then \
		cat logs/incidents/`date +%Y-%m-%d`_incidents.jsonl; \
	else \
		echo "No incidents logged today."; \
	fi

manifest:
	@python3 regimeflex/scripts/manifest.py

preflight:
	@python3 regimeflex/scripts/preflight.py

gated-live:
	@python3 regimeflex/scripts/gated_live.py

next-run:
	@python3 regimeflex/scripts/next_run.py

