"""Eksperimenti sa genetskim algoritmom (PyVRP 0.12.2).

1) Portland (10 kupaca): 10 pokretanja sa razlicitim seed vrednostima -> stabilnost GA.
2) Solomon RC208 (100 kupaca): konvergencija GA u odnosu na najbolje poznato resenje.
3) Solomon RC208: uticaj velicine populacije i broja iteracija.

Rezultati se cuvaju u folderu rezultati/ (csv tabele i png grafici).
Pokretanje: python skripte/eksperimenti_ga.py   (traje oko 2-3 minuta)
"""
import csv
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyvrp
from pyvrp import read
from pyvrp.stop import MaxIterations

from vrp_model import (PODACI, REZULTATI, napravi_model, ucitaj_konfiguraciju,
                       ucitaj_matricu, ucitaj_porudzbine)

SEEDOVI = range(1, 11)
REZULTATI.mkdir(exist_ok=True)


def najbolje_po_iteracijama(rez):
    """Najbolja dopustiva vrednost do svake iteracije i iteracija kada je dostignuta."""
    niz, tek, nadjeno = [], float("inf"), 0
    for i, s in enumerate(rez.stats.feas_stats, start=1):
        if s.size > 0 and s.best_cost < tek:
            tek, nadjeno = s.best_cost, i
        niz.append(tek)
    return niz, nadjeno


