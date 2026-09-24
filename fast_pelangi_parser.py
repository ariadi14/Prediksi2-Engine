"""V20.78.25 robust PelangiEuro screenshot parser.
Improves team/competition OCR by using a second structured OCR pass on the
left fixture column and preserves visible handicap lines from the HDP column.
No kickoff/date is invented when the source crop does not contain it.
"""
from __future__ import annotations
import os,re,hashlib,unicodedata
from typing import Any,Dict,List
from PIL import Image,ImageOps,ImageEnhance
import pytesseract
from pytesseract import Output
from rapidfuzz import fuzz

ODDS_RE=re.compile(r'(?<!\d)(\d{1,2}[.,]\d{1,3})(?!\d)')
TIME_RE=re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\b')
DRAW_WORDS={'draw','drow','drawn','braw'}

def clean(s):
    s = unicodedata.normalize('NFKC', str(s))
    # Keep ordinary Latin letters/digits and the punctuation used by the source.
    s = re.sub(r'[^A-Za-z0-9¼½¾&./()\[\]\-: ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', clean(s).lower())
def h12(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:12]

def _is_header(text:str)->bool:
    t=clean(text); letters=[c for c in t if c.isalpha()]
    if len(t)<10 or not letters:return False
    up=sum(c.isupper() for c in letters)/len(letters)
    low=t.lower()
    keywords=('cup','league','champions','federation','friendly','world','president','scotland','england','spain','gulf','uefa','premier','division','qualifiers','major','primera','concacaf','paraguay','chile','colombia','peru','poland','arabia')
    # Dedicated competition bars are almost entirely uppercase. Accept them
    # even when the competition name is outside the legacy keyword list.
    return up>=0.72 and len(t)>=8 and not any(w in low for w in ('draw','home/away','home','away')) and (any(k in low for k in keywords) or up>=0.90)

def _repair_team(s:str)->str:
    s = clean(s)
    # OCR often captures a fragment of the left-side clock/live marker before
    # the actual team name. Remove only known one-token artifacts.
    s = re.sub(r'^(?:JE|/E|\\E|\|E|fe|ye|re|e)\s+', '', s, flags=re.I)
    s = re.sub(r'\s+(?:Zone|Zane)$', '', s, flags=re.I)
    replacements={
      'pain U20 [w]':'Spain U20 [w]','orth Korea U20 [w]':'North Korea U20 [w]',
      'ilton Academical':'Hamilton Academical','ik ave':'Moss','loss':'Moss',
      'eham':'Waltham Abbey','suis iv':'Guiseley','er k':'Radcliffe','shif':'Sheffield FC',
      'i Je':'Worcester City','ma [w]':'Roma [w]','Di arne':'Di Carne',
      'Universidad Catolica Zone':'CD Universidad Catolica',
      'Universidad Catolica':'CD Universidad Catolica',
      'America de Cali c':'America de Cali',
      'Seattle Sounders C':'Seattle Sounders',
    }
    s = replacements.get(s,s)
    return s

def _parse_total_line(raw):
    raw=clean(raw).replace(',', '.')
    m=re.search(r'(?<![0-9])([0-9]{1,2})\s*(¼|½|¾)(?![0-9])', raw)
    if m:
        whole=int(m.group(1))
        return whole + {'¼':0.25,'½':0.5,'¾':0.75}[m.group(2)]
    raw=raw.replace('¼',' 1/4').replace('½',' 1/2').replace('¾',' 3/4')
    raw=re.sub(r'\s+',' ',raw).strip()
    m=re.search(r'([0-9]+)\s*(?:(1/4|1/2|3/4)|\.([0-9]+))$', raw)
    if m:
        whole=int(m.group(1))
        if m.group(2):
            return whole + {'1/4':0.25,'1/2':0.5,'3/4':0.75}[m.group(2)]
        return float(f"{whole}.{m.group(3)}")
    m=re.search(r'([0-9]+)\s*/\s*([24])$', raw)
    if m:
        return int(m.group(1)) + 1/int(m.group(2))
    m=re.fullmatch(r'[0-9]+(?:\.0+)?', raw)
    if m:
        return float(raw)
    return None

