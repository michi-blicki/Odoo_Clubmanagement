#!/usr/bin/env python3
"""
Übersetzt die clubmanagement.pot automatisch mit DeepL in drei Sprachen:
- de_CH (Deutsch – Schweiz)
- fr_FR (Französisch – Frankreich)
- it_IT (Italienisch – Italien)
"""

import os
import sys
import polib
import deepl
from dotenv import load_dotenv
from tqdm import tqdm

# === KONFIGURATION ==========================================================
# Lade Environment-Variablen (API-Key aus .env)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

if not DEEPL_API_KEY:
    sys.exit("❌ Kein DeepL API Key gefunden. Bitte in .env-Datei DEEPL_API_KEY=... setzen!")

# Pfade
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # clubmanagement/
I18N_DIR = os.path.join(BASE_DIR, "clubmanagement", "i18n")
SOURCE_FILE = os.path.join(I18N_DIR, "clubmanagement.pot")

# Zielsprache-Konfiguration
TARGET_LANGS = {
    "de_CH": "DE",  # Deutsch (Schweiz)
    "fr_FR": "FR",     # Französisch
    "it_IT": "IT"      # Italienisch
}

# ===========================================================================


def translate_po(source_path, target_lang_code, deepl_lang):
    print(f"Übersetze nach {target_lang_code} ({deepl_lang}) …")

    po = polib.pofile(source_path)
    translator = deepl.Translator(DEEPL_API_KEY)

    total = len(po)
    translated_count = 0

    for entry in tqdm(po, desc=f"{target_lang_code}"):
        # Nur übersetzen, wenn msgid vorhanden und msgstr leer ist
        if entry.msgid and not entry.msgstr:
            try:
                # Platzhalter schützen
                safe_text = entry.msgid.replace("%", "%%")
                result = translator.translate_text(
                    safe_text,
                    source_lang="EN",
                    target_lang=deepl_lang
                )
                entry.msgstr = result.text.replace("%%", "%")
                translated_count += 1
            except Exception as e:
                print(f"⚠️ Fehler bei '{entry.msgid[:60]}': {e}")

    # Sprachmetadaten hinzufügen
    po.metadata["Language"] = target_lang_code
    po.metadata["Last-Translator"] = "DeepL (automatisch)"
    po.metadata["Language-Team"] = f"{target_lang_code} Team"
    po.metadata["X-Generator"] = "translate_po_deepl.py"

    # Ergebnisdatei speichern
    target_path = os.path.join(I18N_DIR, f"{target_lang_code}.po")
    po.save(target_path)

    print(f"✅ {translated_count}/{total} Einträge übersetzt → {target_path}\n")


def main():
    print("=== Starte Übersetzung mit DeepL ===")
    print(f"Quell-Datei: {SOURCE_FILE}\n")

    if not os.path.exists(SOURCE_FILE):
        sys.exit(f"❌ Datei {SOURCE_FILE} wurde nicht gefunden.")

    for target_lang_code, deepl_lang in TARGET_LANGS.items():
        translate_po(SOURCE_FILE, target_lang_code, deepl_lang)

    print("🎉 Übersetzung abgeschlossen.")


if __name__ == "__main__":
    main()
