from v20_78_22_walkforward import walk_forward
rows=[{"Date":f"2020-01-{i:02d}","FTR":"H"} for i in range(1,26)]
r=walk_forward(rows,lambda tr,te: .5,min_train=20); assert len(r)==5
print("V20.78.22 TEST PASS")