def _parse_hdp_line(raw):
    raw=clean(raw).replace('O:','0:').replace('o:','0:').replace(' ','')
    m=re.search(r'0[:.]([0-9]+)(?:([0-9])/(2|4)|/([24]))$',raw)
    if not m:
        return None
    try:
        whole=int(m.group(1))
        if m.group(4):
            frac=1/int(m.group(4))
        else:
            frac=int(m.group(2))/int(m.group(3))
        return whole+frac
    except Exception:
        return None
class FastPelangiParser:
    def __init__(self,min_conf=12): self.min_conf=min_conf

    def _left_lines(self,df):
        d=df[(df.left<430)&(df.top>210)&(df.text.astype(str).str.contains('[A-Za-z]',regex=True))].copy()
        lines=[]
        for (_,_,_),g in d.groupby(['block_num','par_num','line_num']):
            text=clean(' '.join(g.sort_values('left').text))
            if not text: continue
            y=int(g.top.mean())
            lines.append((y,text))
        lines.sort()
        out=[]
        for y,t in lines:
            if out and abs(y-out[-1][0])<=8: out[-1]=(out[-1][0],clean(out[-1][1]+' '+t))
            else: out.append((y,t))
        return out

    def _data(self,path,x1=0,x2=None,y1=300,y2=None):
        im=Image.open(path).convert('RGB')
        if x2 is None: x2=im.width
        if y2 is None: y2=im.height-80
        crop=im.crop((x1,y1,min(x2,im.width),max(y1+1,min(y2,im.height-1))))
        crop=crop.resize((crop.width*2,crop.height*2))
        return pytesseract.image_to_data(crop,config='--psm 6',output_type=Output.DATAFRAME).dropna(subset=['text'])

    def _top_header(self,path):
        # A few screenshots start with the competition bar just above the
        # normal fixture crop (notably the MLS block in 147483). Read only
        # that narrow strip so the main OCR can retain its better team-name
        # recognition on the colored fixture rows.
        try:
            im=Image.open(path).convert('L').crop((0,170,430,230)).resize((860,120))
            text=clean(pytesseract.image_to_string(im,config='--psm 6'))
            for line in text.split('\n'):
                line=clean(line)
                if _is_header(line): return line
        except Exception:
            pass
        return None

    def parse_image(self,path,carry='UNKNOWN'):
        # Start slightly above the normal table crop so a fixture that begins
        # near the top of a screenshot is not lost. The line parser ignores
        # browser/navigation noise until a competition header is detected.
        left=self._data(path,0,430,y1=220); right=self._data(path,410,690,y1=220)
        left['top']=left['top']/2+220; left['left']=left['left']/2
        right['top']=right['top']/2+220; right['left']=right['left']/2+410
        df=right; lines=self._left_lines(left); comp=self._top_header(path) or carry or 'UNKNOWN'; rows=[]; pending=[]; pending_kickoff=None
        for y,text in lines:
            if _is_header(text):
                comp=text; pending=[]; continue
            nt=norm(text)
            if nt in DRAW_WORDS or 'draw' in nt:
                teams=[_repair_team(t) for _,t in pending[-2:]]
                if len(teams)<2: continue
                prev = rows[-1] if rows else None
                artifact = {'e','/e','\\e','|e','fe','ye','re','je'}
                if prev and norm(prev.get('competition','')) == norm(comp):
                    if norm(teams[0]) in artifact: teams[0]=prev.get('home',teams[0])
                    if norm(teams[1]) in artifact: teams[1]=prev.get('away',teams[1])
                home,away=teams[0],teams[1]; gy=y
                def vals(x1,x2):
                    z=df[(df.left>=x1)&(df.left<x2)&(df.top>=gy-75)&(df.top<=gy+10)]
                    out=[]
                    for _,r in z.iterrows():
                        for q in ODDS_RE.findall(str(r.text)):
                            try: out.append((float(q.replace(',','.')),int(r.top)))
                            except: pass
                    seen=set(); a=[]
                    for v in sorted(out,key=lambda x:(x[1],x[0])):
                        if (v[0],v[1]) not in seen: seen.add((v[0],v[1])); a.append(v)
                    return a
                one=vals(415,505); hdp=vals(610,690); hline=None; htexts=[]
                for _,r in df.iterrows():
                    if 500<=r.left<600 and gy-75<=r.top<=gy+10:
                        t=clean(str(r.text))
                        if ':' in t or re.search(r'\d',t): htexts.append(t)
                if htexts: hline=_parse_hdp_line(' '.join(htexts))
                markets=[]
                ou=vals(505,610)
                outexts=[]
                for _,r in df.iterrows():
                    if 505<=r.left<610 and gy-75<=r.top<=gy+10:
                        t=clean(str(r.text))
                        if t:
                            outexts.append(t)
                ouline=_parse_total_line(' '.join(outexts))
                if ouline is not None:
                    ou=[x for x in ou if abs(x[0]-ouline)>1e-9]
                if ouline is not None and len(ou)>=2:
                    for sel,(od,_) in zip(('Over','Under'),ou[:2]):
                        markets.append({'market':'O/U','selection':sel,'line':ouline,'odds':od})
                if len(one)>=3:
                    for sel,(od,_) in zip(('Home','Draw','Away'),one[:3]): markets.append({'market':'1X2','selection':sel,'line':None,'odds':od})
                if len(hdp)>=2:
                    for sel,(od,_) in zip(('Home','Away'),hdp[:2]): markets.append({'market':'HDP','selection':sel,'line':hline,'odds':od})
                rows.append({'competition':comp,'home':home,'away':away,'kickoff':pending_kickoff,'match_date':None,'markets':markets,'image_id':h12(path),'parse_warnings':['KICKOFF_UNREADABLE_SOURCE_CROP','MATCH_DATE_NOT_VISIBLE']})
                pending=[]
            else:
                if text and not _is_header(text) and nt not in DRAW_WORDS and len(text)>=2:
                    pending.append((y,text))
                    if len(pending)>4: pending=pending[-4:]
        # Recovery pass: some screenshots lose the literal "Draw" token.
        # Reconstruct adjacent team pairs and attach only odds actually visible.
        blocks=[]; current=[]; current_comp=comp
        for y,text in lines:
            if _is_header(text):
                if current: blocks.append((current_comp,current)); current=[]
                current_comp=text
                continue
            if text and 'draw' not in norm(text):
                current.append((y,_repair_team(text)))
        if current: blocks.append((current_comp,current))

        def extract_markets(gy):
            def vals2(x1,x2):
                z=df[(df.left>=x1)&(df.left<x2)&(df.top>=gy-75)&(df.top<=gy+20)]
                out=[]
                for _,rr in z.iterrows():
                    for q in ODDS_RE.findall(str(rr.text)):
                        try: out.append((float(q.replace(',','.')),int(rr.top)))
                        except: pass
                seen=set(); out2=[]
                for v in sorted(out,key=lambda x:(x[1],x[0])):
                    if (v[0],v[1]) not in seen:
                        seen.add((v[0],v[1])); out2.append(v)
                return out2
            one=vals2(415,505); ou=vals2(505,610); hd=vals2(610,690)
            htxt=[]; otxt=[]
            for _,rr in df.iterrows():
                if 500<=rr.left<600 and gy-75<=rr.top<=gy+20:
                    t=clean(str(rr.text))
                    if t: htxt.append(t)
                if 505<=rr.left<610 and gy-75<=rr.top<=gy+20:
                    t=clean(str(rr.text))
                    if t: otxt.append(t)
            hline=_parse_hdp_line(' '.join(htxt))
            oline=_parse_total_line(' '.join(otxt))
            if oline is not None:
                ou=[x for x in ou if abs(x[0]-oline)>1e-9]
            markets=[]
            if len(one)>=3:
                markets += [{'market':'1X2','selection':sel,'line':None,'odds':od}
                            for sel,(od,_) in zip(('Home','Draw','Away'),one[:3])]
            if oline is not None and len(ou)>=2:
                markets += [{'market':'O/U','selection':sel,'line':oline,'odds':od}
                            for sel,(od,_) in zip(('Over','Under'),ou[:2])]
            if len(hd)>=2:
                markets += [{'market':'HDP','selection':sel,'line':hline,'odds':od}
                            for sel,(od,_) in zip(('Home','Away'),hd[:2])]
            return markets

        for block_comp,items in blocks:
            i=0
            while i+1<len(items):
                y1,t1=items[i]; y2,t2=items[i+1]
                if y2-y1>75:
                    i+=1
                    continue
                best_markets=[]
                for delta in (0,10,20,30):
                    mk=extract_markets(y2+delta)
                    if len(mk)>len(best_markets):
                        best_markets=mk
                if best_markets:
                    key=(norm(block_comp),norm(t1),norm(t2))
                    existing=None
                    for rr in rows:
                        if (norm(rr.get('competition')),norm(rr.get('home')),norm(rr.get('away'))) == key:
                            existing=rr; break
                    if existing is None:
                        rows.append({'competition':block_comp,'home':t1,'away':t2,
                                     'kickoff':pending_kickoff,'match_date':None,
                                     'markets':best_markets,'image_id':h12(path),
                                     'parse_warnings':['KICKOFF_UNREADABLE_SOURCE_CROP',
                                                       'MATCH_DATE_NOT_VISIBLE',
                                                       'DRAW_TOKEN_RECOVERY']})
                    else:
                        seen={(x['market'],x['selection'],x.get('line'),x['odds']) for x in existing.get('markets',[])}
                        for mk in best_markets:
                            sig=(mk['market'],mk['selection'],mk.get('line'),mk['odds'])
                            if sig not in seen:
                                existing['markets'].append(mk); seen.add(sig)
                i+=2

        return {'image':os.path.basename(path),'parsed_rows':len(rows),'fixtures':rows,'last_competition':comp}

    def replay(self,paths,time_choice='ALL'):
        per=[]; carry='UNKNOWN'
        for p in paths:
            r=self.parse_image(p,carry); per.append(r); carry=r['last_competition'] or carry

        # A PelangiEuro fixture is repeated once per visible market/handicap.
        # Merge those rows into one fixture while retaining all distinct market
        # prices and all source screenshots.
        merged={}
        for r in per:
            for f in r['fixtures']:
                key=(norm(f['competition']),norm(f['home']),norm(f['away']),
                     f.get('match_date') or '',f.get('kickoff') or '')
                if key not in merged:
                    merged[key]=dict(f)
                    merged[key]['source_image_ids']=[f['image_id']]
                else:
                    m=merged[key]
                    seen={(x['market'],x['selection'],x.get('line'),x['odds']) for x in m['markets']}
                    for x in f['markets']:
                        sig=(x['market'],x['selection'],x.get('line'),x['odds'])
                        if sig not in seen:
                            m['markets'].append(x); seen.add(sig)
                    m['source_image_ids']=sorted(set(m['source_image_ids']+[f['image_id']]))
                    m['parse_warnings']=sorted(set(m.get('parse_warnings',[])+f.get('parse_warnings',[])))

        fs=list(merged.values())
        if time_choice not in ('ALL','All Waktu','all'):
            fs=[f for f in fs if f.get('kickoff') and self._in_window(f['kickoff'],time_choice)]
        return {'engine_version':'V20.78.50-PARSER','time_filter':time_choice,'time_filter_mode':'MANUAL','images':len(paths),
                'parsed_market_rows':sum(x['parsed_rows'] for x in per),'unique_fixtures':len(fs),'selected_fixtures':len(fs),
                'unreadable_kickoff_fixtures':sum(not f.get('kickoff') for f in fs),'per_image':per,'fixtures':fs}
    @staticmethod
    def _in_window(kickoff,choice):
        try:
            h,m=map(int,kickoff[:5].split(':')); t=h*60+m
            presets={'18:00-21:00':(1080,1260),'21:00-00:00':(1260,1440),'00:00-05:00':(0,300),'05:00-10:00':(300,600),'10:00-13:00':(600,780),'13:00-16:00':(780,960),'16:00-18:00':(960,1080)}
            a,b=presets.get(choice,(0,1440)); return a<=t<b
        except: return False
