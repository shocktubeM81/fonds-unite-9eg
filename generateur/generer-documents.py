"""Produire un recueil unique depuis la constitution et les annexes du Fonds d'unité."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from sources import load_sources

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[([^]]+)\]\(([^)]+)\)')

def read(path):
    return Path(path).read_text(encoding='utf-8-sig')

def clean_label(text):
    return LINK.sub(lambda m: m[1], text).replace('**', '')

def block_key(line):
    heading = re.match(r'^(#+)\s+(.+)', line)
    if heading:
        num = re.match(r'(\d+)\.', heading[2])
        return 'H:' + (num[1] if num else heading[2])
    para = re.match(r'^(\d+\.\d+)\.\s', line)
    return 'P:' + para[1] if para else 'T:' + line

def split_segments(text, structure):
    lines = text.splitlines()
    headings = [(i,l) for i,l in enumerate(lines) if l.startswith('#')]
    segments = []
    for spec in structure['segments']:
        starts = [i for i,l in headings if l == spec['marker']]
        if len(starts) != 1:
            raise ValueError('Titre manquant ou répété dans le maître: '+spec['marker'])
        start = starts[0]
        level = len(spec['marker'])-len(spec['marker'].lstrip('#'))
        end = next((i for i,l in headings if i>start and len(l)-len(l.lstrip('#'))<=level),len(lines))
        body = lines[start if spec['include_marker'] else start+1:end]
        segments.append((start,end,spec,body))
    return segments

def validate(text, structure):
    if any(x in text for x in ('{%','{{','<a ', '{#')):
        raise ValueError('Le maître ne doit pas contenir de balises HTML ou Jekyll.')
    segments = split_segments(text, structure)
    total=0
    for _,_,spec,body in segments:
        seq={}
        for line in body:
            m=re.match(r'^(\d+)\.(\d+)\.\s',line)
            if m:
                a,b=map(int,m.groups())
                if b!=seq.get(a,0)+1:
                    raise ValueError(f"Numérotation discontinue dans {spec['marker']}: {a}.{b}")
                seq[a]=b;total+=1
    constitution = next(body for _, _, spec, body in segments if spec['source'] == 'constitution-projet.md')
    numbered = [int(m[1]) for line in constitution if (m := re.match(r'^\*\*(\d+)\.\*\*\s', line))]
    if numbered != list(range(1, len(numbered) + 1)):
        raise ValueError('Numérotation discontinue dans la constitution')
    return segments,len(numbered)

def local_heading(line, shift):
    m=re.match(r'^(#+) (.+)',line)
    return '#'*max(1,len(m[1])-shift)+' '+m[2] if m else line

def bookmark_name(value):
    return 'b_'+hashlib.sha1(value.encode('utf-8')).hexdigest()[:28]

def document_blocks(text,segments):
    by_line={}
    for start,end,spec,body in segments:
        offset=start if spec['include_marker'] else start+1
        for i,line in enumerate(body,offset):
            by_line[i]=(spec,spec['anchors'].get(block_key(local_heading(line,spec['shift'])),[]))
    fixed={}
    blocks=[]
    for i,line in enumerate(text.splitlines()):
        line=line.strip()
        if not line:continue
        ids=list(by_line.get(i,(None,[]))[1])
        if line in fixed:ids.append(fixed[line])
        # Seules les anciennes ancres du recueil qui ne changent pas de rôle sont reprises.
        blocks.append({'text':line,'ids':list(dict.fromkeys(ids))})
    known={a for b in blocks for a in b['ids']}
    for b in blocks:
        for m in LINK.finditer(b['text']):
            if m[2].startswith('#') and m[2][1:] not in known:
                raise ValueError('Renvoi interne sans destination: '+m[2])
    return blocks

def add_bold_runs(paragraph, text):
    for i, part in enumerate(re.split(r'\*\*(.*?)\*\*', text)):
        run = paragraph.add_run(part)
        if i % 2:
            run.bold = True


def rendered_blocks(blocks):
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if block['text'].startswith('|'):
            rows = []
            while i < len(blocks) and blocks[i]['text'].startswith('|'):
                cells = [c.strip() for c in blocks[i]['text'].strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            yield dict(text='', ids=[], table=rows)
        else:
            yield block
            i += 1


def add_runs(paragraph,text):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    pos=0
    for m in LINK.finditer(text):
        add_bold_runs(paragraph,text[pos:m.start()])
        link=OxmlElement('w:hyperlink')
        if m[2].startswith('#'):
            link.set(qn('w:anchor'),bookmark_name(m[2][1:]))
        else:
            link.set(qn('r:id'),paragraph.part.relate_to(m[2],RT.HYPERLINK,is_external=True))
        r=OxmlElement('w:r');props=OxmlElement('w:rPr')
        color=OxmlElement('w:color');color.set(qn('w:val'),'000000');props.append(color)
        under=OxmlElement('w:u');under.set(qn('w:val'),'single');props.append(under)
        r.append(props);t=OxmlElement('w:t');t.text=m[1];r.append(t);link.append(r);paragraph._p.append(link)
        pos=m.end()
    add_bold_runs(paragraph,text[pos:])

def make_docx(blocks,profile,target):
    from docx import Document
    from docx.shared import Cm,Pt,RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.section import WD_SECTION_START
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document()
    sec=doc.sections[0];sec.page_width=Cm(21.59);sec.page_height=Cm(27.94)
    for side in ('left','right','top','bottom'):
        french={'left':'gauche','right':'droite','top':'haut','bottom':'bas'}[side]
        setattr(sec,side+'_margin',Cm(profile['marge_'+french+'_cm']))
    for style in doc.styles:
        if style.type==1:
            style.font.name=profile['police'];style.font.color.rgb=RGBColor(0,0,0);style.font.italic=False
            fonts=style._element.get_or_add_rPr().find(qn('w:rFonts'))
            if fonts is not None:
                fonts.attrib.clear()
                for attr in ('ascii','hAnsi','eastAsia','cs'):fonts.set(qn('w:'+attr),profile['police'])
    # Le modèle Word par défaut peut contenir une ligne bleue héritée du style Title.
    for border in list(doc.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    normal=doc.styles['Normal'];normal.font.size=Pt(profile['taille'])
    normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.line_spacing=1
    for n,size in [(1,14),(2,13),(3,12),(4,12)]:
        st=doc.styles['Heading '+str(n)];st.font.size=Pt(size);st.font.bold=True
        st.paragraph_format.space_before=Pt(12);st.paragraph_format.space_after=Pt(7)
        st.paragraph_format.keep_with_next=True
    title=doc.styles['Title'];title.font.name=profile['police'];title.font.size=Pt(17);title.font.bold=True
    title.font.color.rgb=RGBColor(0,0,0)
    p=doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(20)
    logo=ROOT/profile['insigne'] if profile.get('insigne') else None
    if logo and logo.exists():p.add_run().add_picture(str(logo),width=Cm(4.1))
    p=doc.add_paragraph(profile['titre_couverture'],style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(25);p.paragraph_format.space_after=Pt(20)
    for text in (profile['unite'],profile['lieu'],profile['adresse']):
        p=doc.add_paragraph(text);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(9)
    version=next((b['text'] for b in blocks if b['text'].startswith('Version ')),'Projet à adopter et à approuver')
    p=doc.add_paragraph(version);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_before=Pt(30)
    body=doc.add_section(WD_SECTION_START.NEW_PAGE);body.header.is_linked_to_previous=False;body.footer.is_linked_to_previous=False
    num=OxmlElement('w:pgNumType');num.set(qn('w:start'),'1');body._sectPr.append(num)
    p=body.header.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=p.add_run(profile['entete']);run.font.size=Pt(9)
    p=body.footer.paragraphs[0]
    for field in ('PAGE','SECTIONPAGES'):
        if field!='PAGE':p.add_run('/')
        fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),field);p._p.append(fld)
    for n in (1,2):
        name='TOC '+str(n)
        st=doc.styles[name] if name in doc.styles else doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        st.font.name=profile['police'];st.font.size=Pt(12);st.font.color.rgb=RGBColor(0,0,0)
        st.paragraph_format.space_after=Pt(2);st.paragraph_format.line_spacing=1
        st.paragraph_format.keep_with_next=False
        st.paragraph_format.left_indent=Cm(0 if n==1 else 0.6)
        st.paragraph_format.tab_stops.add_tab_stop(Cm(21.59-profile['marge_gauche_cm']-profile['marge_droite_cm']),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
    p=doc.add_paragraph('Table des matières')
    p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(14)
    p.runs[0].bold=True;p.runs[0].font.size=Pt(14)
    p=doc.add_paragraph()
    # Champ Word natif: deux niveaux, numéros de page et liens internes.
    for kind,value in [('begin',None),('instr',' TOC \\o "1-2" \\h \\z \\u '),('separate',None),('text','Table des matières à actualiser dans Word.'),('end',None)]:
        run=OxmlElement('w:r')
        if kind in ('begin','separate','end'):
            node=OxmlElement('w:fldChar');node.set(qn('w:fldCharType'),kind)
        elif kind=='instr':
            node=OxmlElement('w:instrText');node.set(qn('xml:space'),'preserve');node.text=value
        else:node=OxmlElement('w:t');node.text=value
        run.append(node);p._p.append(run)
    bookmark_id=1;first=True;after_part_two=False;signature=False
    for b in rendered_blocks(blocks):
        if 'table' in b:
            rows = b['table']
            table = doc.add_table(rows=0, cols=max(map(len, rows)))
            table.style = 'Table Grid'
            for row in rows:
                cells = table.add_row().cells
                for cell, value in zip(cells, row): add_runs(cell.paragraphs[0], value)
            continue
        line=b['text']
        if line.startswith('# ') or line.startswith('Version '):continue
        h=re.match(r'^(#+) (.+)',line)
        if h:
            level=min(4,len(h[1])-1);text=h[2]
            p=doc.add_paragraph(text,style='Heading '+str(level))
            new_page=(len(h[1])==2) or (len(h[1])==3 and text.startswith(('Règlement ','Annexe ')) and not after_part_two)
            p.paragraph_format.page_break_before=new_page
            after_part_two=text.startswith('Partie II')
            signature='Approbation du commandant' in text
            first=False
        else:
            p=doc.add_paragraph();m=re.match(r'^(\d+\.\d+\.) (.*)',line)
            if m:
                p.paragraph_format.left_indent=Cm(1.1);p.paragraph_format.first_line_indent=Cm(-1.1)
                p.paragraph_format.tab_stops.add_tab_stop(Cm(1.1))
                p.add_run(m[1]+'\t');add_runs(p,m[2])
            else:add_runs(p,line.removeprefix('- '))
            p.paragraph_format.widow_control=True
            if signature and not line.startswith('Signé à'):p.paragraph_format.keep_with_next=True
            after_part_two=False
        for ident in b['ids']:
            start=OxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(bookmark_id));start.set(qn('w:name'),bookmark_name(ident))
            end=OxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(bookmark_id));p._p.insert(0,start);p._p.append(end);bookmark_id+=1
    doc.core_properties.title=clean_label(blocks[0]['text'].lstrip('# '));doc.core_properties.author=profile.get('auteur', profile['unite'])
    doc.save(target)

def reportlab_pdf(blocks,profile,target):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus.tableofcontents import TableOfContents
    class WithContents(SimpleDocTemplate):
        def afterFlowable(self,flowable):
            for ident in getattr(flowable,'_export_anchors',[]):
                exported_anchors[ident]=self.page-1
            entry=getattr(flowable,'_toc_entry',None)
            if entry:
                level,text,key=entry
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text,key,level=level,closed=False)
                self.notify('TOCEntry',(level,html.escape(text),self.page-1,key))
    class Pages(Canvas):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);self.states=[]
        def showPage(self):self.states.append(dict(self.__dict__));self._startPage()
        def save(self):
            count=len(self.states)
            for state in self.states:
                self.__dict__.update(state)
                if self._pageNumber>1:
                    self.setFont('Times-Roman',9);self.drawCentredString(letter[0]/2,letter[1]-1.3*cm,profile['entete'])
                    self.drawString(profile['marge_gauche_cm']*cm,1.2*cm,f'{self._pageNumber-1}/{count-1}')
                super().showPage()
            super().save()
    styles={n:ParagraphStyle(n,fontName='Times-Roman',fontSize=12,leading=14,spaceAfter=7) for n in ['body','ref']}
    for level in range(1,5):styles[str(level)]=ParagraphStyle('h'+str(level),fontName='Times-Bold',fontSize=14 if level==1 else 12,leading=16,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    styles['cover']=ParagraphStyle('cover',fontName='Times-Bold',fontSize=17,leading=24,alignment=TA_CENTER,spaceAfter=18)
    styles['center']=ParagraphStyle('center',fontName='Times-Roman',fontSize=12,leading=16,alignment=TA_CENTER,spaceAfter=10)
    def inline(text):
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html.escape(text))
    def markup(text):
        out=[];pos=0
        for m in LINK.finditer(text):
            out.append(inline(text[pos:m.start()]))
            href=('#'+bookmark_name(m[2][1:])) if m[2].startswith('#') else m[2]
            out.append('<link href="'+html.escape(href,quote=True)+'"><u>'+html.escape(m[1])+'</u></link>');pos=m.end()
        out.append(inline(text[pos:]));return ''.join(out)
    exported_anchors={}
    story=[Spacer(1,20)]
    logo=ROOT/profile['insigne'] if profile.get('insigne') else None
    if logo and logo.exists():
        from PIL import Image as PILImage
        with PILImage.open(logo) as im:w,h=im.size
        story.append(Image(str(logo),width=4.1*cm,height=4.1*cm*h/w))
    story.extend([Spacer(1,25),Paragraph(html.escape(profile['titre_couverture']).replace('\n','<br/>'),styles['cover'])])
    for text in [profile['unite'],profile['lieu'],profile['adresse'],next(b['text'] for b in blocks if b['text'].startswith('Version '))]:story.append(Paragraph(html.escape(text),styles['center']))
    story.append(PageBreak())
    story.append(Paragraph('Table des matières',styles['1']))
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle('toc0',fontName='Times-Roman',fontSize=12,leading=15,spaceAfter=3),ParagraphStyle('toc1',fontName='Times-Roman',fontSize=12,leading=15,leftIndent=0.6*cm,spaceAfter=3)]
    story.extend([toc,PageBreak()]);first=True;after_part_two=False
    for b in rendered_blocks(blocks):
        if 'table' in b:
            rows = [[Paragraph(markup(cell), styles['body']) for cell in row] for row in b['table']]
            columns = max(map(len, rows))
            rows = [row + [''] * (columns - len(row)) for row in rows]
            width = (21.59-profile['marge_gauche_cm']-profile['marge_droite_cm'])*cm
            table = Table(rows, colWidths=[width/columns]*columns, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.4,'black'),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),'#eeeeee')]))
            story.extend([table,Spacer(1,8)])
            continue
        line=b['text'];h=re.match(r'^(#+) (.+)',line)
        if line.startswith('# ') or line.startswith('Version '):continue
        if h:
            title=h[2]
            if (len(h[1])==2 and not first) or (len(h[1])==3 and title.startswith(('Règlement ','Annexe ')) and not after_part_two):story.append(PageBreak())
            style=styles[str(min(4,len(h[1])-1))];line=title;first=False;after_part_two=title.startswith('Partie II')
        else:style=styles['body'];after_part_two=False
        anchor=''.join('<a name="'+bookmark_name(i)+'"/>' for i in b['ids'])
        flow=Paragraph(anchor+markup(line.removeprefix('- ')),style)
        flow._export_anchors=b['ids']
        if h and len(h[1]) in (2,3):flow._toc_entry=(len(h[1])-2,h[2],bookmark_name('toc:'+b['text']))
        story.append(flow)
    doc=WithContents(str(target),pagesize=letter,leftMargin=profile['marge_gauche_cm']*cm,rightMargin=profile['marge_droite_cm']*cm,topMargin=profile['marge_haut_cm']*cm,bottomMargin=profile['marge_bas_cm']*cm,title=clean_label(blocks[0]['text'].lstrip('# ')),author=profile.get('auteur', profile['unite']))
    doc.multiBuild(story,canvasmaker=Pages)
    # Exposer les ancres comme destinations PDF nommées pour les renvois entre fichiers.
    from pypdf import PdfWriter
    writer=PdfWriter(clone_from=str(target))
    for ident,page in exported_anchors.items():
        writer.add_named_destination(bookmark_name(ident),page)
    temporary=target.with_suffix('.pdf.tmp')
    with temporary.open('wb') as stream:writer.write(stream)
    writer.close()
    temporary.replace(target)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--modele',default='9eg',help='Nom du profil JSON dans generateur/modeles, ou chemin du fichier')
    ap.add_argument('--texte-seul',action='store_true',help='Produire seulement la copie TXT')
    ap.add_argument('--docx-seul',action='store_true',help='Produire le Word et la copie TXT sans exporter le PDF')
    ap.add_argument('--pdf-moteur',choices=['auto','word','reportlab'],default='auto')
    ap.add_argument('--sortie',default='exports',help='Dossier de sortie, relatif au projet ou absolu')
    args=ap.parse_args()
    text,structure,sources=load_sources()
    segments,count=validate(text,structure);blocks=document_blocks(text,segments)
    out=Path(args.sortie)
    if not out.is_absolute():out=ROOT/out
    out.mkdir(parents=True,exist_ok=True)
    pp=Path(args.modele)
    if not pp.is_file():pp=ROOT/'generateur/modeles'/(args.modele+'.json')
    profile=json.loads(read(pp))
    jobs=[('constitution-fonds-unite-9eg',profile['titre_couverture'],blocks)]
    results=[]
    for name,title,items in jobs:
        current=dict(profile)
        plain='\n\n'.join(b['text'] for b in items)+'\n'
        plain=LINK.sub(lambda m:m[1]+' ('+m[2]+')' if not m[2].startswith('#') else m[1],plain)
        plain=re.sub(r'^#+\s*','',plain,flags=re.M)
        (out/(name+'.txt')).write_text(plain,encoding='utf-8-sig')
        engine=None;error=None
        if not args.texte_seul:
            docx=out/(name+'.docx');pdf=out/(name+'.pdf')
            make_docx(items,current,docx)
            if not args.docx_seul:
                engine='reportlab'
                if args.pdf_moteur in ('auto','word') and os.name=='nt':
                    try:
                        subprocess.run(['powershell.exe','-NoProfile','-File',str(ROOT/'generateur/exporter-pdf.ps1'),'-Document',str(docx),'-Pdf',str(pdf)],check=True,timeout=90,capture_output=True,text=True)
                        engine='word'
                    except (subprocess.SubprocessError,OSError) as exc:
                        error=str(exc)
                        if isinstance(exc,subprocess.CalledProcessError):error+='\n'+(exc.stderr or '')
                        if args.pdf_moteur=='word':raise RuntimeError('Export PDF Word impossible: '+error) from exc
                if engine=='reportlab':
                    reportlab_pdf(items,current,pdf)
        results.append({'document':name,'pdf_moteur':engine,'word_pdf_erreur':error})
        print('Créé : '+name,flush=True)
    info={'sources':{path:hashlib.sha256(content.encode('utf-8')).hexdigest() for path,content in sources.items()},'sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),'paragraphes':count,'modele':pp.name,'documents':results}
    (out/'generation.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{count} paragraphes vérifiés. {len(jobs)} documents créés dans {out}.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('Erreur:',e,file=sys.stderr);sys.exit(1)
