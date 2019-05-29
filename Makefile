PYTHON = python3

MODULE_NAME = pytb
AUTHOR = "Daniel Grießhaber"
DOCS_DIR = docs


$(DOCS_DIR)/_build/html/%.html: $(DOCS_DIR)/%.rst
	sphinx-apidoc -Fa -A $(AUTHOR) -o $(DOCS_DIR) $(MODULE_NAME)
	make -C $(DOCS_DIR) doctest
	make -C $(DOCS_DIR) html

docs: $(DOCS_DIR)/_build/html/index.html

test:
	$(PYTHON) -m unittest pytb/test/test_*.py

clean:
	rm -r $(DOCS_DIR)/_build
	$(PYTHON) setup.py clean

install:
	$(PYTHON) setup.py clean

.PHONY: docs clean test