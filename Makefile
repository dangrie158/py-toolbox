PYTHON = python3

MODULE_NAME = pytb
AUTHOR = "Daniel Grießhaber"
DOCS_SRC_DIR = docs

$(DOCS_SRC_DIR)/%.rst: $(MODULE_NAME)/%.py

$(DOCS_SRC_DIR)/_build/html/%.html: $(DOCS_SRC_DIR)/%.rst
	make -C $(DOCS_SRC_DIR) doctest
	make -C $(DOCS_SRC_DIR) html

format:
	black $(MODULE_NAME)

analyze:
	$(PYTHON) -m mypy pytb/*.py
	$(PYTHON) -m pylint pytb/*.py

docs: format $(DOCS_SRC_DIR)/_build/html/index.html
	touch $(DOCS_SRC_DIR)/_build/html/.nojekyll

test: format analyze
	$(PYTHON) -m unittest pytb/test/test_*.py

clean:
	-rm -r $(DOCS_SRC_DIR)/_build/html/
	$(PYTHON) setup.py clean

install:
	$(PYTHON) setup.py install

release: clean test docs
	$(PYTHON) setup.py sdist upload

.PHONY: docs clean test format analyze release
