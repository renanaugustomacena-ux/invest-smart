"""Gerarchia delle eccezioni condivise per i servizi MONEYMAKER.

Come i "codici di errore" di un'ambulanza: ogni tipo di eccezione
indica un problema specifico, così il servizio sa come reagire.
"""


class MoneyMakerError(Exception):
    """Eccezione base per tutti gli errori MONEYMAKER — la "sirena generica"."""


class ConfigurationError(MoneyMakerError):
    """Sollevata quando la configurazione è non valida o mancante."""


class ConnectionError(MoneyMakerError):
    """Sollevata quando il servizio non riesce a connettersi a una dipendenza."""


class DataValidationError(MoneyMakerError):
    """Sollevata quando i dati in ingresso non superano la validazione."""


class SignalRejectedError(MoneyMakerError):
    """Sollevata quando un segnale di trading è rifiutato dai controlli di rischio."""

    def __init__(self, signal_id: str, reason: str) -> None:
        self.signal_id = signal_id
        self.reason = reason
        super().__init__(f"Segnale {signal_id} rifiutato: {reason}")


class RiskLimitExceededError(MoneyMakerError):
    """Sollevata quando un limite di rischio viene superato."""


class BrokerError(MoneyMakerError):
    """Sollevata quando la comunicazione con il broker fallisce."""


class RateLimitExceededError(MoneyMakerError):
    """Sollevata quando il rate limit viene superato.

    Come un "semaforo rosso": troppe richieste in poco tempo.
    Il client deve attendere prima di riprovare.
    """

    def __init__(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        retry_after: float | None = None,
    ) -> None:
        self.key = key
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after = retry_after
        msg = f"Rate limit superato per '{key}': max {limit} richieste ogni {window_seconds}s"
        if retry_after:
            msg += f" (retry tra {retry_after:.1f}s)"
        super().__init__(msg)
