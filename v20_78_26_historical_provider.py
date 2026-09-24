"""Historical evidence fallback for V20.78.27.
Uses only completed rows before the fixture date when a date is known.
This is explicitly marked HISTORICAL_ONLY; it never masquerades as live data.
"""
from __future__ import annotations
import os,re
from typing import Any,Dict
import pandas as pd

class HistoricalEvidenceProvider:
    name='historical-football-data'
    def __init__(self,path=None,window=80):
        self.path=path or os.getenv('FOOTBALL_DATA_CSV')
        self.window=window; self.df=None; self._team_index={}
        if self.path and os.path.exists(self.path):
            try:
                self.df=pd.read_csv(self.path,low_memory=False)
                self.df['Date']=pd.to_datetime(self.df['Date'],errors='coerce')
                for col in ('HomeTeam','AwayTeam'):
                    for team in self.df[col].astype(str).unique(): self._team_index.setdefault(self._n(team),[]).append(team)
            except Exception: self.df=None
    @staticmethod
    def _n(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower())
    def _team_rows(self,team, before=None):
        if self.df is None:return self.df
        t=self._n(team)
        aliases=self._team_index.get(t,[])
        if not aliases:
            return self.df.iloc[0:0].copy()
        h=self.df['HomeTeam'].astype(str).isin(aliases)
        a=self.df['AwayTeam'].astype(str).isin(aliases)
        d=self.df.loc[h|a].copy()
        if before is not None and not pd.isna(before): d=d[d['Date']<before]
        d=d.sort_values(['Date','Time'],na_position='first').tail(self.window)
        return d
    def _stats(self,team,before=None):
        d=self._team_rows(team,before)
        if d is None or len(d)==0:return None
        tn=self._n(team); gf=[]; ga=[]; wins=draws=0
        for _,r in d.iterrows():
            try:
                hg=float(r['FTHG']); ag=float(r['FTAG'])
            except: continue
            if self._n(r['HomeTeam'])==tn: f,g=hg,ag
            else: f,g=ag,hg
            gf.append(f); ga.append(g)
            if f>g:wins+=1
            elif f==g:draws+=1
        if not gf:return None
        return {'matches':len(gf),'gf':sum(gf)/len(gf),'ga':sum(ga)/len(ga),'win_rate':wins/len(gf),'draw_rate':draws/len(gf)}
    def fetch(self,fixture:Dict[str,Any]):
        out={'provider':self.name,'evidence_status':'MISSING'}
        home_name=fixture.get('home_canonical') or fixture.get('home')
        away_name=fixture.get('away_canonical') or fixture.get('away')
        if self.df is None:return out
        before=None
        if fixture.get('match_date'):
            before=pd.to_datetime(fixture['match_date'],errors='coerce')
        h=self._stats(home_name,before); a=self._stats(away_name,before)
        if not h or not a:return out
        # Historical goal averages are used as a conservative expected-goals proxy.
        home_xg=max(0.15,min(4.5,0.62*h['gf']+0.38*a['ga']))
        away_xg=max(0.15,min(4.5,0.62*a['gf']+0.38*h['ga']))
        total=h['matches']+a['matches']
        out.update({'home_xg':home_xg,'away_xg':away_xg,
                    'form_home_prob':max(0.05,min(0.95,(h['win_rate']+0.5*h['draw_rate'])/(1.0+0.0))),
                    'evidence_status':'HISTORICAL_ONLY','historical_matches':total,
                    'evidence_sources':['historical-football-data']})
        out['evidence_quality']=min(0.65,0.25+0.40*min(1,total/100))
        return out
