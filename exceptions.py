class NoConnectionToAPIError(Exception):
    """Проблема с подключением к API."""


class HwHaveNoStatusError(Exception):
    """Домашняя работа без статуса."""


class HwHaveNoNameError(Exception):
    """В овтете API нет ключа 'homework_name'."""


class SendMessageError(Exception):
    """Ошибка отправки сообщения в Telegram."""


class JsonDecodeError(Exception):
    """Ошибка преобразования к типу данных Python."""
