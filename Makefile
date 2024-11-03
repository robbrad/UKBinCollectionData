.PHONY: install pre-build build black pycodestyle update-wiki

## @CI_actions Installs the checked out version of the code to your poetry managed venv
install:
	poetry install --without dev

install-dev:
	poetry install 

## @CI_actions Runs code quality checks
pre-build: black unit-tests
	rm setup.py || echo "There was no setup.py"
	poetry show --no-dev | awk '{print "poetry add "$$1"=="$$2}' | sort | sh

## @CI_actions Builds the project into an sdist
build:
	poetry build -f sdist

## @Code_quality Runs black on the checked out code
black:
	poetry run black uk_bin_collection

## @Code_quality Runs pycodestyle on the the checked out code
pycodestyle:
	poetry run pycodestyle --statistics -qq uk_bin_collection

## @Testing runs unit tests
integration-tests: ## runs tests for the project
	if [ -z "$(councils)" ]; then \
		poetry run pytest uk_bin_collection/tests/step_defs/ -n logical --alluredir=build/$(matrix)/allure-results; \
	else \
		poetry run pytest uk_bin_collection/tests/step_defs/ -k "$(councils)" -n logical --alluredir=build/$(matrix)/allure-results; \
	fi

parity-check:
	poetry run python uk_bin_collection/tests/council_feature_input_parity.py $(repo) $(branch)

unit-tests:
	poetry run coverage erase
	- poetry run coverage run --append --omit "*/tests/*" -m pytest -vv -s --log-cli-level=DEBUG uk_bin_collection/tests custom_components/uk_bin_collection/tests --ignore=uk_bin_collection/tests/step_defs/ 
	poetry run coverage xml

update-wiki:
	poetry run python wiki/generate_wiki.py
