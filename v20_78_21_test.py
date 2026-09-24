from v20_78_21_probability_stress import stress
r=stress({"home":.4,"draw":.3,"away":.3}); assert r["sum_ok"] and abs(sum(r["base"].values())-100)<1e-6
print("V20.78.21 TEST PASS")
