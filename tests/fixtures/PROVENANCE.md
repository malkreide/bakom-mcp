# Herkunft der Fixtures

Aufgezeichnet am **2026-08-15** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

Eine Antwort je **Abfrage**, nicht je Endpunkt: dieser Server spricht mit vier
Hosts, aber in einem Dutzend Abfrageformen. Vier Dateien wuerden die
Portfolio-Regel erfuellen und fast nichts belegen.

Die Antworten stammen aus dem echten Lifespan-Client (gleicher User-Agent,
gleiches Timeout, gleiche Egress-Allowlist wie im Betrieb), abgegriffen ueber
einen httpx-Response-Hook. Neu gesetzt ist die Einrueckung; gekuerzt ist, wo
unten vermerkt, allein die **Zahl** der Trefferzeilen. Kein Feld einer
behaltenen Zeile ist angetastet, und `count` steht wie geliefert — CKAN meldet
dort die Gesamtzahl der Treffer, nicht die Zahl der gelieferten Zeilen.

Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.
Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.

## `breitband_100.json`

- **Werkzeug:** `bakom_broadband_coverage`
- **Eingabe:** `{'latitude': 47.3769, 'longitude': 8.5417, 'min_speed_mbps': '100'}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.downlink100&QUERY_LAYERS=ch.bakom.downlink100&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2683104.0346262627%2C1247725.5974930264%2C2683504.0346262627%2C1248125.5974930264`
- **Auswahl:** ungekuerzt
- **Groesse:** 647 Bytes
- **SHA-256:** `ab2a0fd5509d5bd72d08548607d2ca15661797ee0d25eb83bf8e1764668fd8b9`

## `glasfaser.json`

- **Werkzeug:** `bakom_glasfaser_verfuegbarkeit`
- **Eingabe:** `{'latitude': 47.3769, 'longitude': 8.5417}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.anschlussart-glasfaser&QUERY_LAYERS=ch.bakom.anschlussart-glasfaser&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2683104.0346262627%2C1247725.5974930264%2C2683504.0346262627%2C1248125.5974930264`
- **Auswahl:** ungekuerzt
- **Groesse:** 658 Bytes
- **SHA-256:** `798f146b18bf5cd0c29d35637aac7aed35a16c09fe186c5ee3d7d7b2d2412036`

## `mobilfunk_5g.json`

- **Werkzeug:** `bakom_mobilfunk_abdeckung`
- **Eingabe:** `{'latitude': 47.3769, 'longitude': 8.5417, 'generation': '5G'}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.mobilnetz-5g&QUERY_LAYERS=ch.bakom.mobilnetz-5g&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2683104.0346262627%2C1247725.5974930264%2C2683504.0346262627%2C1248125.5974930264`
- **Auswahl:** ungekuerzt
- **Groesse:** 638 Bytes
- **SHA-256:** `4c8f4f79cc0584ee73e6dd27c23bb804c145f01c9c5b4ca139b84a8770d5dfd3`

## `multi_standort_1.json`

- **Werkzeug:** `bakom_multi_standort_konnektivitaet`
- **Eingabe:** `{'locations': [{'name': 'Zürich HB', 'latitude': 47.3769, 'longitude': 8.5417}, {'name': 'Grimsel', 'latitude': 46.561, 'longitude': 8.337}]}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.mobilnetz-5g&QUERY_LAYERS=ch.bakom.mobilnetz-5g&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2683104.0346262627%2C1247725.5974930264%2C2683504.0346262627%2C1248125.5974930264`
- **Auswahl:** ungekuerzt
- **Hinweis:** Zwei Standorte, je zwei Layer — Reihenfolge: ZH-5G, ZH-Glasfaser, Grimsel-5G, Grimsel-Glasfaser.
- **Groesse:** 638 Bytes
- **SHA-256:** `4c8f4f79cc0584ee73e6dd27c23bb804c145f01c9c5b4ca139b84a8770d5dfd3`

## `multi_standort_2.json`

