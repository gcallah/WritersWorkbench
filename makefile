include common.mk

dev_env: FORCE
	pip3 install --upgrade pip
	pip3 install -r requirements-dev.txt
	echo "You need to see these env vars in your startup script"
	cat docs/env_vars_to_set.txt

prod_env: FORCE
	pip3 install --upgrade pip
	echo "Uninstalling backendcore"
	yes | pip uninstall backendcore
	echo "Install packages"
	pip install --upgrade -r requirements.txt

new_code: FORCE
	echo "Pulling new code"
	git pull origin master

rebuild: new_code prod_env
	echo "Going to reboot the webserver using $(API_TOKEN)"
	pa_reload_webapp.py $(PA_DOMAIN)
	touch reboot
	echo "Finished rebuild."

dev_container: Dockerfile  $(REQ_DIR)/requirements-dev.txt
	docker build -t apimm-dev $(PROJ_DIR)

all_tests: FORCE
	cd $(SERVER_DIR); make tests

tests: FORCE
	echo "Run make all_tests from top level dir."

docs: $(PYTHONFILES)
	rm -rf $(HTML_DOCS_DIR)
	pydoc3 -f --html -o $(DOCS_DIR) -c show_source_code=False --skip-errors $(SERVER_DIR)

github: FORCE
	-git commit -a
	git push origin master

prod: all_tests github

new_core: FORCE
	pip uninstall backendcore
	pip install git+ssh://git@github.com/AthenaKouKou/BackEndCore.git

local_core: FORCE
	pip uninstall backendcore
	pip install git+file://$(MIX_HOME)/BackEndCore/

integration_tests:
	cd $(SERVER_DIR); make tests

pull: new_core
	git pull
