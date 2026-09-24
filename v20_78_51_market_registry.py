"""Hard source-market registry for V20.78.51.
Only markets/lines explicitly present in the submitted source are eligible.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Tuple

def _line(x):
    if x is None: return None
    try: return float(x)
    except (TypeError, ValueError): return str(x).strip()

def normalize_market(m: Dict[str, Any]) -> Dict[str, Any]:
    market=str(m.get('market','')).strip().upper().replace('OVER/UNDER','O/U').replace('OU','O/U')
    sel=str(m.get('selection','')).strip()
    return {'market':market,'selection':sel,'line':_line(m.get('line')),'odds':m.get('odds')}

def registry(visible: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, Any], Dict[str, Any]]:
    out={}
    for raw in visible:
        m=normalize_market(raw)
        if not m['market'] or not m['selection']: continue
        key=(m['market'],m['line'])
        out.setdefault(key, {'market':m['market'],'line':m['line'],'selections':[]})
        out[key]['selections'].append({'selection':m['selection'],'odds':m['odds']})
    return out

def is_visible(candidate: Dict[str, Any], reg: Dict[Tuple[str, Any], Dict[str, Any]]) -> bool:
    m=normalize_market(candidate)
    key=(m['market'],m['line'])
    block=reg.get(key)
    if not block: return False
    return any(str(x['selection']).lower()==m['selection'].lower() for x in block['selections'])

def lock_candidates(candidates: Iterable[Dict[str, Any]], visible: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reg=registry(visible); out=[]
    for c in candidates:
        if is_visible(c,reg):
            x=dict(c); x['source_market_locked']=True; out.append(x)
        else:
            x=dict(c); x['source_market_locked']=False; x['status']='MARKET_NOT_AVAILABLE_IN_SOURCE'
    return out
