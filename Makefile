.PHONY: clean
clean:
	rm -rf env

.PHONY: prepare
prepare: clean
	virtualenv env -p python3
	env/bin/pip install -r requirements.txt

.PHONY: run_wms
run_wms:
	env/bin/python tile_server.py

