"""V20.78.51 final production-candidate gate."""
def gate(code_pass, real_data_verified, historical_pass, stress_pass, calibration_pass, parlay_pass):
    checks={
      "code":bool(code_pass),"real_data":bool(real_data_verified),
      "historical":bool(historical_pass),"stress":bool(stress_pass),
      "calibration":bool(calibration_pass),"parlay":bool(parlay_pass)}
    return {"version":"V20.78.51","checks":checks,"ready":all(checks.values()),
            "status":"PRODUCTION_CANDIDATE" if all(checks.values()) else "NOT_READY"}
