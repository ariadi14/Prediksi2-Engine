"""V20.78.36 evidence retrieval with provenance and failure isolation.

Evidence is considered ENRICHED only when the provider returned substantive
statistical evidence that can feed the probability engine. A fixture match
object alone is not probability evidence.
"""
from v20_78_3_live_providers import flatten_provider_payload


class EvidenceService:
    def __init__(self, providers):
        self.providers = providers or []

    @staticmethod
    def _usable_probability_evidence(flat):
        """Return True only when both sides have a real-data scoring basis.

        Accepted complete sources mirror the probability engine fallbacks:
        - xG / predicted goals for both sides;
        - home/away scoring + opponent concession averages from season stats;
        - recent form scoring + opponent concession averages.

        Directional percentages (ML/attack/defence) alone are not enough to
        mark the fixture enriched because they do not provide the complete
        expected-goals basis used by the current engine.
        """
        if not isinstance(flat, dict):
            return False

        pair_sources = (
            ('home_xg', 'away_xg'),
            ('home_predicted_goals', 'away_predicted_goals'),
            (
                'home_goals_for_home_avg',
                'home_goals_against_home_avg',
                'away_goals_for_away_avg',
                'away_goals_against_away_avg',
            ),
            (
                'home_recent_goals_for_avg',
                'home_recent_goals_against_avg',
                'away_recent_goals_for_avg',
                'away_recent_goals_against_avg',
            ),
        )
        for keys in pair_sources:
            if all(flat.get(k) is not None for k in keys):
                return True
        return False

    def fetch(self, fixture):
        if not fixture.get('fixture_id'):
            return {'status': 'MISSING', 'reason': 'NO_FIXTURE_ID', 'providers': []}

        attempts = []
        merged = {}
        usable_sources = []

        for p in self.providers:
            name = getattr(p, 'name', p.__class__.__name__)
            if fixture.get('skip_live_providers') and name == 'api-football':
                attempts.append({
                    'provider': name,
                    'ok': False,
                    'errors': ['SKIPPED_AFTER_API_FOOTBALL_DAILY_QUOTA_EXHAUSTED'],
                })
                continue
            try:
                raw = p.fetch(fixture) or {}
                flat = flatten_provider_payload(raw)

                attempts.append({
                    'provider': name,
                    'ok': bool(raw.get('fixture_match') or flat),
                    'errors': raw.get('errors', []),
                    'endpoint_diagnostics': raw.get('endpoint_diagnostics', {}),
                    'recent_form_diagnostics': raw.get('recent_form_diagnostics', {}),
                })

                if raw.get('fixture_match'):
                    merged['fixture_match'] = raw['fixture_match']

                for k, v in flat.items():
                    if v not in (None, {}, []):
                        merged.setdefault(k, v)

                if self._usable_probability_evidence(flat):
                    usable_sources.append(name)

            except Exception as e:
                attempts.append({
                    'provider': name,
                    'ok': False,
                    'errors': [str(e)[:200]],
                })

        if not merged:
            return {
                'status': 'UNAVAILABLE',
                'reason': 'ALL_PROVIDERS_FAILED_OR_EMPTY',
                'providers': attempts,
            }

        # A provider fixture object proves fixture resolution only; it does
        # not prove that probability evidence was retrieved.
        if not self._usable_probability_evidence(merged):
            return {
                'status': 'INSUFFICIENT_DATA',
                'reason': 'NO_USABLE_PROBABILITY_EVIDENCE',
                'providers': attempts,
                'payload': merged,
                'usable_evidence_sources': usable_sources,
            }

        return {
            'status': 'ENRICHED',
            'providers': attempts,
            'payload': merged,
            'usable_evidence_sources': usable_sources,
        }
