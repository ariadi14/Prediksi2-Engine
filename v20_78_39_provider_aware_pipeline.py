"""V20.78.39 provider-aware Team ID -> Fixture ID -> Evidence pipeline.
No fabricated live data. A deterministic mock provider is available only for integration tests.
"""
from __future__ import annotations
from typing import Any, Dict
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from v20_78_34_provider_connection import ProviderConnection
from v20_78_35_fixture_validation import validate_fixture
from v20_78_36_evidence_retrieval import EvidenceService
from v20_78_37_probability_activation import ProbabilityActivation
from v20_78_28_team_identity import norm_name


class ProviderAwarePipeline:
    VERSION='V20.78.39'

    def __init__(self, connection=None):
        self.connection=connection or ProviderConnection()
        self.providers=self.connection.providers
        self.ev=EvidenceService(self.providers)
        self.prob=ProbabilityActivation()

    @staticmethod
    def _fallback_team_identity(provider, name):
        """Resolve OCR-noisy team names without inventing an identity.

        The original resolver required a high absolute score before trying a
        fixture. Screenshot OCR can lower that score even when the correct
        provider team is obvious. We therefore use the provider's candidate
        search, rank candidates by normalized similarity, and require both a
        reasonable score and a clear margin over the runner-up.
        """
        fn=getattr(provider,'search_teams',None)
        if not fn or not name:
            return None
        try:
            rows=fn(name) or []
        except Exception:
            return None
        scored=[]
        q=norm_name(name)
        for row in rows:
            candidate=row.get('name')
            if not candidate:
                continue
            score=max(
                fuzz.ratio(q,norm_name(candidate)),
                fuzz.WRatio(q,norm_name(candidate)),
            )
            scored.append((float(score),row))
        if not scored:
            return None
        scored.sort(key=lambda x:x[0], reverse=True)
        score,row=scored[0]
        second=scored[1][0] if len(scored)>1 else 0.0
        if score < 70.0 or (len(scored)>1 and score-second < 8.0):
            return None
        return {
            'status':'RESOLVED_FALLBACK',
            'raw':name,
            'canonical_name':row.get('name'),
            'score':round(score,1),
            'second_score':round(second,1),
            'provider_ids':row.get('provider_ids') or {},
            'country':row.get('country'),
        }

    def resolve_identity(self, fixture: Dict[str,Any]):
        out=dict(fixture)
        for side in ('home','away'):
            name=out.get(f'{side}_canonical') or out.get(side)
            if not name:
                continue
            best=None
            for p in self.providers:
                fn=getattr(p,'resolve_team',None)
                if not fn:
                    continue
                try:
                    r=fn(name)
                except Exception as e:
                    r={'status':'UNRESOLVED','reason':str(e)[:160]}
                if r.get('status') in ('RESOLVED_HIGH','RESOLVED_MEDIUM'):
                    best=r
                    break
                fallback=self._fallback_team_identity(p,name)
                if fallback and (best is None or fallback.get('score',0) > best.get('score',0)):
                    best=fallback
                elif best is None:
                    best=r
            if best:
                out[f'{side}_identity']=best
                if best.get('canonical_name'):
                    out[f'{side}_canonical']=best['canonical_name']
                if best.get('provider_ids'):
                    out[f'{side}_provider_ids']=best['provider_ids']
        return out

    @staticmethod
    def _fixture_date_candidates(fixture: Dict[str, Any]):
        """Return safe date probes for screenshots whose date was unreadable."""
        base = str(fixture.get('match_date') or '').strip()
        if not base or not fixture.get('match_date_inferred'):
            return [base]
        try:
            d = datetime.strptime(base, '%Y-%m-%d').date()
        except ValueError:
            return [base]
        return [(d + timedelta(days=delta)).isoformat() for delta in (0, 1, 2, -1)]

    def resolve_fixture(self, fixture: Dict[str,Any]):
        # First try the provider's daily fixture index using the screenshot
        # names directly. This avoids expensive per-team /teams calls and
        # still requires a real provider fixture before acceptance.
        for probe_date in self._fixture_date_candidates(fixture):
            probe = dict(fixture)
            if probe_date:
                probe['match_date'] = probe_date
            for p in self.providers:
                fn=getattr(p,'find_fixture',None)
                if not fn: continue
                try: candidates=fn(dict(probe)) or []
                except Exception: candidates=[]
                for c in candidates:
                    v=validate_fixture(probe,c,min_team=82,min_comp=40)
                    if v.get('status')=='VALID':
                        out=dict(probe)
                        out['fixture_id']=c.get('fixture_id')
                        out['home_canonical']=c.get('home_name')
                        out['away_canonical']=c.get('away_name')
                        out['home_provider_ids']={'api-football': c.get('home_id')} if c.get('home_id') else out.get('home_provider_ids',{})
                        out['away_provider_ids']={'api-football': c.get('away_id')} if c.get('away_id') else out.get('away_provider_ids',{})
                        out['provider_competition']=c.get('competition')
                        out['kickoff_utc']=c.get('kickoff_utc')
                        out['kickoff_wib']=c.get('kickoff_wib')
                        out['kickoff']=c.get('kickoff_wib') or c.get('kickoff_utc')
                        out['match_date']=c.get('date') or out.get('match_date')
                        out['fixture_date_resolution_mode']='INFERRED_NEARBY_DATE' if probe_date != str(fixture.get('match_date')) else 'EXACT_DATE'
                        return out,v

        # If direct fixture matching fails, use the slower identity resolver
        # as a second path. Unknown remains unresolved.
        f=self.resolve_identity(fixture)
        for probe_date in self._fixture_date_candidates(f):
            probe = dict(f)
            if probe_date:
                probe['match_date'] = probe_date
            for p in self.providers:
                fn=getattr(p,'find_fixture',None)
                if not fn: continue
                try: candidates=fn(probe) or []
                except Exception: candidates=[]
                for c in candidates:
                    v=validate_fixture(probe,c,min_team=82,min_comp=40)
                    if v.get('status')=='VALID':
                        probe['fixture_id']=c.get('fixture_id')
                        probe['home_canonical']=c.get('home_name') or probe.get('home_canonical')
                        probe['away_canonical']=c.get('away_name') or probe.get('away_canonical')
                        probe['provider_competition']=c.get('competition')
                        probe['kickoff_utc']=c.get('kickoff_utc')
                        probe['kickoff_wib']=c.get('kickoff_wib')
                        probe['kickoff']=c.get('kickoff_wib') or c.get('kickoff_utc')
                        probe['match_date']=c.get('date') or probe.get('match_date')
                        probe['fixture_date_resolution_mode']='INFERRED_NEARBY_DATE' if probe_date != str(f.get('match_date')) else 'EXACT_DATE'
                        return probe,v

        # Quota-safe fallback: when API-Football explicitly reports its daily
        # quota exhausted, the screenshot remains the source of fixture identity
        # while the local DB supplies only historical evidence. We do not invent
        # a provider fixture ID; the synthetic local ID is an internal key only.
        quota_exhausted = any(
            bool(getattr(p, '_last_fixture_lookup', {}).get('api_quota_exhausted'))
            for p in self.providers
        )
        if quota_exhausted:
            for p in self.providers:
                if getattr(p, 'name', '') != 'football-local-db':
                    continue
                fetch = getattr(p, 'fetch', None)
                if not fetch:
                    continue
                try:
                    historical = fetch(dict(fixture)) or {}
                except Exception:
                    historical = {}
                if historical.get('historical_db_source'):
                    out = dict(fixture)
                    out['fixture_id'] = (
                        f"local:{fixture.get('match_date')}:{norm_name(fixture.get('home'))}:"
                        f"{norm_name(fixture.get('away'))}"
                    )
                    out['home_canonical'] = fixture.get('home')
                    out['away_canonical'] = fixture.get('away')
                    out['kickoff'] = fixture.get('kickoff') or fixture.get('kickoff_wib')
                    out['provider_competition'] = fixture.get('competition')
                    out['local_historical_evidence_available'] = True
                    out['skip_live_providers'] = True
                    return out, {
                        'status': 'VALID',
                        'match_mode': 'SCREENSHOT_IDENTITY_LOCAL_HISTORY',
                        'provider': 'football-local-db',
                        'reason': 'API_FOOTBALL_DAILY_QUOTA_EXHAUSTED',
                    }

                return f,{'status':'REJECTED','reason':'NO_VALID_PROVIDER_FIXTURE'}

        # Always return a deterministic rejected result when no provider path
        # can resolve the fixture. The previous implementation could fall
        # through without returning a tuple, causing callers that unpack
        # resolve_fixture() to crash with "cannot unpack non-iterable NoneType".
        return f, {'status': 'REJECTED', 'reason': 'NO_VALID_PROVIDER_FIXTURE'}

    def run_fixture(self, fixture: Dict[str,Any]):
        f, validation=self.resolve_fixture(fixture)
        if validation.get('status')!='VALID':
            ev={'status':'MISSING','reason':validation.get('reason')}
        else:
            ev=self.ev.fetch(f)
        pred=self.prob.run('|'.join(str(f.get(k,'')) for k in ('competition','home_canonical','away_canonical','match_date','kickoff')),ev,f.get('markets') or [])
        return {'fixture':f,'validation':validation,'evidence':ev,'prediction':pred}
