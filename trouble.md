## 3 stappenplan om alles op te starten
0. Login op biotechdag user, wachtwoord: `framboos`
1. Verbinding met raspberry pi
    * wifi netwerk `dambi_framboos`
    * wachtwoord: `framboos`
    Dit is cruciaal, zonder verbinding met het wifi netwerk zal niets werken
2. Start server:
    * Open terminal
    * `cd ballsorter`
    * `python3 server/server.py`
    * Open firefox, ga naar `localhost:5000`. F11 om fullscreen
3. Druk op start om te starten, wacht één seconde voor het opstarten van de machine, het live icoontje zal beginnen pinken (elke 30 frames pinkt dit icoontje af en aan) druk op stop om te stoppen. Easy :)


## Troubleshooting:
* Webpagina doet raar:
    * Herlaad web pagina
    * Kill alle python processen met `pkill python3` in terminal, server zal opnieuw moeten opgestart worden

* Start niet…
    * Open console, login op raspberry door `ssh pi@172.24.1.1`. 
    * Indien geen verbinding: hoogstwaarschijnlijk geen verbinding met dambi_framboos wifi network. Kan komen doordat de raspberry is gecrashet. Start raspberry opnieuw op, kan één minuut duren vooraleer opnieuw connectie met de raspberry wifi.
    * Indien verbinding met raspberry, herlaadt de webpagina om opnieuw met de server te verbinden
    * Probeer poort vrij te maken: `fuser 8002/tcp -k`, 8002 is de poort waarop de beelden binnen komen.

* Heel traag
    * Kill alle python processen met `pkill python3` in terminal, server zal opnieuw moeten opgestart worden
    
* Scherm is niet gemirrored
    * Druk op `Fn + F8`, mogelijks moet dit meermaals gebeuren omdat hij over verschillende mogelijkheden gaat
    
* Raakt niet opgelost: 0485814059
