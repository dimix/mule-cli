# mule — ricerca e download da eMule (ed2k / Kad) via CLI

Una piccola CLI che pilota un motore **MLDonkey** headless (in Docker) per cercare
e scaricare file dalle reti **ed2k** e **Kad** — senza nessuna app Mac con GUI.
Output `--json` su ogni comando dati, così è usabile sia a mano sia da un agente.

## Installazione (macOS)

Serve solo [Homebrew](https://brew.sh). Poi:

```bash
git clone https://github.com/dimix/mule-cli.git
cd mule-cli
./install.sh
```

`install.sh` fa tutto: installa Colima + Docker, avvia il motore MLDonkey in un
container, aggancia Kad e i server ed2k, e mette `mule` nel PATH. È idempotente
(puoi rilanciarlo). Dopo, da qualsiasi cartella:

```bash
mule search "big buck bunny"
mule download <id>
```

## Architettura

```
  ./mule  (Python, host)  ──telnet 127.0.0.1:4000──▶  MLDonkey (container Docker)
                                                          │ ed2k + Kad (serverless)
   download completati  ◀── ./data/incoming/files/ ◀──────┘
```

- Il lavoro di rete (protocollo ed2k/Kad, hashing, code, sorgenti) lo fa MLDonkey.
- La CLI manda comandi alla console di MLDonkey e ne ripulisce/parsa l'output.
- Container: `mule-mldonkey` (immagine `carlonluca/mldonkey`, arm64 nativo).
- Runtime container: **Colima** (VM Linux leggera installata via Homebrew).

## Dove finiscono i file

| | percorso sul Mac |
|---|---|
| Completati | `./data/incoming/files/` |
| Parziali   | `./data/temp/` |
| Config MLDonkey | `./data/*.ini` |

(`./data` è montato come `/var/lib/mldonkey` dentro il container.)

## Uso quotidiano

```bash
./mule net                       # stato reti (Kad connesso?)
./mule search interstellar       # cerca (attende ~35s i risultati Kad)
./mule search "big buck bunny" --limit 15
./mule results                   # rimostra l'ultima ricerca
./mule download 12               # scarica il risultato n. 12 (anche più id)
./mule downloads                 # avanzamento dei download attivi
./mule pause 1 / resume 1        # pausa / riprendi
./mule cancel 1                  # annulla (gestisce la conferma da solo)
./mule commit                    # sposta i completati in incoming/
```

Ogni comando dati accetta `--json`:
```bash
./mule search debian --json
./mule downloads --json
```

Grimaldello per comandi MLDonkey grezzi (debug/avanzato):
```bash
./mule console "vma"             # lista tutti i server
./mule console "kad_stats"
```

## Gestione del demone

```bash
./mule daemon status             # è su?
./mule daemon start|stop|restart
./mule daemon logs
```

## Dopo un riavvio del Mac

Colima non parte da solo (a meno di `brew services start colima`). Quindi:

```bash
colima start                     # riavvia la VM Linux
docker start mule-mldonkey       # il container ha restart=unless-stopped, parte da solo
./mule net                       # verifica che Kad si riconnetta
```

## Bootstrap delle reti (se la ricerca smette di dare risultati)

ed2k/Kad vanno "agganciati" a dei peer. La config attuale è già impostata, ma se
in futuro Kad non si connette più:

```bash
./mule console "kad_web"                                   # nodi Kad di default
./mule console "urladd kad http://upd.emule-security.org/nodes.dat"
./mule console "force_web_infos kad"
./mule console "save"
```

Per i **server ed2k** le liste automatiche (server.met) sono quasi tutte morte:
meglio aggiungere a mano server vivi con `n <ip> <port>`. Questi risultavano
funzionanti (giu 2026) — il primo regge ~23M di file:

```bash
./mule console "n 45.82.80.155 5687"      # eMule Security  (il più carico)
./mule console "n 176.123.5.89 4725"      # eMule Sunrise
./mule console "n 91.208.162.87 4232"     # Sharing-Devils
./mule console "n 145.239.2.134 4661"     # GrupoTS
./mule console "c"                         # connetti
./mule console "save"
```

Nota: l'ipfilter (`guarding.p2p`) può marcare dei server come "IP blocked".

## Note

- La rete ed2k/Kad indicizza **soprattutto file multimediali**: query tipo "ubuntu"
  spesso danno 0 risultati. I risultati **non sono filtrati**.
- I server ed2k classici sono quasi tutti morti: il download reale passa per **Kad**.
- Dietro NAT senza port-forward avrai "LowID": funziona, ma più lento. Per "HighID"
  va aperta sul router la porta TCP/UDP del container (19040/19044).
- Scarica solo contenuti che hai il diritto di scaricare.

## Stack installato

- `brew install colima docker`
- immagine `carlonluca/mldonkey` (porte: 4000 console, 4080 web, 19040/19044 p2p)
- la CLI è solo `./mule` (Python 3, nessuna dipendenza esterna)

## Disclaimer / uso lecito

`mule-cli` è un **client** per le reti P2P ed2k/Kad — come aMule, eMule o un
qualsiasi client BitTorrent. Non ospita né distribuisce alcun contenuto: si limita
a parlare con una rete pubblica esistente.

La responsabilità su **cosa** viene cercato e scaricato è interamente di chi usa lo
strumento. Usalo solo per file che hai il diritto di scaricare (software libero,
opere di pubblico dominio, contenuti tuoi o con licenza che lo permette) e nel
rispetto delle leggi sul diritto d'autore del tuo paese. Il software è fornito
"così com'è", senza garanzie (vedi `LICENSE`).
