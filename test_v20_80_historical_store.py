from v20_80_historical_store import HistoricalMatchStore

def test_monthly_import_is_additive_and_deduplicated(tmp_path):
    csv1 = tmp_path / "a.csv"
    csv1.write_text(
        "Date,Div,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "2026-09-01,E0,Alpha,Bravo,2,1\n"
        "2026-09-02,E1,Charlie,Delta,0,0\n",
        encoding="utf-8",
    )
    csv2 = tmp_path / "b.csv"
    csv2.write_text(
        "Date,Div,HomeTeam,AwayTeam,FTHG,FTAG,HomeXG,AwayXG\n"
        "2026-09-01,E0,Alpha,Bravo,2,1,1.7,0.8\n"
        "2026-09-03,E0,Echo,Foxtrot,1,3,0.9,1.8\n",
        encoding="utf-8",
    )

    db = tmp_path / "history.sqlite"
    store = HistoricalMatchStore(str(db))
    try:
        first = store.import_csv(str(csv1), "source-a")
        second = store.import_csv(str(csv2), "source-b")
        assert first["inserted"] == 2
        assert second["inserted"] == 1
        assert second["updated"] == 1
        assert store.count() == 3
        row = [x for x in store.recent(10) if x["home_team"] == "Alpha"][0]
        assert row["home_xg"] == 1.7
        assert row["away_xg"] == 0.8
    finally:
        store.close()

def test_invalid_rows_are_rejected(tmp_path):
    csv1 = tmp_path / "bad.csv"
    csv1.write_text(
        "Date,HomeTeam,AwayTeam\n"
        ",Alpha,Bravo\n"
        "2026-09-01,Charlie,Delta\n",
        encoding="utf-8",
    )
    store = HistoricalMatchStore(str(tmp_path / "history.sqlite"))
    try:
        result = store.import_csv(str(csv1))
        assert result["invalid"] == 1
        assert result["inserted"] == 1
        assert store.count() == 1
    finally:
        store.close()
