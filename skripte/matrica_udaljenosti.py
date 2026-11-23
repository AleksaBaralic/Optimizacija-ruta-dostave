"""Preuzimanje matrice udaljenosti i vremena voznje za skladiste i sve kupce.

1) Geokodiranje adresa (Nominatim, OpenStreetMap) -> koordinate.
2) Matrica udaljenosti i vremena voznje za profil vozila iz konfiguracije
   (OpenRouteService; driving-hgv = teretno vozilo / kamion).
API kljuc se cita iz promenljive ORS_API_KEY u fajlu .env.
Rezultat: podaci/matrica.json i podaci/matrica_km.csv.
"""
import json
import os
import time

import requests
from dotenv import load_dotenv

from vrp_model import KOREN, PODACI, ucitaj_konfiguraciju, ucitaj_porudzbine

HEADERS = {"User-Agent": "seminarski-rad-FTN-Cacak/1.0"}


def geokodiraj(adresa):
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": adresa, "format": "json", "limit": 1},
                     headers=HEADERS, timeout=30)
    r.raise_for_status()
    rez = r.json()
    if not rez:
        raise SystemExit(f"Adresa nije pronadjena: {adresa}")
    return float(rez[0]["lat"]), float(rez[0]["lon"])


def preuzmi_matricu(koordinate, profil, kljuc):
    r = requests.post(f"https://api.openrouteservice.org/v2/matrix/{profil}",
                      json={"locations": [[lon, lat] for lat, lon in koordinate],
                            "metrics": ["distance", "duration"], "units": "m"},
                      headers={**HEADERS, "Authorization": kljuc}, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Greska OpenRouteService ({r.status_code}): {r.text}")
    odg = r.json()
    if any(v is None for red in odg["distances"] for v in red):
        raise SystemExit("Neka lokacija nije dostupna za izabrani profil vozila.")
    dist = [[round(d) for d in red] for red in odg["distances"]]    # metri
    vreme = [[round(t) for t in red] for red in odg["durations"]]   # sekunde
    return dist, vreme


def ispisi(naslov, mat, delilac):
    print(f"\n{naslov}")
    print("     " + "".join(f"{j:>6}" for j in range(len(mat))))
    for i, red in enumerate(mat):
        print(f"{i:>3}  " + "".join(f"{v / delilac:>6.1f}" for v in red))


if __name__ == "__main__":
    load_dotenv(KOREN / ".env")
    kljuc = os.getenv("ORS_API_KEY", "").strip()
    if not kljuc:
        raise SystemExit("API kljuc nije pronadjen. U fajl .env upisi: ORS_API_KEY=tvoj_kljuc")

    konf = ucitaj_konfiguraciju()
    kupci = ucitaj_porudzbine(konf)
    profil = konf["vozila"]["profil"]
    nazivi = [konf["skladiste"]["naziv"]] + [k["naziv"] for k in kupci]
    adrese = [konf["skladiste"]["adresa"]] + [k["adresa"] for k in kupci]

    print("1) GEOKODIRANJE ADRESA (OpenStreetMap)")
    print(f"{'#':>2}  {'Lokacija':<28}{'lat':>10}{'lon':>12}")
    koordinate = []
    for i, (naziv, adresa) in enumerate(zip(nazivi, adrese)):
        lat, lon = geokodiraj(adresa)
        koordinate.append((lat, lon))
        print(f"{i:>2}  {naziv:<28}{lat:>10.5f}{lon:>12.5f}")
        time.sleep(1.1)  # Nominatim dozvoljava 1 zahtev u sekundi

    print(f"\n2) MATRICA UDALJENOSTI (OpenRouteService, profil {profil})")
    dist, vreme = preuzmi_matricu(koordinate, profil, kljuc)

    with open(PODACI / "matrica.json", "w", encoding="utf-8") as f:
        json.dump({"profil": profil, "nazivi": nazivi, "adrese": adrese,
                   "koordinate": koordinate, "distanca_m": dist, "vreme_s": vreme},
                  f, ensure_ascii=False, indent=1)
    with open(PODACI / "matrica_km.csv", "w", encoding="utf-8") as f:
        f.write("od/do;" + ";".join(str(j) for j in range(len(dist))) + "\n")
        for i, red in enumerate(dist):
            f.write(f"{i};" + ";".join(f"{d / 1000:.2f}".replace(".", ",") for d in red) + "\n")

    ispisi("Udaljenosti [km] (0 = skladiste, 1-10 = kupci):", dist, 1000)
    ispisi("Vreme voznje [min]:", vreme, 60)
    print("\nSacuvano: podaci/matrica.json i podaci/matrica_km.csv")
