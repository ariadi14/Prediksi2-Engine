"""V20.78.52 Data Acquisition -> Evidence/Data Quality bridge."""
from __future__ import annotations
from typing import Any, Dict

VALID_STATUS={"LIVE","CACHED","FALLBACK","PARTIAL","MISSING"}

def build_quality_bridge(acquisition: Dict[str,Any]) -> Dict[str,Any]:
    meta=acquisition.get("acquisition_meta",{}) or {}
    fields={}
    live=cached=fallback=missing=0
    for field, m in meta.items():
        status=str((m or {}).get("status","MISSING")).upper()
        if status not in VALID_STATUS: status="MISSING"
        fields[field]={"status":status,"source":(m or {}).get("source")}
        live += status=="LIVE"; cached += status=="CACHED"; fallback += status=="FALLBACK"; missing += status=="MISSING"
    total=len(fields)
    available=live+cached+fallback
    completeness=(available/total) if total else 0.0
    status="AVAILABLE" if completeness>=0.75 else "PARTIAL" if available else "MISSING"
    return {"status":status,"completeness":round(completeness,4),"fields":fields,"counts":{"live":live,"cached":cached,"fallback":fallback,"missing":missing},"no_data_is_not_negative":True}
