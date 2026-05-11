.PHONY: run test lint format check install uninstall wipe release packages package test-packages test-package

ICONS_DIR := $(HOME)/.local/share/icons
APPS_DIR  := $(HOME)/.local/share/applications
SRC_APP_ICON  := src/linxpad/icons/linxpad.png
SRC_FOLDER_ICON  := src/linxpad/icons/linxpad-folder.png
DESKTOP   := $(APPS_DIR)/linxpad.desktop

run:
	PYTHONPATH=src python3 -m linxpad.main

install:
	python3 -m pip install -e .
	mkdir -p $(ICONS_DIR) $(APPS_DIR)
	cp $(SRC_APP_ICON) $(ICONS_DIR)/linxpad.png
	cp $(SRC_FOLDER_ICON) $(ICONS_DIR)/linxpad-folder.png
	@printf '[Desktop Entry]\nType=Application\nName=LinxPad\nComment=Full screen applications files folders and web search launcher for desktops\nExec=linxpad\nIcon=$(ICONS_DIR)/linxpad.png\nCategories=Utility;\nTerminal=false\nStartupNotify=false\nStartupWMClass=LinxPad\n' > $(DESKTOP)
	update-desktop-database $(APPS_DIR) 2>/dev/null || true

uninstall:
	bash uninstall

wipe:
	bash uninstall --wipe

test:
	python3 -m pytest tests/ -v

lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	ruff check --fix src/ tests/
	black src/ tests/

check: lint test

release:
	bash packaging/scripts/release.sh

packages:
	bash packaging/scripts/packages.sh

package:
	bash packaging/scripts/packages.sh --interactive

test-packages:
	bash packaging/scripts/test-packages.sh

test-package:
	bash packaging/scripts/test-packages.sh --interactive