- **Werkzeug:** `bakom_multi_standort_konnektivitaet`
- **Eingabe:** `{'locations': [{'name': 'Zürich HB', 'latitude': 47.3769, 'longitude': 8.5417}, {'name': 'Grimsel', 'latitude': 46.561, 'longitude': 8.337}]}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.anschlussart-glasfaser&QUERY_LAYERS=ch.bakom.anschlussart-glasfaser&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2683104.0346262627%2C1247725.5974930264%2C2683504.0346262627%2C1248125.5974930264`
- **Auswahl:** ungekuerzt
- **Hinweis:** Zwei Standorte, je zwei Layer — Reihenfolge: ZH-5G, ZH-Glasfaser, Grimsel-5G, Grimsel-Glasfaser.
- **Groesse:** 658 Bytes
- **SHA-256:** `798f146b18bf5cd0c29d35637aac7aed35a16c09fe186c5ee3d7d7b2d2412036`

## `multi_standort_3.json`

- **Werkzeug:** `bakom_multi_standort_konnektivitaet`
- **Eingabe:** `{'locations': [{'name': 'Zürich HB', 'latitude': 47.3769, 'longitude': 8.5417}, {'name': 'Grimsel', 'latitude': 46.561, 'longitude': 8.337}]}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.mobilnetz-5g&QUERY_LAYERS=ch.bakom.mobilnetz-5g&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2668683.881436072%2C1156829.1322718845%2C2669083.881436072%2C1157229.1322718845`
- **Auswahl:** ungekuerzt
- **Hinweis:** Zwei Standorte, je zwei Layer — Reihenfolge: ZH-5G, ZH-Glasfaser, Grimsel-5G, Grimsel-Glasfaser.
- **Groesse:** 638 Bytes
- **SHA-256:** `a9ccfcbbe5af55ce0f896b7ce9f676520b4587effdccb3562b3a830c4a5fa8e0`

## `multi_standort_4.json`

- **Werkzeug:** `bakom_multi_standort_konnektivitaet`
- **Eingabe:** `{'locations': [{'name': 'Zürich HB', 'latitude': 47.3769, 'longitude': 8.5417}, {'name': 'Grimsel', 'latitude': 46.561, 'longitude': 8.337}]}`
- **URL:** `https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=ch.bakom.anschlussart-glasfaser&QUERY_LAYERS=ch.bakom.anschlussart-glasfaser&INFO_FORMAT=application%2Fjson&I=500&J=500&WIDTH=1000&HEIGHT=1000&CRS=EPSG%3A2056&BBOX=2668683.881436072%2C1156829.1322718845%2C2669083.881436072%2C1157229.1322718845`
- **Auswahl:** ungekuerzt
- **Hinweis:** Zwei Standorte, je zwei Layer — Reihenfolge: ZH-5G, ZH-Glasfaser, Grimsel-5G, Grimsel-Glasfaser.
- **Groesse:** 239 Bytes
- **SHA-256:** `b20bdd93108d67973b0d49502993dbcce98a7cc96da5d991440ab6d53e24c5a6`

## `sendeanlagen.json`

- **Werkzeug:** `bakom_sendeanlagen_suche`
- **Eingabe:** `{'latitude': 47.3769, 'longitude': 8.5417, 'radius_m': 1000}`
- **URL:** `https://api3.geo.admin.ch/rest/services/api/MapServer/identify?geometry=2682304.0346262627%2C1246925.5974930264%2C2684304.0346262627%2C1248925.5974930264&geometryType=esriGeometryEnvelope&imageDisplay=1000%2C1000%2C96&mapExtent=2682304.0346262627%2C1246925.5974930264%2C2684304.0346262627%2C1248925.5974930264&tolerance=10&layers=all%3Ach.bakom.standorte-mobilfunkanlagen&sr=2056&returnGeometry=true&lang=de`
- **Auswahl:** die ersten 5 von 201 Zeilen in `results`, aus 297451 Bytes Rohantwort
- **Groesse:** 9825 Bytes
- **SHA-256:** `744b3ed2cab475d57e8f3746f9e67ba3c8f74a960cb62f34b69c805368955a7a`

