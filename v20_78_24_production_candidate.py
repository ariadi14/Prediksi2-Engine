"""V20.78.24 production-candidate gate."""
VERSION="V20.78.24"
def gate(report, syntax_ok=True, integration_ok=True):
 checks={"syntax":bool(syntax_ok),"integration":bool(integration_ok),"report_ready":report.get("report_status")=="READY" if isinstance(report,dict) else False}
 return {"version":VERSION,"checks":checks,"ready":all(checks.values())}
