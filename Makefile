APPNAME = mandoline-py
VERSION = 0.8.6

all::
	@echo "make build install deinstall tests clean"
	@echo "HINT: if you like to code on the base, run 'python3 mandoline/__init__.py' after running build at least once"

build::
	#sudo apt install python3-savitar
	python3 setup.py build

install::
	sudo python3 setup.py install

deinstall::

tests::
	cd tests && $(MAKE)

clean::
	rm -rf build
	cd tests && $(MAKE) clean

# -- devs only:

edit::
	${EDITOR} mandoline/*.py setup.py README.rst CHANGES LICENSE Makefile tests/Makefile

change::
	git commit -am "..."

push::
	git push -u origin master

pull::
	git pull

backup::
	cd ..; tar cfvz ~/Backup/${APPNAME}-${VERSION}.tar.gz ${APPNAME}; scp ~/Backup/${APPNAME}-${VERSION}.tar.gz backup:Backup/