## `frequenzdaten.json`

- **Werkzeug:** `bakom_frequenzdaten`
- **Eingabe:** `{'latitude': 47.3769, 'longitude': 8.5417}`
- **URL:** `https://api3.geo.admin.ch/rest/services/api/MapServer/identify?geometry=2681304.0346262627%2C1245925.5974930264%2C2685304.0346262627%2C1249925.5974930264&geometryType=esriGeometryEnvelope&imageDisplay=1000%2C1000%2C96&mapExtent=2681304.0346262627%2C1245925.5974930264%2C2685304.0346262627%2C1249925.5974930264&tolerance=10&layers=all%3Ach.bakom.radio-fernsehsender&sr=2056&returnGeometry=false&lang=de`
- **Auswahl:** die ersten 1 von 1 Zeilen in `results`, aus 442 Bytes Rohantwort
- **Groesse:** 559 Bytes
- **SHA-256:** `e4b4f5ce08aba9bddcafff349e911a668fc4c5ec7dddaa40d15dc152d0f92f32`

## `rtv_suche.json`

- **Werkzeug:** `bakom_rtv_suche`
- **Eingabe:** `{'query': 'SRF', 'limit': 5}`
- **URL:** `https://ckan.opendata.swiss/api/3/action/package_search?fq=organization%3Abundesamt-fur-kommunikation-bakom&q=rtv+radio+fernsehen+SRF&rows=5`
- **Auswahl:** die ersten 3 von 5 Zeilen in `result.results`, aus 88141 Bytes Rohantwort
- **Groesse:** 63977 Bytes
- **SHA-256:** `ea379832a6805e28d2be8352115f05cae858a9994fc9055dd8a425e3510acb68`

## `medienstruktur.json`

- **Werkzeug:** `bakom_medienstruktur_info`
- **Eingabe:** `{'thema': 'medien'}`
- **URL:** `https://ckan.opendata.swiss/api/3/action/package_search?fq=organization%3Abundesamt-fur-kommunikation-bakom&q=medien&rows=10&sort=metadata_modified+desc`
- **Auswahl:** die ersten 3 von 10 Zeilen in `result.results`, aus 177229 Bytes Rohantwort
- **Groesse:** 69454 Bytes
- **SHA-256:** `4813fd6f09766f99c3d2d8a905b5d64180cbbfc26d2085c33a0df658074e69bc`

## `aktuell.json`

- **Werkzeug:** `bakom_aktuell`
- **Eingabe:** `{'thema': 'medien'}`
- **URL:** `https://ckan.opendata.swiss/api/3/action/package_search?fq=organization%3Abundesamt-fur-kommunikation-bakom&q=medien&rows=20&sort=metadata_modified+desc`
- **Auswahl:** die ersten 3 von 20 Zeilen in `result.results`, aus 339192 Bytes Rohantwort
- **Groesse:** 69454 Bytes
- **SHA-256:** `4813fd6f09766f99c3d2d8a905b5d64180cbbfc26d2085c33a0df658074e69bc`

## `telekomstatistik.json`

- **Werkzeug:** `bakom_telekomstatistik_uebersicht`
- **Eingabe:** `{'thema': 'breitband'}`
- **URL:** `https://ckan.opendata.swiss/api/3/action/package_search?fq=organization%3Abundesamt-fur-kommunikation-bakom&q=breitband&rows=10&sort=score+desc%2C+metadata_modified+desc`
- **Auswahl:** die ersten 1 von 1 Zeilen in `result.results`, aus 12708 Bytes Rohantwort
- **Groesse:** 15313 Bytes
- **SHA-256:** `cd63687ae674d64779d21193934a5fdb0e1e42f2c4cf05ea3ca4a9645c05f395`

## `medien_katalog.json`

