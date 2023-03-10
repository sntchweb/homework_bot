class NoConnectionToAPIError(Exception):
    """Проблема с подключением к API."""

    ...


class HwHaveNoStatusError(Exception):
    """Домашняя работа без статуса."""

    ...


class HwHaveNoNameError(Exception):
    """В овтете API нет ключа 'homework_name'."""

    ...
