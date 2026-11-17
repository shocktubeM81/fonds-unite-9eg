"""Vérifier l'assemblage et les exports du Fonds d'unité."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from sources import ROOT, load_sources
GEN = runpy.run_path(str(ROOT / 'generateur/generer-documents.py'))

class DocumentsTest(unittest.TestCase):
    def setUp(self):
        self.text, self.structure, self.sources = load_sources()
        self.segments, self.count = GEN['validate'](self.text, self.structure)
        self.blocks = GEN['document_blocks'](self.text, self.segments)

    def test_sources_and_links(self):
        self.assertEqual(list(self.sources)[0], 'constitution-projet.md')
        self.assertEqual(len([p for p in self.sources if p.startswith('annexes/')]), 7)
        self.assertEqual(self.count, 20)
        ids = [a for b in self.blocks for a in b['ids']]
        self.assertEqual(len(ids), len(set(ids)))
        links = [m[2] for b in self.blocks for m in GEN['LINK'].finditer(b['text'])]
        self.assertTrue(any(link.startswith('#source-') for link in links))
        self.assertTrue(all(not link.endswith('.md') for link in links))

    def test_invalid_numbering_and_links(self):
        with self.assertRaisesRegex(ValueError, 'Numérotation discontinue'):
            GEN['validate'](self.text.replace('**2.**', '**99.**', 1), self.structure)
        with self.assertRaisesRegex(ValueError, 'Renvoi interne sans destination'):
            GEN['document_blocks'](self.text+'\n[renvoi](#inexistant)\n', self.segments)

    def test_export(self):
        from docx import Document
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run([sys.executable, str(ROOT/'generateur/generer-documents.py'), '--pdf-moteur', 'reportlab', '--sortie', folder], check=True, capture_output=True)
            out = Path(folder); name = 'constitution-fonds-unite-9eg'
            self.assertEqual({p.suffix for p in out.iterdir()}, {'.txt', '.docx', '.pdf', '.json'})
            doc = Document(out/(name+'.docx'))
            self.assertGreater(len(doc.tables), 0)
            self.assertIn("Fonds d'unité", doc.core_properties.author)
            pdf = PdfReader(out/(name+'.pdf'))
            self.assertGreater(len(pdf.pages), 5)
            text = '\n'.join(page.extract_text() for page in pdf.pages)
            for letter in 'ABCDEFG':
                self.assertIn('Annexe '+letter, text)
            self.assertTrue(pdf.named_destinations)
            meta = json.loads((out/'generation.json').read_text(encoding='utf-8'))
            self.assertEqual(set(meta['sources']), set(self.sources))

if __name__ == '__main__':
    unittest.main()
