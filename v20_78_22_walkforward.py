"""V20.78.22 leakage-safe walk-forward validation."""
VERSION="V20.78.22"
def walk_forward(rows, predictor, min_train=20):
 rows=sorted(rows,key=lambda r:(r.get("Date",r.get("date","")),r.get("Time",r.get("time",""))))
 out=[]
 for i in range(min_train,len(rows)):
  train=rows[:i]; test=rows[i]; pred=predictor(train,test)
  out.append({"index":i,"prediction":pred,"actual":test.get("FTR") or test.get("result")})
 return out
def brier_binary(items):
 xs=[((1 if str(x["actual"]).upper() in {"H","W","1","WIN"} else 0)-float(x["prediction"]))**2 for x in items if x.get("actual") is not None]
 return sum(xs)/len(xs) if xs else None
