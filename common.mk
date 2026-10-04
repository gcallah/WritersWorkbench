# common make vars and targets:
export PROJ_DIR = $(shell pwd)
export SERVER_DIR = $(PROJ_DIR)/server
export PROJECTS_DIR = $(PROJ_DIR)/projects

export PANDOC = pandoc
export PYLINT = flake8
export PYLINTFLAGS = --exclude=__main__.py

# Use a local SQLite database in database/ at the top of the repo:
export DATABASE = sqlite
export SQLITE_LOC ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/database

PYTHONFILES = $(shell ls *.py)
PYTESTFLAGS = -vv --verbose --cov-branch --cov-report term-missing --tb=short -W ignore::FutureWarning

MAIL_METHOD = api

FORCE:

tests: lint pytests

lint: $(patsubst %.py,%.pylint,$(PYTHONFILES))

%.pylint:
	$(PYLINT) $(PYLINTFLAGS) $*.py

pytests: FORCE
	echo $(USER_DB_FILE)
	export TEST_DB=1 SQL_DB_NM=test_sql.db; pytest $(PYTESTFLAGS) --cov=$(PKG)

# test a python file:
%.py: FORCE
	$(PYLINT) $(PYLINTFLAGS) $@
	export TEST_DB=1 SQL_DB_NM=test_sql.db; pytest $(PYTESTFLAGS) tests/test_$*.py

nocrud:
	-rm *~
	-rm *.log
	-rm *.out
	-rm .*swp
	-rm $(TESTDIR)/*~
