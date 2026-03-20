# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""MONEYMAKER V1 — MetaTrader 5 Bridge.

Lo "sportello bancario" dell'ecosistema MONEYMAKER: il livello di esecuzione.
Riceve i segnali di trading validati dall'Algo Engine tramite gRPC e li
traduce in chiamate API MetaTrader 5. Come un cassiere che riceve l'ordine
di pagamento e lo esegue allo sportello.

Tre funzioni principali:
1. Ricevitore Segnali — valida, de-duplica, controlla lo stato di MT5
2. Gestore Ordini — traduce segnali in ordini MT5 (lotti, SL/TP)
3. Tracciatore Posizioni — monitora posizioni aperte, trailing stop, chiusure parziali

Fail-safe per default: nel dubbio, non fare nulla.
"""
