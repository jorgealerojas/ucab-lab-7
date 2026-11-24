.PHONY: test coverage lint validate local-demo clean-generated

test:
	python3 -m pytest

coverage:
	python3 -m coverage run -m pytest
	python3 -m coverage report

lint:
	python3 -m compileall -q app scripts tests
	shellcheck scripts/*.sh
	cfn-lint infra/lab-stack.yaml

validate: lint coverage
	python3 scripts/validate_repository.py

local-demo:
	python3 scripts/run_local_demo.py --config config/pipeline.example.json --output generated/local-demo

clean-generated:
	rm -rf generated
