#!/usr/bin/env python3
"""Remplit le modèle Apps Script VideoAsk → Drive.

Usage : python3 integrations/fill_gs.py <ID du dossier RUSHES> [--out fichier.gs]
Écrit le code prêt à coller et affiche la clé secrète à ajouter à l'URL du webhook (?k=...).
"""
import argparse
import secrets
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder_id')
    ap.add_argument('--secret', default=None)
    ap.add_argument('--out', default='/tmp/videoask_to_drive.gs')
    a = ap.parse_args()
    secret = a.secret or secrets.token_urlsafe(12)
    code = (HERE / 'videoask_to_drive.gs').read_text(encoding='utf-8')
    code = code.replace('{{FOLDER_ID}}', a.folder_id).replace('{{SECRET}}', secret)
    Path(a.out).write_text(code, encoding='utf-8')
    print(f'code: {a.out}')
    print(f'secret: {secret}')


if __name__ == '__main__':
    main()
