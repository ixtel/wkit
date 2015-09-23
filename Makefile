flake:
	flake8 wkit test

flake_verbose:
	flake8 wkit test --show-pep8

test:
	py.test

coverage:
	py.test --cov weblib --cov-report term-missing

clean:
	find -name '*.pyc' -delete
	find -name '*.swp' -delete

upload:
	python setup.py sdist upload

build: venv deps

venv:
	virtualenv --system-site-packages --python=python3.4 .env
	
deps:
	.env/bin/pip install -r requirements.txt

.PHONY: all build venv flake test vtest testloop cov clean doc
