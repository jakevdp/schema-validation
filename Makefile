all: install

install:
	python setup.py install

test :
	py.test schema_validation --doctest-modules
