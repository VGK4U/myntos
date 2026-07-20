# MNR Platform — Developer Utilities
#
# Usage:
#   make sync-db          Copy production data → development database
#   make sync-db-dry      Show what would be synced without touching dev
#
# Requires DATABASE_URL (dev) to be set in the environment (Replit Secrets).
# The production URL lives only in backend/copy_prod_to_dev.py (single source of truth).

.PHONY: sync-db sync-db-dry help

help:
	@echo ""
	@echo "MNR Platform — Make targets"
	@echo "----------------------------"
	@echo "  make sync-db       Copy production DB → development DB"
	@echo "  make sync-db-dry   Dry-run: list tables that would be synced (no writes)"
	@echo ""

sync-db:
	@echo ""
	@echo "========================================================"
	@echo "  PROD → DEV database sync"
	@echo "  Started: $$(date '+%Y-%m-%d %H:%M:%S')"
	@echo "========================================================"
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL is not set. Set it via Replit Secrets."; \
		exit 1; \
	fi
	cd backend && python copy_prod_to_dev.py
	@echo ""
	@echo "Sync complete. Restart the FastAPI Backend workflow to pick up fresh data."
	@echo ""

sync-db-dry:
	@echo ""
	@echo "========================================================"
	@echo "  PROD → DEV dry-run (no writes)"
	@echo "========================================================"
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL is not set."; \
		exit 1; \
	fi
	cd backend && python copy_prod_to_dev_dry.py
