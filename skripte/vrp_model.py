"""Ucitavanje ulaznih podataka i formiranje modela CVRPTW za PyVRP 0.12.2.

Ulazni podaci:
  podaci/konfiguracija.json         skladiste, vozila, radno vreme, pauza
  podaci/OptimoRoute_porudzbine.xlsx kupci (isti fajl koji je uvezen u OptimoRoute)
  podaci/matrica.json               udaljenosti i vremena voznje (matrica_udaljenosti.py)

Vreme se u modelu meri u sekundama od pocetka radnog vremena.
Lokacija 0 je skladiste, lokacije 1..n su kupci redom iz Excel fajla.
"""
import json
from pathlib import Path

import openpyxl
from pyvrp import Model

KOREN = Path(__file__).resolve().parent.parent   # folder PyVRP
PODACI = KOREN / "podaci"
REZULTATI = KOREN / "rezultati"


def u_sekunde(hh_mm):
    """'10:30' -> 37800 (sekundi od ponoci)."""
    h, m = str(hh_mm).split(":")[:2]
    return int(h) * 3600 + int(m) * 60


def ucitaj_konfiguraciju():
    with open(PODACI / "konfiguracija.json", encoding="utf-8") as f:
        return json.load(f)


def ucitaj_porudzbine(konf):
    """Cita kupce iz Excel fajla u formatu za uvoz u OptimoRoute."""
    ws = openpyxl.load_workbook(PODACI / konf["porudzbine"], data_only=True).active
    redovi = ws.iter_rows(values_only=True)
    zaglavlje = [str(k).strip() for k in next(redovi)]
    kupci = []
    for red in redovi:
        if not any(red):
            continue
        r = dict(zip(zaglavlje, red))
        kupci.append({
            "id": int(r["Order ID"]),
            "naziv": r["Location Name"],
            "adresa": r["Address"],
            "istovar_min": int(r["Duration"]),
            "kolicina": int(r["Load"]),
            "prozor": (r["Time Window Start"], r["Time Window End"])
            if r["Time Window Start"] else None,
        })
    return kupci


def ucitaj_matricu():
    with open(PODACI / "matrica.json", encoding="utf-8") as f:
        return json.load(f)


def napravi_model(konf, kupci, mat):
    pocetak = u_sekunde(konf["radno_vreme"]["od"])
    kraj = u_sekunde(konf["radno_vreme"]["do"]) - pocetak
    lat, lon = zip(*mat["koordinate"])

    m = Model()
    depo = m.add_depot(x=lon[0], y=lat[0], tw_early=0, tw_late=kraj,
                       name=konf["skladiste"]["naziv"])
    m.add_vehicle_type(num_available=konf["vozila"]["broj"],
                       capacity=konf["vozila"]["kapacitet_kg"],
                       start_depot=depo, end_depot=depo,
                       tw_early=0, tw_late=kraj,
                       start_late=0)   # svi vozaci krecu na pocetku radnog vremena
    for i, k in enumerate(kupci, start=1):
        a, b = (0, kraj)
        if k["prozor"]:
            a = u_sekunde(k["prozor"][0]) - pocetak
            b = u_sekunde(k["prozor"][1]) - pocetak
        m.add_client(x=lon[i], y=lat[i], delivery=k["kolicina"],
                     service_duration=k["istovar_min"] * 60,
                     tw_early=a, tw_late=b, name=k["naziv"])
    for i, frm in enumerate(m.locations):
        for j, to in enumerate(m.locations):
            m.add_edge(frm, to, distance=mat["distanca_m"][i][j],
                       duration=mat["vreme_s"][i][j])
    return m


def sat(konf, s):
    """Sekunde od pocetka radnog vremena -> 'HH:MM'."""
    s = int(s) + u_sekunde(konf["radno_vreme"]["od"])
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def duzina_rute(mat, lokacije):
    """Duzina rute (m) skladiste -> lokacije -> skladiste prema matrici."""
    put = [0] + list(lokacije) + [0]
    return sum(mat["distanca_m"][a][b] for a, b in zip(put, put[1:]))


def slobodno_za_pauzu(konf, route):
    """Slobodno vreme vozaca (s) u intervalu predvidjenom za pauzu.

    Zauzeto je vreme od polaska do povratka, osim cekanja na vremenski prozor.
    """
    pocetak = u_sekunde(konf["radno_vreme"]["od"])
    od = u_sekunde(konf["pauza"]["od"]) - pocetak
    do = u_sekunde(konf["pauza"]["do"]) - pocetak

    def preklop(a, b):
        return max(0, min(b, do) - max(a, od))

    zauzeto = preklop(route.start_time(), route.end_time())
    for v in route.schedule():
        zauzeto -= preklop(v.start_service - v.wait_duration, v.start_service)
    return (do - od) - zauzeto
