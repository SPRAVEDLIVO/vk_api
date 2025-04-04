# -*- coding: utf-8 -*-
"""
:authors: python273
:license: Apache License, Version 2.0, see LICENSE file

:copyright: (c) 2019 python273
"""

import enum

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, enum.Enum):
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()


class VerificationMethod(StrEnum):
    """
    Перечисление способов подтверждения входа в аккаунт.

    EMAIL, SMS, CALLRESET и PUSH требуют вызова метода API для отправки.
    """
    PUSH = enum.auto()
    EMAIL = enum.auto()
    QR_CODE = enum.auto()
    CODEGEN = enum.auto()
    SMS = enum.auto()
    CALLRESET = enum.auto()
    PASSWORD = enum.auto()
    RESERVE_CODE = enum.auto()
    PASSKEY = enum.auto()


class VkUserPermissions(enum.IntEnum):
    """
    Перечисление прав пользователя.
    Список прав получается побитовым сложением (x | y) каждого права.
    Подробнее в документации VK API: https://vk.com/dev/permissions
    """

    #: Пользователь разрешил отправлять ему уведомления
    #: (для flash/iframe-приложений).
    #: Не работает с этой библиотекой.
    NOTIFY = 1

    #: Доступ к друзьям.
    FRIEND = 2

    #: Доступ к фотографиям.
    PHOTOS = 2**2

    #: Доступ к аудиозаписям.
    #: При отсутствии доступа к закрытому API аудиозаписей это право позволяет
    #: только загрузку аудио.
    AUDIO = 2**3

    #: Доступ к видеозаписям.
    VIDEO = 2**4

    #: Доступ к историям.
    STORIES = 2**6

    #: Доступ к wiki-страницам.
    PAGES = 2**7

    #: Добавление ссылки на приложение в меню слева.
    ADD_LINK = 2**8

    #: Доступ к статусу пользователя.
    STATUS = 2**10

    #: Доступ к заметкам пользователя.
    NOTES = 2**11

    #: Доступ к расширенным методам работы с сообщениями.
    MESSAGES = 2**12

    #: Доступ к обычным и расширенным методам работы со стеной.
    WALL = 2**13

    #: Доступ к расширенным методам работы с рекламным API.
    ADS = 2**15

    #: Доступ к API в любое время. Рекомендуется при работе с этой библиотекой.
    OFFLINE = 2**16

    #: Доступ к документам.
    DOCS = 2**17

    #: Доступ к группам пользователя.
    GROUPS = 2**18

    #: Доступ к оповещениям об ответах пользователю.
    NOTIFICATIONS = 2**19

    #: Доступ к статистике групп и приложений пользователя, администратором которых он является.
    STATS = 2**20

    #: Доступ к email пользователя.
    EMAIL = 2**22

    #: Доступ к товарам.
    MARKET = 2**27


class AudiosSearchOptions(enum.Enum):
    GLOBAL_AUDIOS = "search_global_audios"
    MY_MUSIC = "search_owned_audios"
    LYRICS = "_global_audios_lyrics"
