# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
DOCSDIRNAME   = mp2i-discord-bot-docs

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

apidoc:
	@sphinx-apidoc -o "$(SOURCEDIR)" ../mp2i --private -A "Adrien Jayat"

docs:
	@make html
	@cp -rf "$(BUILDDIR)/html/" "../../"
	@rm -rf "../../$(DOCSDIRNAME)/"
	@mv -f "../../html/" "../../$(DOCSDIRNAME)/"
	@make clean
	@rm -rf "$(BUILDDIR)/html" "logs/"


.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
