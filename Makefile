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

docs: format $(DOCS_SRC_DIR)/_build/html/index.html
	touch $(DOCS_SRC_DIR)/_build/html/.nojekyll

test:
	$(PYTHON) -m unittest pytb/test/test_*.py

clean:
	-rm -r $(DOCS_SRC_DIR)/_build/html/
	$(PYTHON) setup.py clean

install:
	$(PYTHON) setup.py install

.PHONY: docs clean test format