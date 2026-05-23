# VoltPure Edge — Home Assistant Add-on

## Installatie

1. In HA: **Instellingen → Add-ons → Add-on Store**
2. Klik rechtsboven op menu (⋮) → **Repositories**
3. Voeg toe: `https://github.com/zwijn25/voltpure-platform`
4. Refresh — **VoltPure Edge** verschijnt in de lijst
5. Klik **Installeren**
6. Configuratie-tab → vul in:
   - `klant_id` — ontvangen per mail
   - `license_token` — ontvangen per mail
7. **Start** de add-on

## Wat doet het?

- Leest energie-data uit Home Assistant (P1, PV, batterij, EV-lader, Shelly's)
- Publisht naar VoltPure cloud (MQTT over Cloudflare Tunnel — geen poort open)
- Maakt je data zichtbaar op `https://app.voltpure.be` (per-klant login)
- License-gated: zonder geldig abonnement geen publish

## Vereisten

- Home Assistant OS of Supervised
- HA-entities aanwezig voor minstens: net-verbruik (`sensor.p1_actief_vermogen` of equivalent)

## Privacy

- Alle data op VoltPure-servers (België)
- TLS-versleuteld via Cloudflare Tunnel
- Geen externe verwerker — Anthropic/AWS/Google zien je data NIET
- GDPR-conform, export op vraag

## Support

- Mail: info@voltpure.be
- Portal: https://app.voltpure.be/pro

## Versie

1.0.0 — initial release