def sacuvaj_csv(ime, zaglavlje, redovi):
    with open(REZULTATI / ime, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(zaglavlje)
        w.writerows(redovi)


def zbir(vrednosti):
    return min(vrednosti), st.mean(vrednosti), max(vrednosti), st.pstdev(vrednosti)


# ---------------------------------------------------------------------------
print("=" * 72)
print("1) PORTLAND - 10 pokretanja GA (3000 iteracija, razliciti seed)")
print("=" * 72)
konf = ucitaj_konfiguraciju()
kupci = ucitaj_porudzbine(konf)
mat = ucitaj_matricu()
model = napravi_model(konf, kupci, mat)

redovi = []
print(f"{'Seed':>4}{'Distanca [km]':>16}{'Iteracija resenja':>20}{'Vreme [s]':>12}")
for seed in SEEDOVI:
    rez = model.solve(stop=MaxIterations(3000), seed=seed, display=False)
    _, it = najbolje_po_iteracijama(rez)
    km = rez.best.distance() / 1000
    redovi.append([seed, f"{km:.2f}", it, f"{rez.runtime:.2f}"])
    print(f"{seed:>4}{km:>16.2f}{it:>20}{rez.runtime:>12.2f}")
km = [float(r[1]) for r in redovi]
mn, avg, mx, sd = zbir(km)
print(f"Najbolje {mn:.2f} km | prosek {avg:.2f} km | najgore {mx:.2f} km | "
      f"st. devijacija {sd:.2f} km")
sacuvaj_csv("portland_10_pokretanja.csv",
            ["seed", "distanca_km", "iteracija_resenja", "vreme_s"], redovi)

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("2) SOLOMON RC208 (100 kupaca) - konvergencija GA")
print("=" * 72)
data = read(PODACI / "RC208.vrp", round_func="dimacs")   # distance x10, kao u DIMACS
with open(PODACI / "RC208.sol", encoding="utf-8") as f:
    BKS = float([l for l in f if l.startswith("Cost")][0].split()[1])
print(f"Najbolje poznato resenje (BKS): {BKS:.1f}")

ITER_KONV = 3000
plt.figure(figsize=(8, 4.5))
for seed, boja in zip([1, 2, 3], ["#1f4e79", "#c0504d", "#4f8f3a"]):
    rez = pyvrp.solve(data, MaxIterations(ITER_KONV), seed=seed)
    niz, it = najbolje_po_iteracijama(rez)
    niz = [v / 10 for v in niz]
    pocetak = next(v for v in niz if v < float("inf"))
    print(f"seed {seed}: prvo dopustivo {pocetak:.1f} -> najbolje {niz[-1]:.1f} "
          f"(iteracija {it}, odstupanje od BKS {(niz[-1] - BKS) / BKS * 100:.2f} %)")
    plt.plot(range(1, len(niz) + 1), [v if v < float("inf") else None for v in niz],
             color=boja, lw=1.8, label=f"Покретање {seed}")
plt.axhline(BKS, color="black", ls="--", lw=1, label=f"Најбоље познато решење ({BKS:.1f})".replace(".", ","))
plt.xscale("log")
plt.ylim(BKS * 0.98, BKS * 1.25)
plt.xlabel("Итерација (генерација), логаритамска скала")
plt.ylabel("Укупна дистанца")
plt.title("Конвергенција генетског алгоритма – Solomon RC208")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(REZULTATI / "konvergencija_rc208.png", dpi=200)

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("3) SOLOMON RC208 - uticaj parametara (10 pokretanja po varijanti)")
print("=" * 72)

POPULACIJE = [5, 25, 100]          # min_pop_size (podrazumevano 25)
ITER_POP = 300
print(f"a) Velicina populacije (min_pop_size), {ITER_POP} iteracija")
print(f"{'Populacija':>10}{'Najbolje':>10}{'Prosek':>10}{'Najgore':>10}{'Odst. [%]':>11}")
red_pop, prosek_pop = [], []
for mp in POPULACIJE:
    par = pyvrp.SolveParams(population=pyvrp.PopulationParams(min_pop_size=mp))
    v = [pyvrp.solve(data, MaxIterations(ITER_POP), seed=s, params=par).cost() / 10
         for s in SEEDOVI]
    mn, avg, mx, sd = zbir(v)
    prosek_pop.append(avg)
    red_pop.append([mp, f"{mn:.1f}", f"{avg:.1f}", f"{mx:.1f}", f"{(avg - BKS) / BKS * 100:.2f}"])
    print(f"{mp:>10}{mn:>10.1f}{avg:>10.1f}{mx:>10.1f}{(avg - BKS) / BKS * 100:>11.2f}")
sacuvaj_csv("rc208_velicina_populacije.csv",
            ["min_pop_size", "najbolje", "prosek", "najgore", "odstupanje_proseka_od_BKS_%"],
            red_pop)

ITERACIJE = [100, 300, 1000, 3000]
print("\nb) Broj iteracija (podrazumevani parametri)")
print(f"{'Iteracije':>10}{'Najbolje':>10}{'Prosek':>10}{'Najgore':>10}{'Odst. [%]':>11}{'Vreme [s]':>11}")
red_it, prosek_it = [], []
for n in ITERACIJE:
    rr = [pyvrp.solve(data, MaxIterations(n), seed=s, collect_stats=False) for s in SEEDOVI]
    v = [r.cost() / 10 for r in rr]
    t = st.mean(r.runtime for r in rr)
    mn, avg, mx, sd = zbir(v)
    prosek_it.append(avg)
    red_it.append([n, f"{mn:.1f}", f"{avg:.1f}", f"{mx:.1f}", f"{(avg - BKS) / BKS * 100:.2f}", f"{t:.2f}"])
    print(f"{n:>10}{mn:>10.1f}{avg:>10.1f}{mx:>10.1f}{(avg - BKS) / BKS * 100:>11.2f}{t:>11.2f}")
sacuvaj_csv("rc208_broj_iteracija.csv",
            ["iteracije", "najbolje", "prosek", "najgore", "odstupanje_proseka_od_BKS_%", "vreme_s"],
            red_it)

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].bar([str(p) for p in POPULACIJE], [(a - BKS) / BKS * 100 for a in prosek_pop], color="#1f4e79")
ax[0].set_xlabel("Минимална величина популације")
ax[0].set_ylabel("Просечно одступање од BKS [%]")
ax[0].set_title(f"Утицај величине популације ({ITER_POP} итерација)")
ax[1].plot([str(n) for n in ITERACIJE], [(a - BKS) / BKS * 100 for a in prosek_it],
           "-o", color="#1f4e79", lw=2)
ax[1].set_xlabel("Број итерација")
ax[1].set_title("Утицај броја итерација")
for a in ax:
    a.grid(alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig(REZULTATI / "parametri_rc208.png", dpi=200)

print("\nSacuvano u rezultati/: portland_10_pokretanja.csv, konvergencija_rc208.png,")
print("rc208_velicina_populacije.csv, rc208_broj_iteracija.csv, parametri_rc208.png")
