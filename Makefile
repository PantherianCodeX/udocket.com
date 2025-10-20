.PHONY: lint-schemas

# Lightweight, opt-in schema validation; does not run in CI by default.
lint-schemas:
	@echo "Validating JSON Schemas under spec/schemas ..."
	@python scripts/codegen/schemas.py validate

