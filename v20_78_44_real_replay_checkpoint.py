"""V20.78.44 real replay checkpoint report."""
def checkpoint(results):
    return {
      'version':'V20.78.44','screenshots':results.get('screenshots',0),
      'fixtures':results.get('fixtures',0),'fixture_ids':results.get('fixture_ids',0),
      'evidence':results.get('evidence',0),'predictions':results.get('predictions',0),
      'status':'PASS' if results.get('fixture_ids',0)>0 and results.get('evidence',0)>0 and results.get('predictions',0)>0 else 'NOT_PASS'
    }
