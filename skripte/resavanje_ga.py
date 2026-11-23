"""Resavanje CVRPTW genetskim algoritmom (PyVRP 0.12.2) i poredjenje sa
rutama koje je nasao OptimoRoute (Scenario 1), izracunatim nad istom matricom.

Primer pokretanja:  python skripte/resavanje_ga.py --iteracije 3000 --seed 1
Ispis se cuva u rezultati/portland/resenje_ga.txt, a rute u resenje_ga.json.
"""
import argparse
import io
import json
import sys

from pyvrp.stop import MaxIterations

from vrp_model import (REZULTATI, duzina_rute, napravi_model, sat, slobodno_za_pauzu,
                       ucitaj_konfiguraciju, ucitaj_matricu, ucitaj_porudzbine)

arg = argparse.ArgumentParser()
arg.add_argument("--iteracije", type=int, default=3000)
arg.add_argument("--seed", type=int, default=1)
arg = arg.parse_args()


class Dupli:
    """Ispis istovremeno na ekran i u memoriju (za cuvanje u fajl)."""
    def __init__(self, *tokovi):
        self.tokovi = tokovi

    def write(self, t):
        for tok in self.tokovi:
            tok.write(t)

    def flush(self):
        for tok in self.tokovi:
            tok.flush()


IZLAZ = io.StringIO()
sys.stdout = Dupli(sys.__stdout__, IZLAZ)

konf = ucitaj_konfiguraciju()
kupci = ucitaj_porudzbine(konf)
mat = ucitaj_matricu()
naz = mat["nazivi"]
id_u_lokaciju = {k["id"]: i for i, k in enumerate(kupci, start=1)}
pauza = konf["pauza"]["trajanje_min"] * 60

rez = napravi_model(konf, kupci, mat).solve(
    stop=MaxIterations(arg.iteracije), seed=arg.seed, display=False)
best = rez.best

print("=" * 72)
print(f"GENETSKI ALGORITAM - {arg.iteracije} iteracija, seed {arg.seed}, "
      f"vreme {rez.runtime:.2f} s")
print("=" * 72)
print(f"Profil vozila:      {mat['profil']}")
print(f"Resenje izvodljivo: {'DA' if best.is_feasible() else 'NE'}")
print(f"Ukupna distanca:    {best.distance() / 1000:.2f} km\n")
for k, r in enumerate(best.routes(), start=1):
    t = r.duration()
    print(f"Vozilo {k}: {len(r.visits())} kupaca, {r.distance() / 1000:.2f} km, "
          f"polazak {sat(konf, r.start_time())}, povratak {sat(konf, r.end_time())}, "
          f"trajanje {t // 3600} h {t % 3600 // 60:02d} min, "
          f"cekanje {r.wait_duration() // 60} min")
    sl = slobodno_za_pauzu(konf, r)
    print(f"     pauza {konf['pauza']['od']}-{konf['pauza']['do']}: slobodno {sl // 60} min "
          f"-> {'moguca' if sl >= pauza else 'NIJE moguca'}")
    for v in r.schedule():
        if v.location >= 1:
            print(f"     {sat(konf, v.start_service)}  {v.location:>2}  {naz[v.location]}")
print()

# --- Poredjenje sa OptimoRoute (Scenario 1), isti redosled meren istom matricom ---
print("=" * 72)
print(f"POREDJENJE: redosled iz OptimoRoute-a meren istom matricom ({mat['profil']})")
print("=" * 72)
print(f"{'Ruta':<20}{'Redosled kupaca':<18}{'Matrica [km]':>13}{'OptimoRoute [km]':>19}")
uk = uk_or = 0
for ime, ruta in konf["optimoroute_scenario1"].items():
    d = duzina_rute(mat, [id_u_lokaciju[i] for i in ruta["redosled"]]) / 1000
    uk += d
    uk_or += ruta["km"]
    print(f"{ime:<20}{str(ruta['redosled']):<18}{d:>13.2f}{ruta['km']:>19.1f}")
print(f"{'Ukupno':<38}{uk:>13.2f}{uk_or:>19.1f}")
ga_km = best.distance() / 1000
print(f"\nGenetski algoritam:       {ga_km:.2f} km")
print(f"OptimoRoute (ista matr.): {uk:.2f} km")
print(f"Razlika:                  {uk - ga_km:+.2f} km ({(uk - ga_km) / uk * 100:+.1f} %)")

# --- Cuvanje ispisa u fajl ---
REZULTATI.mkdir(parents=True, exist_ok=True)
with open(REZULTATI / "resenje_ga.json", "w", encoding="utf-8") as f:
    json.dump({"distanca_km": round(ga_km, 2),
               "rute": [list(r.visits()) for r in best.routes()],
               "km_po_ruti": [round(r.distance() / 1000, 2) for r in best.routes()]},
              f, indent=1)
with open(REZULTATI / "resenje_ga.txt", "w", encoding="utf-8") as f:
    f.write(IZLAZ.getvalue())
print("\nSacuvano: rezultati/portland/resenje_ga.txt i resenje_ga.json")