- **Werkzeug:** `bakom_medien_statistik`
- **Eingabe:** `{}`
- **URL:** `https://lindas.admin.ch/query`
- **Rumpf:** `query=%0A++++++++++++++++PREFIX+schema%3A+%3Chttp%3A%2F%2Fschema.org%2F%3E%0A++++++++++++++++SELECT+%3Fname+%28MAX%28%3Fv%29+AS+%3Fversion%29+%28SAMPLE%28%3Fcube%29+AS+%3Fany%29+FROM+%3Chttps%3A%2F%2Flindas.admin.ch%2Fofcom%2Fcube%3E+WHERE+%7B%0A++++++++++++++++++%3Fcube+a+%3Chttps%3A%2F%2Fcube.link%2FCube%3E+%3B+schema%3Aname+%3Fname+%3B+schema%3Aversion+%3Fv+%3B%0A++++++++++++++++++++++++schema%3AcreativeWorkStatus+%3Chttps%3A%2F%2Fld.admin.ch%2Fvocabulary%2FCreativeWorkStatus%2FPublished%3E+.%0A++++++++++++++++++FILTER%28LANG%28%3Fname%29+%3D+%22de%22%29%0A++++++++++++++++++%0A++++++++++++++++%7D+GROUP+BY+%3Fname+ORDER+BY+%3Fname%0A++++++++++++++++`
- **Auswahl:** ungekuerzt
- **Hinweis:** Der Katalog aller veroeffentlichten BAKOM-Cubes. Ungekuerzt — der Server zaehlt die Titel, eine gekuerzte Liste zaehlte falsch.
- **Groesse:** 34947 Bytes
- **SHA-256:** `e75fd0fecbda40885598f74f0e15cad95d7a88c9d3ee15456870691bbe26ae74`

## `medien_auswertung_1.json`

- **Werkzeug:** `bakom_medien_statistik`
- **Eingabe:** `{'thema': 'Meinungsmacht von Medienkonzernen', 'limit': 10}`
- **URL:** `https://lindas.admin.ch/query`
- **Rumpf:** `query=%0A++++++++++++++++PREFIX+schema%3A+%3Chttp%3A%2F%2Fschema.org%2F%3E%0A++++++++++++++++SELECT+%3Fname+%28MAX%28%3Fv%29+AS+%3Fversion%29+%28SAMPLE%28%3Fcube%29+AS+%3Fany%29+FROM+%3Chttps%3A%2F%2Flindas.admin.ch%2Fofcom%2Fcube%3E+WHERE+%7B%0A++++++++++++++++++%3Fcube+a+%3Chttps%3A%2F%2Fcube.link%2FCube%3E+%3B+schema%3Aname+%3Fname+%3B+schema%3Aversion+%3Fv+%3B%0A++++++++++++++++++++++++schema%3AcreativeWorkStatus+%3Chttps%3A%2F%2Fld.admin.ch%2Fvocabulary%2FCreativeWorkStatus%2FPublished%3E+.%0A++++++++++++++++++FILTER%28LANG%28%3Fname%29+%3D+%22de%22%29%0A++++++++++++++++++FILTER%28CONTAINS%28LCASE%28STR%28%3Fname%29%29%2C+LCASE%28%22Meinungsmacht+von+Medienkonzernen%22%29%29%29%0A++++++++++++++++%7D+GROUP+BY+%3Fname+ORDER+BY+%3Fname%0A++++++++++++++++`
- **Auswahl:** ungekuerzt
- **Hinweis:** Reihenfolge: Titelsuche, Dimensionen des Cubes, Beobachtungen.
- **Groesse:** 569 Bytes
- **SHA-256:** `b77bb88b8db3eff8efff149eb9ab234dcf7ec484e180e51bee389723c987a26c`

## `medien_auswertung_2.json`

