.PHONY: cli test coverage clean

cli:
	python3 -m src.cli

test:
	python3 -m pytest tests/ -v

coverage:
	coverage run -m pytest tests/
	coverage report -m

clean:
	rm -rf .coverage htmlcov .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +