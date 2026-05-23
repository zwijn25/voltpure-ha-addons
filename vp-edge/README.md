# VoltPure Edge — Home Assistant Add-on

## Wat is dit?

Een **bruggetje** tussen jouw Home Assistant en het **VoltPure EMS-platform** (cloud-optimizer).

Het is **niet** zelf de optimizer. Deze add-on doet één ding:
- Leest live energiedata uit je HA (P1, PV, batterij, EV-lader, Shelly's)
- Stuurt ze versleuteld naar VoltPure cloud
- Ontvangt aansturingen terug (laadlimieten, schakel-commando's)

De **slimme aansturing draait in de cloud**, niet hier.

## Waarom een aparte addon en niet "gewoon" een HA-automation?

| Functie | HA zelf (DIY) | VoltPure-platform |
|---|---|---|
| Aan/uit-automation op overschot | ✓ | ✓ |
| Solcast PV-forecast 24-72u | ❌ (alleen ruwe entity) | ✓ (eigen blend met Open-Meteo + correctie) |
| ENTSO-E/Belpex prijs-curve optimizer | ❌ | ✓ (24u-cascade plan) |
| VREG-piek-management 15-min-rolling | ❌ (zelf bouwen = bricolage) | ✓ (cross-klant geleerd, anonieme bias) |
| NILM apparaat-detectie (~1500 toestellen) | ❌ | ✓ (waterboiler, oven, droger, EV — automatisch) |
| Slim-laden Liam-style per Shelly | ❌ | ✓ (auto-vol-detectie via watt-drempel) |
| EV-lader cascade (Easee/Peblar/Pulsar/Wallbox) | Beperkt | ✓ (122+ merken) |
| Fleet-anonieme peer-learning | ❌ (niet mogelijk solo) | ✓ (jouw biases corrigeren via 100+ klanten) |
| 30-dagen anomalie-detectie | ❌ | ✓ |
| Maandrapport + besparing-cijfers | ❌ | ✓ |
| Dashboard `app.voltpure.be/pro` | ❌ | ✓ |
| Documenten-kluis + AI-analyse | ❌ | ✓ |

Wie het zelf wil bouwen: **3-6 maanden werk per klant**. VoltPure heeft het al gedaan voor 100+ klanten, blijft het verbeteren via cloud-deployments.

## Wat krijg je voor het abonnement?

- ✅ Continue cloud-optimalisatie (24u-cascade, elke 30s herrekenen)
- ✅ Automatische updates van de optimizer (geen klant-actie)
- ✅ Per-klant dashboard `app.voltpure.be/pro` (10 views: flow, kluis, NILM, alerts, rapportage)
- ✅ Maandelijks besparing-rapport via mail
- ✅ Pro-actieve anomalie-melding (defecte omvormer, batterij-degradatie)
- ✅ Hardware-onafhankelijk: werkt met élke HA-installatie
- ✅ Support via info@voltpure.be

## Installatie

1. **Settings → Add-ons → Add-on Store**
2. Menu (⋮) → **Repositories**
3. Voeg toe: `https://github.com/zwijn25/voltpure-ha-addons`
4. Refresh → installeer **VoltPure Edge**
5. ⚠ **Eerste installatie duurt 3-5 min** — HA bouwt Docker image lokaal
6. Tab **Configuratie**: vul `klant_id` + `license_token` in (per mail ontvangen)
7. **Start** → tab **Log** → wacht op `License OK`

## Vereisten

- Home Assistant OS of Supervised (Green / Yellow / Blue / Pi4-met-HAOS)
- Geldige VoltPure-licentie (`klant_id` + `license_token`)
- Minstens een net-verbruik-sensor (P1 / HomeWizard / DSMR)

## Privacy

- ✅ Data op VoltPure-servers (België)
- ✅ TLS via Cloudflare Tunnel (geen poort open in jouw router)
- ✅ Géén Anthropic / AWS / Google — geen data naar derden
- ✅ GDPR-conform, volledige export op vraag
- ✅ Geen advertenties, geen data-verkoop

## Stoppen

- Tab **Info** → **STOPPEN** → optimizer ontvangt geen nieuwe data, jouw HA blijft draaien zoals voor de installatie.
- Volledig verwijderen → **DEINSTALLEREN** + repository verwijderen.

## Support

- Mail: info@voltpure.be
- Portal: https://app.voltpure.be
- Suggesties / bugs: tab **Instellingen** in `app.voltpure.be/pro`

## Versie

1.0.1 — productie-ready (license-gate + multi-arch build + officieel logo)