- **Werkzeug:** `bakom_medien_statistik`
- **Eingabe:** `{'thema': 'Meinungsmacht von Medienkonzernen', 'limit': 10}`
- **URL:** `https://lindas.admin.ch/query`
- **Rumpf:** `query=%0A++++++++++++++++PREFIX+schema%3A+%3Chttp%3A%2F%2Fschema.org%2F%3E%0A++++++++++++++++PREFIX+sh%3A+%3Chttp%3A%2F%2Fwww.w3.org%2Fns%2Fshacl%23%3E%0A++++++++++++++++SELECT+DISTINCT+%3Fpfad+%3Fdname+FROM+%3Chttps%3A%2F%2Flindas.admin.ch%2Fofcom%2Fcube%3E+WHERE+%7B%0A++++++++++++++++++%3Fcube+a+%3Chttps%3A%2F%2Fcube.link%2FCube%3E+%3B+schema%3Aname+%22Meinungsmacht+von+Medienkonzernen%22%40de+%3B%0A++++++++++++++++++++++++schema%3Aversion+6+%3B%0A++++++++++++++++++++++++%3Chttps%3A%2F%2Fcube.link%2FobservationConstraint%3E%2Fsh%3Aproperty+%3Fp+.%0A++++++++++++++++++%3Fp+sh%3Apath+%3Fpfad+%3B+schema%3Aname+%3Fdname+.%0A++++++++++++++++++FILTER%28LANG%28%3Fdname%29+%3D+%22de%22%29%0A++++++++++++++++%7D%0A++++++++++++++++`
- **Auswahl:** ungekuerzt
- **Hinweis:** Reihenfolge: Titelsuche, Dimensionen des Cubes, Beobachtungen.
- **Groesse:** 928 Bytes
- **SHA-256:** `8deb3afdeff0d8cfd9939eab69ec66c014012713dff6f1f6747edf6f0be401d2`

## `medien_auswertung_3.json`

- **Werkzeug:** `bakom_medien_statistik`
- **Eingabe:** `{'thema': 'Meinungsmacht von Medienkonzernen', 'limit': 10}`
- **URL:** `https://lindas.admin.ch/query`
- **Rumpf:** `query=%0A++++++++++++++++PREFIX+schema%3A+%3Chttp%3A%2F%2Fschema.org%2F%3E%0A++++++++++++++++SELECT+%3Fo+%3Fp+%3Fv+%3Fvlabel+FROM+%3Chttps%3A%2F%2Flindas.admin.ch%2Fofcom%2Fcube%3E+WHERE+%7B%0A++++++++++++++++++%7B%0A++++++++++++++++++++SELECT+%3Fo+WHERE+%7B%0A++++++++++++++++++++++%3Fcube+a+%3Chttps%3A%2F%2Fcube.link%2FCube%3E+%3B+schema%3Aname+%22Meinungsmacht+von+Medienkonzernen%22%40de+%3B%0A++++++++++++++++++++++++++++schema%3Aversion+6+%3B%0A++++++++++++++++++++++++++++%3Chttps%3A%2F%2Fcube.link%2FobservationSet%3E%2F%3Chttps%3A%2F%2Fcube.link%2Fobservation%3E+%3Fo+.%0A++++++++++++++++++++++%3Fo+schema%3AobservationDate+%3Fjahr+.%0A++++++++++++++++++++++%0A++++++++++++++++++++%7D+ORDER+BY+DESC%28%3Fjahr%29+LIMIT+10%0A++++++++++++++++++%7D%0A++++++++++++++++++%3Fo+%3Fp+%3Fv+.%0A++++++++++++++++++OPTIONAL+%7B+%3Fv+schema%3Aname+%3Fvlabel+FILTER%28LANG%28%3Fvlabel%29+%3D+%22de%22%29+%7D%0A++++++++++++++++%7D%0A++++++++++++++++`
- **Auswahl:** ungekuerzt
- **Hinweis:** Reihenfolge: Titelsuche, Dimensionen des Cubes, Beobachtungen.
- **Groesse:** 24770 Bytes
- **SHA-256:** `755fa46d7f999c3b5f3759de2d2bef7198fd660243969ed6c54e4d007f4482f4`
