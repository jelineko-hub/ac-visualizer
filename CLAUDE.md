# AC Visualizer - Stav projektu

## Posledná session (16.3.2026)

### Čo sme spravili:
1. **Textúry na 3D modeloch** - GLB modely boli šedé (OBJ→GLB konverzia stratila textúry). Vyriešené programovým aplikovaním materiálov v Three.js podľa názvu mesh časti (biely plast, mriežka s alpha mapou, Samsung logo, displej s teplotou)
2. **Zúženie katalógu** - len 2 modely s reálnymi 3D dátami (WindFree Comfort + Cebu) na testovanie
3. **WebXR AR s tap-to-place** - pridaný nový AR režim s detekciou plôch:
   - Android Chrome (ARCore) → WebXR s reticle krúžkom + klepnutím na stenu
   - iPhone/desktop → fallback na pôvodný slider-based AR
   - 3 osi rotácie (X, Y, Z) po umiestnení
   - Screenshot, tlačidlo Presunúť na nové umiestnenie

### Posledný fix:
- **Orientácia modelu na stene** - model sa chytal nesprávnou stranou. Opravené extrahovaním surface normal z hit-test pose a použitím `lookAt` namiesto kopírovania raw quaternion. **TREBA OTESTOVAŤ na telefóne** - ak je model stále otočený zle, môže byť potrebná korekčná rotácia o 180°.

### Čo treba otestovať/dorobiť:
- [ ] Otestovať WebXR AR na Android telefóne - funguje detekcia steny?
- [ ] Overiť orientáciu modelu po fixe - sedí predná strana von zo steny?
- [ ] Screenshot v WebXR režime (zachytí len 3D, nie camera feed - známe WebXR obmedzenie)
- [ ] Pridať ďalšie 3D modely (zatiaľ máme len Samsung WindFree a AR12/Cebu)

### Technické detaily:
- Súbor: `ac-visualizer.html` (všetko v jednom HTML)
- GitHub: `jelineko-hub/ac-visualizer` (master, GitHub Pages)
- URL: https://jelineko-hub.github.io/ac-visualizer/ac-visualizer.html
- Three.js r128 (CDN), GLTFLoader
- Textúry: `models/textures/` (4 JPG súbory pre WindFree)
- Originálne OBJ súbory: `models/samsung windfree/` a `models/samsung ar12/`
