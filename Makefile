PYTHON = python3

MODULE_NAME = pytb
AUTHOR = "Daniel Grießhaber"
DOCS_SRC_DIR = docs-src
DOCS_DIR = docs

$(DOCS_SRC_DIR)/%.rst: $(MODULE_NAME)/%.py

$(DOCS_SRC_DIR)/_build/html/%.html: $(DOCS_SRC_DIR)/%.rst
	sphinx-apidoc -Fa -A $(AUTHOR) -o $(DOCS_SRC_DIR) $(MODULE_NAME)
	make -C $(DOCS_SRC_DIR) doctest
	make -C $(DOCS_SRC_DIR) html

$(DOCS_DIR)/%.html: $(DOCS_SRC_DIR)/_build/html/%.html
	cp -r $(DOCS_SRC_DIR)/_build/html $(DOCS_DIR)
	touch $(DOCS_DIR)/.nojekyll

docs: $(DOCS_DIR)/index.html

test:
	$(PYTHON) -m unittest pytb/test/test_*.py

clean:
	-rm -r $(DOCS_DIR)/
	$(PYTHON) setup.py clean

install:
	$(PYTHON) setup.py clean

.PHONY: docs clean test