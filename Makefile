PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin
LIBDIR = $(PREFIX)/lib/bbs-popcorn
DATADIR = $(PREFIX)/share
APPDIR = $(DATADIR)/applications
ICONDIR = $(DATADIR)/icons/hicolor/scalable/apps

PYTHON = python3
PIP = pip3
APP_ID = io.github.blacksamdev.Popcorn

.PHONY: all install uninstall install-deps check dev clean

all:
	@echo "BBS pOpcOrn — cibles disponibles :"
	@echo "  make install       Installe dans $(PREFIX)"
	@echo "  make install-user  Installe dans ~/.local"
	@echo "  make install-deps  Installe les dépendances Python"
	@echo "  make uninstall     Désinstalle"
	@echo "  make dev           Lance directement depuis les sources"
	@echo "  make check         Vérifie les dépendances"

# ─────────────────────────────
# Dépendances système
# ─────────────────────────────
install-deps:
	@echo ">>> Vérification des dépendances système..."
	@which $(PYTHON) > /dev/null || (echo "ERREUR : python3 manquant" && exit 1)
	@$(PYTHON) -c "import gi" 2>/dev/null || \
		(echo ">>> Installation de PyGObject..." && \
		$(PIP) install PyGObject --break-system-packages)
	@$(PYTHON) -c "import gi; gi.require_version('WebKit', '6.0'); from gi.repository import WebKit" 2>/dev/null || \
		echo "ATTENTION : WebKitGTK 6.0 non trouvé — installez libwebkit2gtk-4.1-dev ou webkit2gtk-4.1"
	@which mpv > /dev/null || echo "ATTENTION : mpv non trouvé — installez mpv"
	@which yt-dlp > /dev/null || \
		(echo ">>> Installation de yt-dlp..." && \
		$(PIP) install yt-dlp --break-system-packages)
	@echo ">>> Dépendances OK."

check:
	@echo ">>> Vérification de l'environnement..."
	@$(PYTHON) -c "import gi; print('PyGObject OK')" 2>/dev/null || echo "MANQUANT : PyGObject"
	@$(PYTHON) -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')" 2>/dev/null || echo "MANQUANT : GTK4"
	@$(PYTHON) -c "import gi; gi.require_version('WebKit', '6.0'); from gi.repository import WebKit; print('WebKitGTK 6.0 OK')" 2>/dev/null || echo "MANQUANT : WebKitGTK 6.0"
	@which mpv > /dev/null && echo "mpv OK ($(shell which mpv))" || echo "MANQUANT : mpv"
	@which yt-dlp > /dev/null && echo "yt-dlp OK ($(shell which yt-dlp))" || echo "MANQUANT : yt-dlp"

# ─────────────────────────────
# Installation système (sudo)
# ─────────────────────────────
install:
	@echo ">>> Installation dans $(PREFIX)..."
	install -Dm755 wrapper-native.sh $(BINDIR)/bbs-popcorn
	install -d $(LIBDIR)/bbs_popcorn
	install -Dm644 src/bbs_popcorn/__init__.py    $(LIBDIR)/bbs_popcorn/__init__.py
	install -Dm644 src/bbs_popcorn/main.py         $(LIBDIR)/bbs_popcorn/main.py
	install -Dm644 src/bbs_popcorn/app.py          $(LIBDIR)/bbs_popcorn/app.py
	install -Dm644 src/bbs_popcorn/player.py       $(LIBDIR)/bbs_popcorn/player.py
	install -Dm644 src/bbs_popcorn/updater.py      $(LIBDIR)/bbs_popcorn/updater.py
	install -Dm644 src/bbs_popcorn/cookies.py      $(LIBDIR)/bbs_popcorn/cookies.py
	install -Dm644 src/bbs_popcorn/logging_utils.py $(LIBDIR)/bbs_popcorn/logging_utils.py
	install -Dm644 src/bbs_popcorn/resume_store.py $(LIBDIR)/bbs_popcorn/resume_store.py
	install -Dm644 src/bbs_popcorn/history_store.py $(LIBDIR)/bbs_popcorn/history_store.py
	install -Dm644 data/$(APP_ID).desktop $(APPDIR)/$(APP_ID).desktop
	install -Dm644 data/$(APP_ID).svg     $(ICONDIR)/$(APP_ID).svg
	@echo ">>> Installation terminée. Lancez : bbs-popcorn"

install-user:
	PREFIX=$$HOME/.local $(MAKE) install
	@echo ">>> Assurez-vous que $$HOME/.local/bin est dans votre PATH."

# ─────────────────────────────
# Désinstallation
# ─────────────────────────────
uninstall:
	@echo ">>> Désinstallation..."
	rm -f  $(BINDIR)/bbs-popcorn
	rm -rf $(LIBDIR)
	rm -f  $(APPDIR)/$(APP_ID).desktop
	rm -f  $(ICONDIR)/$(APP_ID).svg
	@echo ">>> Désinstallation terminée."

# ─────────────────────────────
# Développement (sans install)
# ─────────────────────────────
dev:
	PYTHONPATH=src $(PYTHON) -m bbs_popcorn.main

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
