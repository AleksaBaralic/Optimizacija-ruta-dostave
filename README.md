# Primena genetskog algoritma (GA) u optimizaciji ruta dostave

Softverski deo seminarskog rada iz predmeta *Algoritmi i tehnike modelovanja*
(MAS Informacione tehnologije, FTN Čačak).

Problem rutiranja vozila sa kapacitetom i vremenskim prozorima (CVRPTW) za
10 kupaca u Portlandu rešava se genetskim algoritmom iz biblioteke PyVRP 0.12.2,
a rezultat se poredi sa rešenjem alata OptimoRoute.

## Struktura

```
PyVRP/
├── skripte/
│   ├── vrp_model.py             ucitavanje podataka i matematicki model
│   ├── matrica_udaljenosti.py   preuzimanje udaljenosti za kamion (OpenRouteService)
│   └── resavanje_ga.py          resavanje genetskim algoritmom i poredjenje
├── podaci/
│   ├── konfiguracija.json       skladiste, vozila, radno vreme, pauza
│   ├── OptimoRoute_porudzbine.xlsx  kupci (isti fajl kao u OptimoRoute)
│   └── matrica.json / .csv      matrica udaljenosti (pravi je skripta)
├── rezultati/                   grafici
├── requirements.txt
└── README.md
```

## Pokretanje

```
pip install -r requirements.txt
napraviti fajl .env sa redom ORS_API_KEY=kljuc  (besplatan kljuc: openrouteservice.org)
python skripte/matrica_udaljenosti.py
python skripte/resavanje_ga.py
```
