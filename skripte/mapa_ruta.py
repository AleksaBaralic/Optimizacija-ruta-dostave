"""Crtanje ruta na mapi Portlanda (OpenStreetMap), po ulicama kojima vozi kamion.

Pravi dve mape istog izgleda:
  rezultati/mapa_ruta_ga.html           rute genetskog algoritma (rezultati/resenje_ga.json)
  rezultati/mapa_ruta_optimoroute.html  rute OptimoRoute, Scenario 1 (konfiguracija.json)
Geometrija puta se preuzima sa OpenRouteService (profil iz konfiguracije, driving-hgv).
Pre ove skripte treba pokrenuti resavanje_ga.py.
"""
import json
import os
import webbrowser

import folium
import requests
from dotenv import load_dotenv

from vrp_model import (KOREN, REZULTATI, duzina_rute, ucitaj_konfiguraciju,
                       ucitaj_matricu, ucitaj_porudzbine)

BOJE = ["#2b6cd4", "#d63b3b", "#2f9e44"]   # plava, crvena, zelena (kao u OptimoRoute)


def geometrija(koordinate, profil, kljuc):
    """Put po ulicama kroz zadate tacke -> lista (lat, lon)."""
    r = requests.post(f"https://api.openrouteservice.org/v2/directions/{profil}/geojson",
                      json={"coordinates": [[lon, lat] for lat, lon in koordinate]},
                      headers={"Authorization": kljuc}, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Greska OpenRouteService ({r.status_code}): {r.text}")
    return [(lat, lon) for lon, lat in r.json()["features"][0]["geometry"]["coordinates"]]


def marker(mapa, lat, lon, tekst, boja, velicina=24):
    html = (f'<div style="background:{boja};color:white;border:2px solid white;'
            f'border-radius:50%;width:{velicina}px;height:{velicina}px;line-height:{velicina - 4}px;'
            f'text-align:center;font:bold 12px Arial;box-shadow:0 0 3px #555">{tekst}</div>')
    folium.Marker((lat, lon), icon=folium.DivIcon(html=html, icon_size=(velicina, velicina),
                                                  icon_anchor=(velicina // 2, velicina // 2))
                  ).add_to(mapa)


def uskladi_boje(rute, referentne):
    """Svakoj ruti dodeljuje boju referentne rute sa kojom deli najvise kupaca,
    da bi se mape GA i OptimoRoute lakse poredile."""
    slobodne = list(range(len(referentne)))
    boje = [None] * len(rute)
    parovi = sorted(((len(set(r) & set(referentne[j])), i, j)
                     for i, r in enumerate(rute) for j in range(len(referentne))), reverse=True)
    for _, i, j in parovi:
        if boje[i] is None and j in slobodne:
            boje[i] = j
            slobodne.remove(j)
    for i in range(len(rute)):
        if boje[i] is None:
            boje[i] = slobodne.pop(0)
    return [rute[i] for i in sorted(range(len(rute)), key=lambda i: boje[i])]


def nacrtaj(naslov, rute, mat, profil, kljuc, fajl):
    """rute: lista lista indeksa lokacija (1..n), bez skladista; boje redom plava, crvena, zelena."""
    koord = mat["koordinate"]
    mapa = folium.Map(location=koord[0], zoom_start=14, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors",
        name="Esri World Street Map").add_to(mapa)
    granice = []
    legenda = ""
    for k, ruta in enumerate(rute):
        boja = BOJE[k % len(BOJE)]
        put = geometrija([koord[i] for i in [0] + ruta + [0]], profil, kljuc)
        folium.PolyLine(put, color=boja, weight=5, opacity=0.85).add_to(mapa)
        granice += put
        for redni, i in enumerate(ruta, start=1):
            marker(mapa, *koord[i], redni, boja)
        km = duzina_rute(mat, ruta) / 1000
        legenda += (f'<div><span style="display:inline-block;width:14px;height:14px;'
                    f'background:{boja};margin-right:6px"></span>'
                    f'Возило {k + 1}: {len(ruta)} купца, {f"{km:.2f}".replace(".", ",")} km</div>')
    marker(mapa, *koord[0], "S", "#222222", velicina=28)
    ukupno = sum(duzina_rute(mat, r) for r in rute) / 1000
    mapa.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;top:12px;right:12px;z-index:9999;background:white;'
        f'padding:10px 14px;border-radius:6px;box-shadow:0 0 6px #888;font:14px Arial">'
        f'<b>{naslov}</b><br>Укупно: {f"{ukupno:.2f}".replace(".", ",")} km'
        f'<hr style="margin:6px 0">{legenda}'
        f'<div style="margin-top:4px">S = складиште, бројеви = редослед обиласка</div></div>'))
    mapa.fit_bounds(granice, padding=(30, 30))
    REZULTATI.mkdir(exist_ok=True)
    mapa.save(REZULTATI / fajl)
    print(f"Sacuvano: rezultati/{fajl}  ({ukupno:.2f} km)")
    return REZULTATI / fajl


if __name__ == "__main__":
    load_dotenv(KOREN / ".env")
    kljuc = os.getenv("ORS_API_KEY", "").strip()
    if not kljuc:
        raise SystemExit("API kljuc nije pronadjen. U fajl .env upisi: ORS_API_KEY=tvoj_kljuc")

    konf = ucitaj_konfiguraciju()
    kupci = ucitaj_porudzbine(konf)
    mat = ucitaj_matricu()
    profil = mat["profil"]
    with open(REZULTATI / "resenje_ga.json", encoding="utf-8") as f:
        ga = json.load(f)

    id_u_lokaciju = {k["id"]: i for i, k in enumerate(kupci, start=1)}
    optimo = [[id_u_lokaciju[i] for i in r["redosled"]]
              for r in konf["optimoroute_scenario1"].values()]

    f1 = nacrtaj("Генетски алгоритам", uskladi_boje(ga["rute"], optimo), mat, profil, kljuc, "mapa_ruta_ga.html")
    f2 = nacrtaj("OptimoRoute – Сценарио 1 (иста матрица)", optimo, mat, profil, kljuc,
                 "mapa_ruta_optimoroute.html")
    for f in (f1, f2):
        webbrowser.open(f.resolve().as_uri())
