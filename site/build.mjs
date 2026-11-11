import { readFile, writeFile, mkdir, cp } from 'node:fs/promises';
import { marked } from 'marked';
import { dirname, resolve, join, posix } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = join(root, 'dist');
const constitution = await readFile(join(root, 'constitution-projet.md'), 'utf8');
const marker = '## Références consultées et validation restante';
if (!constitution.includes(marker)) throw new Error('Section des références introuvable.');
const pages = [
  ['index.html', 'Accueil', await readFile(join(root, 'site/accueil.md'), 'utf8')],
  ['constitution.html', 'Constitution', constitution],
  ['references.html', 'Références', '# Références\n\n' + constitution.split(marker)[1]],
  ['validation.html', 'Points à valider', await readFile(join(root, 'documentation/points-a-valider.md'), 'utf8')],
  ['historique.html', 'Historique', await readFile(join(root, 'documentation/historique.md'), 'utf8')],
];
const annexes = [
  ['annexe-a-mandats', 'A — Mandats du comité'],
  ['annexe-b-cadeaux', 'B — Fonds de cadeaux'],
  ['annexe-c-activites', 'C — Fonds d’activités'],
  ['annexe-d-reserve', 'D — Réserve générale et patrimoine'],
  ['annexe-e-subventions', 'E — Subventions'],
  ['annexe-f-dons-recus', 'F — Dons et reçus BNP'],
  ['annexe-g-organisation', 'G — Organisation des fonds'],
];
pages.push(['annexes.html', 'Annexes', '# Annexes de la constitution\n\n**Projet non approuvé — 11 novembre 2026.**\n\nLes annexes A à G reprennent l’organisation du modèle du 34 RGC et l’adaptent au fonds existant 5422.\n\n' + annexes.map(([slug, label]) => `- [${label}](${slug}.html)`).join('\n')]);
const routes = new Map([
  ['constitution-projet.md', 'constitution.html'],
  ['documentation/points-a-valider.md', 'validation.html'],
  ['documentation/historique.md', 'historique.html'],
  ['documentation/justification-fonds-distinct.md', 'justification.html'],
  ['documentation/concordance-34rgc.md', 'concordance.html'],
]);
const sources = new Map([
  ['index.html', 'site/accueil.md'],
  ['constitution.html', 'constitution-projet.md'],
  ['references.html', 'constitution-projet.md'],
  ['validation.html', 'documentation/points-a-valider.md'],
  ['historique.html', 'documentation/historique.md'],
]);
for (const [slug, title] of annexes) {
  const source = `annexes/${slug}.md`;
  routes.set(source, `${slug}.html`);
  sources.set(`${slug}.html`, source);
  pages.push([`${slug}.html`, title, await readFile(join(root, source), 'utf8')]);
}
for (const [file, title, source] of [
  ['justification.html', 'Pourquoi un fonds distinct?', 'documentation/justification-fonds-distinct.md'],
  ['concordance.html', 'Comparaison avec le 34 RGC', 'documentation/concordance-34rgc.md'],
]) {
  sources.set(file, source);
  pages.push([file, title, await readFile(join(root, source), 'utf8')]);
}
const navigation = [
  ['index.html', 'Accueil'], ['constitution.html', 'Constitution'],
  ['annexes.html', 'Annexes'], ['justification.html', 'Pourquoi un fonds distinct?'],
  ['references.html', 'Références'], ['validation.html', 'Validation'],
];
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
await mkdir(output, { recursive: true });
await cp(join(root, 'site/assets'), join(output, 'assets'), { recursive: true });
await writeFile(join(output, '.nojekyll'), '');
await cp(join(root, 'CNAME'), join(output, 'CNAME'));
for (const [file, title, source] of pages) {
  const nav = navigation.map(([target, label]) => `<a href="${target}"${target === file || (target === 'annexes.html' && file.startsWith('annexe-')) ? ' aria-current="page"' : ''}>${label}</a>`).join('');
  const content = marked.parse(source).replace(/href="([^"#]+)"/g, (match, href) => {
    if (/^(?:[a-z]+:|\/\/)/i.test(href)) return match;
    const [path, fragment] = href.split('#');
    if (!path.endsWith('.md')) return match;
    const sourcePath = sources.get(file) || 'constitution-projet.md';
    const destination = routes.get(posix.normalize(posix.join(posix.dirname(sourcePath), path)));
    if (!destination) throw new Error(`${file}: route Markdown absente pour ${href}`);
    return `href="${destination}${fragment ? '#' + fragment : ''}"`;
  });
  const html = `<!doctype html>
<html lang="fr-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><meta name="theme-color" content="#172c3d"><meta name="description" content="Constitution et documents du fonds existant 5422 — Fonds d’unité du 9 EG. Projet non approuvé."><title>${escape(title)} · Fonds d’unité du 9 EG</title><link rel="stylesheet" href="assets/style.css"><script defer src="assets/site.js"></script></head>
<body><a class="skip-link" href="#contenu">Passer au contenu</a><div class="reading-progress" id="reading-progress" aria-hidden="true"></div>
<header class="site-header"><div class="site-header-inner"><a class="brand" href="index.html"><img class="brand-emblem" src="assets/Logo 34RGC Det Rouyn.png" width="570" height="787" alt="" aria-hidden="true"><span class="brand-wordmark"><strong>Fonds d’unité du 9 EG</strong><span>9e Escadron du génie · Rouyn-Noranda</span></span></a><span class="header-caption">Établissement 5422</span></div><nav class="top-nav" aria-label="Navigation principale">${nav}</nav></header>
<div class="page-layout"><aside class="sidebar" id="sidebar" aria-label="Sommaire"><div class="sidebar-sticky"><div class="sidebar-title">Dans ce document</div><nav id="table-of-contents" aria-label="Navigation par section"></nav><div class="sidebar-note"><strong>Fonds existant 5422</strong><span>Projet de constitution soumis aux validations et aux approbations applicables.</span></div></div></aside>
<main class="page-main" id="contenu" tabindex="-1"><div class="page-meta"><span class="eyebrow">${escape(title)}</span><div class="document-actions"><span class="status-label">Projet non approuvé</span><button type="button" id="print-document" class="print-button" hidden>Imprimer</button></div></div><article class="document-content" id="document">${content}</article><footer class="document-footer"><span>Fonds d’unité du 9 EG · 5422</span><a href="https://mess.9eg.ca">Mess</a><a href="concordance.html">Comparaison avec le 34 RGC</a><a href="historique.html">Historique</a><a href="https://github.com/shocktubeM81/fonds-unite-9eg">Dépôt GitHub</a></footer></main></div><button id="toc-toggle" class="toc-toggle" type="button" aria-controls="sidebar" aria-expanded="false" hidden>☰ Sommaire</button></body></html>`;
  await writeFile(join(output, file), html);
}
// Vérifier que tous les liens et fichiers locaux des pages produites existent.
const { access } = await import('node:fs/promises');
for (const [file] of pages) {
  const html = await readFile(join(output, file), 'utf8');
  if ((html.match(/<h1[ >]/g) || []).length !== 1) throw new Error(`${file}: titre principal invalide`);
  for (const match of html.matchAll(/(?:href|src)="([^"#]+)"/g)) {
    const link = match[1];
    if (/^(?:[a-z]+:|\/\/)/i.test(link)) continue;
    await access(resolve(output, link.split('#')[0].split('?')[0]));
  }
}
console.log(`${pages.length} pages construites; liens et ressources locales vérifiés.`);
