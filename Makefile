.PHONY: test lint format check install uninstall release packages test-packages test-packages-interactive

ICONS_DIR := $(HOME)/.local/share/icons
APPS_DIR  := $(HOME)/.local/share/applications
SRC_APP_ICON  := src/linxpad/icons/linxpad.png
SRC_FOLDER_ICON  := src/linxpad/icons/linxpad-folder.png
DESKTOP   := $(APPS_DIR)/linxpad.desktop

install:
	python3 -m pip install -e .
	mkdir -p $(ICONS_DIR) $(APPS_DIR)
	cp $(SRC_APP_ICON) $(ICONS_DIR)/linxpad.png
	cp $(SRC_FOLDER_ICON) $(ICONS_DIR)/linxpad-folder.png
	@printf '[Desktop Entry]\nType=Application\nName=LinxPad\nComment=Full screen applications files folders and web search launcher for desktops\nExec=linxpad\nIcon=$(ICONS_DIR)/linxpad.png\nCategories=Utility;\nTerminal=false\nStartupNotify=false\nStartupWMClass=LinxPad\n' > $(DESKTOP)
	update-desktop-database $(APPS_DIR) 2>/dev/null || true

uninstall:
	python3 -m pip uninstall -y linxpad
	rm -f $(ICONS_DIR)/linxpad.png
	rm -f $(DESKTOP)
	update-desktop-database $(APPS_DIR) 2>/dev/null || true

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

test-packages:
	bash packaging/scripts/test-packages.sh

test-packages-interactive:
	bash packaging/scripts/test-packages.sh --interactive
