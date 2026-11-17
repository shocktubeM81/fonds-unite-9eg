# Générateur du Fonds d'unité du 9 EG

Le générateur assemble `constitution-projet.md`, les annexes A à G (ordre alphabétique), puis les documents d'appui Markdown liés. Les sources restent inchangées. Les liens entre ces documents deviennent des renvois internes dans le recueil.

Depuis la racine du dépôt :

```powershell
py -m pip install -r generateur/requirements.txt
.\generateur\Generer-les-documents.ps1
```

Le double-clic sur `Generer-les-documents.cmd` fonctionne aussi. Les résultats sont dans `exports/`, indépendamment du dossier de lancement :

- `constitution-fonds-unite-9eg.docx`
- `constitution-fonds-unite-9eg.pdf`
- `constitution-fonds-unite-9eg.txt`
- `generation.json` : sources et empreintes, nombre de paragraphes vérifiés et moteur PDF.

Le PDF utilise Word si disponible, sinon ReportLab. Pour imposer ReportLab :

```powershell
.\generateur\Generer-les-documents.ps1 -PdfMoteur reportlab
```

Les tableaux et le gras sont conservés dans Word et PDF. La table des matières Word est un champ actualisable dans Word; celle du PDF ReportLab est calculée lors de la génération. Le profil de couverture et l'insigne sont dans `modeles/9eg.json`.

Vérification :

```powershell
py -m unittest discover -s generateur -p test_sources.py
```
