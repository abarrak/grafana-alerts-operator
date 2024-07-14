all: setup

.PHONY: requirements.txt test

setup:
	python3 -m venv ./
	. ./bin/activate
	pip install -r ./src/requirements.txt

test:
	. ./bin/activate
	pytest ./test/

clean:
	. ./bin/activate
	rm -rf ./.pytest_cache
	rm -rf ./__pycache__
	deactivate

build:
	docker build --tag grafana-alert:1.0 .

