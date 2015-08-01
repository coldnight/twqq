PACKAGE = windmvc/
DOCPATH = doc
PYTHONBIN = python2

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "		doc 			to generate document from source code"
	@echo "		html 			to generate html from document"
	@echo "		htmldoc 		to generate html document from srouce code"
	@echo "		dist 			to upload package to pypi server"
	@echo "		clean 			to clean temp file"


doc:
	rm -rf docs/*
	sphinx-apidoc -F -o $(DOCPATH) $(PACKAGE)

html:
	$(PYTHONBIN) setup.py install
	cd $(DOCPATH) && make html && cd ..

htmldoc:
	$(PYTHONBIN) setup.py install
	rm -rf $(DOCPATH)/*
	sphinx-apidoc -F -o $(DOCPATH) $(PACKAGE)
	cd $(DOCPATH)  && make html && cd ..

dist:
	$(PYTHONBIN) setup.py register sdist upload && rm -rf *.egg_info build dist

clean:
	find ./ -name '*.py[co]' -exec rm -f {} \;
	rm -f check.jpg wait lock
	rm -rf *.egg-info build/ dist/


