all: install

install:
	python setup.py install

test :
	py.test schema_validation --doctest-modules

test-coverage:
	py.test schema_validation --cov=schema_validation
