# -*- coding: utf-8 -*-
"""
:authors: python273
:license: Apache License, Version 2.0, see LICENSE file

:copyright: (c) 2019 python273
"""

import requests
from io import BytesIO
from typing import Iterable, Union
from functools import reduce

from .vk_api import VkApi, VkApiMethod


STORY_ALLOWED_LINK_TEXTS = {
    'to_store', 'vote', 'more', 'book', 'order',
    'enroll', 'fill', 'signup', 'buy', 'ticket',
    'write', 'open', 'learn_more', 'view', 'go_to',
    'contact', 'watch', 'play', 'install', 'read'
}


class AttachmentHandler(dict):
    """Вспомогательный класс, используемый для хранения и обработки результата загрузки объекта"""

    __slots__ = ('key', 'access_key', 'owner_id', 'id')

    def __init__(self, key, raw, id_key=None):
        super().__init__(raw)
        self.key = key
        self.owner_id = self["owner_id"]
        self.id = self[id_key or 'id']
        self.access_key = self.get("access_key")

    def to_attachment(self):
        """Формирует вложение в формате вк"""
        return (
            f"{self.key}{self.owner_id}_{self.id}_{self.access_key}"
            if self.access_key is not None
            else f"{self.key}{self.owner_id}_{self.id}"
        )


class AttachmentsHandler(list):
    """Вспомогательный класс, используемый для хранения и обработки результата загрузки объектов

    :param raw: результат загрузки, полученный от одного из методов VkUpload
    :param key: формат вложения (doc/audio/photo), используемый для формирования вложения в формате вк
    """

    __slots__ = ('raw',)
    
    def __init__(self, key, raw=None, id_key=None) -> None:
        if isinstance(key, Iterable) and all(isinstance(x, AttachmentHandler) for x in key):
            super().__init__(key)
            return
        super().__init__(AttachmentHandler(key, obj, id_key) for obj in raw)

    def to_attachments(self):
        """Формирует вложение в формате вк"""
        return ",".join([obj.to_attachment() for obj in self])

    def __iadd__(self, other):
        if not (isinstance(other, Union[self.__class__, list]) or isinstance(other, AttachmentHandler)):
            raise NotImplementedError(f"Class {self.__class__.__name__} doesn't support addition of type {other.__class__.__name__}")
        if isinstance(other, Union[self.__class__, list]):
            super().__iadd__(other)
        else:
            self.append(other)
        return self


DISALLOWED_FROM_METHODS = ["from_link", "from_bytes"]

class VkUpload(object):
    """ Загрузка файлов через API (https://vk.com/dev/upload_files)

    :param vk: объект :class:`VkApi` или :class:`VkApiMethod`
    """

    __slots__ = ('vk', 'http')

    def __init__(self, vk):

        if not isinstance(vk, (VkApi, VkApiMethod)):
            raise TypeError(
                'The arg should be VkApi or VkApiMethod instance'
            )

        self.vk = vk if isinstance(vk, VkApiMethod) else vk.get_api()
        self.http = requests.Session()
        self.http.headers.pop('user-agent')

    def from_bytes(self, method, bytes, *args, **kwargs):
        """ Создание медиавложений из байтов 

        :param method: название метода класса VkUpload, который будет использоваться для загрузки
        :type method: str

        :param bytes: байты, которые нужно загрузить
        :type bytes: bytes or list[bytes]

        :param args: дополнительные позиционные аргументы, которые будут переданы в метод загрузки
        :param kwargs: дополнительные непозиционные аргументы, которые будут переданы в метод загрузки
        """

        if method in DISALLOWED_FROM_METHODS:
            raise ValueError(f"Метод {method} не является действительным для загрузки.")

        if isinstance(bytes, list):
            return reduce(lambda x, y: x+y, [getattr(self, method)(BytesIO(_bytes), *args, **kwargs) for _bytes in bytes])

        return getattr(self, method)(BytesIO(bytes), *args, **kwargs)

    def from_link(self, method, links, *args, **kwargs):
        """ Создания медиавложения из ссылки 
        
        :param method: название метода класса VkUpload, который будет использоваться для загрузки
        :type method: str

        :param links: ссылка или список ссылок, 
        :type links: str or list[str]

        :param args: дополнительные позиционные аргументы, которые будут переданы в метод загрузки
        :param kwargs: дополнительные непозиционные аргументы, которые будут переданы в метод загрузки
        """

        if method in DISALLOWED_FROM_METHODS:
            raise ValueError(f"Метод {method} не является действительным для загрузки.")

        send_bytes = self.http.get(links).content if isinstance(links, str) else [self.http.get(link).content for link in links]
        return self.from_bytes(method, send_bytes, *args, **kwargs)

    def photo(self, photos, album_id,
              latitude=None, longitude=None, caption=None, description=None,
              group_id=None):
        """ Загрузка изображений в альбом пользователя

        :param photos: путь к изображению(ям) или file-like объект(ы)
        :type photos: str or list

        :param album_id: идентификатор альбома
        :param latitude: географическая широта, заданная в градусах
                            (от -90 до 90)
        :param longitude: географическая долгота, заданная в градусах
                            (от -180 до 180)
        :param caption: текст описания изображения
        :param description: текст описания альбома
        :param group_id: идентификатор сообщества (если загрузка идет в группу)
        """

        values = {'album_id': album_id}

        if group_id:
            values['group_id'] = group_id

        url = self.vk.photos.getUploadServer(**values)['upload_url']

        with FilesOpener(photos) as photo_files:
            response = self.http.post(url, files=photo_files).json()

        if 'album_id' not in response:
            response['album_id'] = response['aid']

        response.update({
            'latitude': latitude,
            'longitude': longitude,
            'caption': caption,
            'description': description
        })

        values.update(response)

        return AttachmentsHandler("photo", self.vk.photos.save(**values))

    def photo_messages(self, photos, peer_id=None):
        """ Загрузка изображений в сообщения

        :param photos: путь к изображению(ям) или file-like объект(ы)
        :type photos: str or list
        :param peer_id: peer_id беседы
        :type peer_id: int
        """

        url = self.vk.photos.getMessagesUploadServer(peer_id=peer_id)[
            'upload_url']

        with FilesOpener(photos) as photo_files:
            response = self.http.post(url, files=photo_files)

        return AttachmentsHandler("photo", self.vk.photos.saveMessagesPhoto(**response.json()))

    def photo_group_widget(self, photo, image_type):
        """ Загрузка изображений в коллекцию сообщества для виджетов приложений сообществ

        :param photo: путь к изображению или file-like объект
        :type photo: str

        :param image_type: тип изображиения в зависимости от выбранного виджета
        (https://vk.com/dev/appWidgets.getGroupImageUploadServer)
        :type image_type: str
        """

        url = self.vk.appWidgets.getGroupImageUploadServer(image_type=image_type)[
            'upload_url']

        with FilesOpener(photo, key_format='file') as photo_files:
            response = self.http.post(url, files=photo_files)

        return AttachmentsHandler("photo", self.vk.appWidgets.saveGroupImage(**response.json()))

    def photo_profile(self, photo, owner_id=None, crop_x=None, crop_y=None,
                      crop_width=None):
        """ Загрузка изображения профиля

        :param photo: путь к изображению или file-like объект
        :param owner_id: идентификатор сообщества или текущего пользователя.
                По умолчанию загрузка идет в профиль текущего пользователя.
                При отрицательном значении загрузка идет в группу.
        :param crop_x: координата X верхнего правого угла миниатюры.
        :param crop_y: координата Y верхнего правого угла миниатюры.
        :param crop_width: сторона квадрата миниатюры.
                При передаче всех crop_* для фотографии также будет
                подготовлена квадратная миниатюра.
        """

        values = {}

        if owner_id:
            values['owner_id'] = owner_id

        crop_params = {}

        if crop_x is not None and crop_y is not None and crop_width is not None:
            crop_params['_square_crop'] = f'{crop_x},{crop_y},{crop_width}'

        response = self.vk.photos.getOwnerPhotoUploadServer(**values)
        url = response['upload_url']

        with FilesOpener(photo, key_format='file') as photo_files:
            response = self.http.post(
                url,
                data=crop_params,
                files=photo_files
            )

        return AttachmentsHandler("photo", self.vk.photos.saveOwnerPhoto(**response.json()))

    def photo_chat(self, photo, chat_id):
        """ Загрузка и смена обложки в беседе

        :param photo: путь к изображению или file-like объект
        :param chat_id: ID беседы
        """

        values = {'chat_id': chat_id}
        url = self.vk.photos.getChatUploadServer(**values)['upload_url']

        with FilesOpener(photo, key_format='file') as photo_file:
            response = self.http.post(url, files=photo_file)

        return self.vk.messages.setChatPhoto(
            file=response.json()['response']
        )

    def photo_wall(self, photos, user_id=None, group_id=None, caption=None):
        """ Загрузка изображений на стену пользователя или в группу

        :param photos: путь к изображению(ям) или file-like объект(ы)
        :type photos: str or list

        :param user_id: идентификатор пользователя
        :param group_id: идентификатор сообщества (если загрузка идет в группу)
        :param caption: текст описания фотографии.
        """

        values = {}

        if user_id:
            values['user_id'] = user_id
        elif group_id:
            values['group_id'] = group_id

        if caption:
            values['caption'] = caption

        response = self.vk.photos.getWallUploadServer(**values)
        url = response['upload_url']

        with FilesOpener(photos) as photos_files:
            response = self.http.post(url, files=photos_files)

        values.update(response.json())

        return AttachmentsHandler("photo", self.vk.photos.saveWallPhoto(**values))

    def photo_market(self, photo, group_id, main_photo=False,
                     crop_x=None, crop_y=None, crop_width=None):
        """ Загрузка изображений для товаров в магазине

        :param photo: путь к изображению(ям) или file-like объект(ы)
        :type photo: str or list

        :param group_id: идентификатор сообщества, для которого необходимо загрузить фотографию товара
        :type group_id: int
        :param main_photo: является ли фотография обложкой товара
        :type main_photo: bool
        :param crop_x: координата x для обрезки фотографии (верхний правый угол)
        :type crop_x: int
        :param crop_y: координата y для обрезки фотографии (верхний правый угол)
        :type crop_y: int
        :param crop_width: ширина фотографии после обрезки в px
        :type crop_width: int
        """

        if group_id < 0:
            group_id = abs(group_id)

        values = {
            'main_photo': main_photo,
            'group_id': group_id,
        }

        if crop_x is not None:
            values['crop_x'] = crop_x
        if crop_y is not None:
            values['crop_y'] = crop_y
        if crop_width is not None:
            values['crop_width'] = crop_width

        response = self.vk.photos.getMarketUploadServer(**values)
        url = response['upload_url']

        with FilesOpener(photo) as photos_files:
            response = self.http.post(url, files=photos_files)

        values.update(response.json())

        return self.vk.photos.saveMarketPhoto(**values)

    def photo_market_album(self, photo, group_id):
        """ Загрузка фотографии для подборки товаров

        :param photo: путь к изображению(ям) или file-like объект(ы)
        :type photo: str or list

        :param group_id: идентификатор сообщества, для которого необходимо загрузить фотографию для подборки товаров
        :type group_id: int
        """

        if group_id < 0:
            group_id = abs(group_id)

        values = {
            'group_id': group_id,
        }

        response = self.vk.photos.getMarketAlbumUploadServer(**values)
        url = response['upload_url']

        with FilesOpener(photo) as photos_files:
            response = self.http.post(url, files=photos_files)

        values.update(response.json())

        return self.vk.photos.saveMarketAlbumPhoto(**values)

    def audio(self, audio, artist, title):
        """ Загрузка аудио

        :param audio: путь к аудиофайлу или file-like объект
        :param artist: исполнитель
        :param title: название
        """

        url = self.vk.audio.getUploadServer()['upload_url']

        with FilesOpener(audio, key_format='file') as f:
            response = self.http.post(url, files=f).json()

        response.update({
            'artist': artist,
            'title': title
        })

        return AttachmentsHandler("audio", self.vk.audio.save(**response))

    def video(self, video_file=None, link=None, name=None, description=None,
              is_private=None, wallpost=None, group_id=None,
              album_id=None, privacy_view=None, privacy_comment=None,
              no_comments=None, repeat=None):
        """ Загрузка видео

        :param video_file: путь к видеофайлу или file-like объект.
        :type video_file: object or str

        :param link: url для встраивания видео с внешнего сайта,
            например, с Youtube.
        :type link: str

        :param name: название видеофайла
        :type name: str

        :param description: описание видеофайла
        :type description: str

        :param is_private: указывается 1, если видео загружается для отправки
            личным сообщением. После загрузки с этим параметром видеозапись
            не будет отображаться в списке видеозаписей пользователя и не будет
            доступна другим пользователям по ее идентификатору.
        :type is_private: bool

        :param wallpost: требуется ли после сохранения опубликовать
            запись с видео на стене.
        :type wallpost: bool

        :param group_id: идентификатор сообщества, в которое будет сохранен
            видеофайл. По умолчанию файл сохраняется на страницу текущего
            пользователя.
        :type group_id: int

        :param album_id: идентификатор альбома, в который будет загружен
            видеофайл.
        :type album_id: int

        :param privacy_view: настройки приватности просмотра видеозаписи в
            специальном формате. (https://vk.com/dev/objects/privacy)
            Приватность доступна для видеозаписей, которые пользователь
            загрузил в профиль. (список слов, разделенных через запятую)
        :param privacy_comment: настройки приватности комментирования
            видеозаписи в специальном формате.
            (https://vk.com/dev/objects/privacy)

        :param no_comments: 1 — закрыть комментарии (для видео из сообществ).
        :type no_comments: bool

        :param repeat: зацикливание воспроизведения видеозаписи. Флаг.
        :type repeat: bool
        """

        if not link and not video_file:
            raise ValueError('Either link or video_file param is required')

        if link and video_file:
            raise ValueError('Both params link and video_file aren\'t allowed')

        values = {
            'name': name,
            'description': description,
            'is_private': is_private,
            'wallpost': wallpost,
            'link': link,
            'group_id': group_id,
            'album_id': album_id,
            'privacy_view': privacy_view,
            'privacy_comment': privacy_comment,
            'no_comments': no_comments,
            'repeat': repeat
        }

        response = self.vk.video.save(**values)
        url = response.pop('upload_url')

        with FilesOpener(video_file or [], 'video_file') as f:
            response.update(self.http.post(
                url,
                files=f or None
            ).json())
            return AttachmentHandler("video", response, "video_id")
  
    def thumb_video(self, photo_path: str, owner_id: int, video_id: int):
        """
        Загружает обложку для видео и применяет ее.

        :param photo_path: Путь к файлу изображения, которое будет использовано в качестве обложки.
        :type photo_path: str

        :param owner_id: Идентификатор пользователя (положительное число) или группы (отрицательное число), 
                        для которой загружается миниатюра.
        :type owner_id: int

        :param video_id: Идентификатор видео.
        :type video_id: int
        """
        
        response = self.vk.video.getThumbUploadUrl(owner_id=owner_id)
        upload_url = response.pop('upload_url')

        with FilesOpener(photo_path, key_format='file') as file:
            upload_response = self.http.post(upload_url, files=file)
            
        response = self.vk.video.saveUploadedThumb(owner_id=owner_id,
                                                   thumb_json=upload_response.text,
                                                   video_id=video_id,
                                                   set_thumb=1)
        return response

    def document(self, doc, title=None, tags=None, group_id=None,
                 to_wall=False, message_peer_id=None, doc_type=None):
        """ Загрузка документа

        :param doc: путь к документу или file-like объект
        :param title: название документа
        :param tags: метки для поиска
        :param group_id: идентификатор сообщества (если загрузка идет в группу)
        """

        values = {
            'group_id': group_id,
            'peer_id': message_peer_id,
            'type': doc_type
        }

        if to_wall:
            method = self.vk.docs.getWallUploadServer
        elif message_peer_id:
            method = self.vk.docs.getMessagesUploadServer
        else:
            method = self.vk.docs.getUploadServer

        url = method(**values)['upload_url']

        with FilesOpener(doc, 'file') as files:
            response = self.http.post(url, files=files).json()

        response.update({
            'title': title,
            'tags': tags
        })

        return AttachmentsHandler("doc", self.vk.docs.save(**response))

    def document_wall(self, doc, title=None, tags=None, group_id=None):
        """ Загрузка документа в папку Отправленные,
        для последующей отправки документа на стену
        или личным сообщением.

        :param doc: путь к документу или file-like объект
        :param title: название документа
        :param tags: метки для поиска
        :param group_id: идентификатор сообщества (если загрузка идет в группу)
        """

        return self.document(doc, title, tags, group_id, to_wall=True)

    def document_message(self, doc, title=None, tags=None, peer_id=None):
        """ Загрузка документа для отправки личным сообщением.

        :param doc: путь к документу или file-like объект
        :param title: название документа
        :param tags: метки для поиска
        :param peer_id: peer_id беседы
        """

        return self.document(doc, title, tags, message_peer_id=peer_id)

    def audio_message(self, audio, peer_id=None, group_id=None):
        """ Загрузка аудио-сообщения.

        :param audio: путь к аудиофайлу или file-like объект
        :param peer_id: идентификатор диалога
        :param group_id: для токена группы, можно передавать ID группы,
            вместо peer_id
        """

        return self.document(
            audio,
            doc_type='audio_message',
            message_peer_id=peer_id,
            group_id=group_id,
            to_wall=group_id is not None
        )

    def graffiti(self, image, peer_id=None, group_id=None):
        """ Загрузка граффити

        :param image: путь к png изображению или file-like объект.
        :param peer_id: идентификатор диалога (только для авторизации пользователя)
        :param group_id: для токена группы, нужно передавать ID группы,
            вместо peer_id
        """

        return self.document(
            image,
            doc_type='graffiti',
            message_peer_id=peer_id,
            group_id=group_id,
            to_wall=group_id is not None
        )

    def photo_cover(self, photo, group_id,
                    crop_x=None, crop_y=None,
                    crop_x2=None, crop_y2=None):
        """ Загрузка изображения профиля

        :param photo: путь к изображению или file-like объект
        :param group_id: идентификатор сообщества
        :param crop_x: координата X верхнего левого угла для обрезки изображения
        :param crop_y: координата Y верхнего левого угла для обрезки изображения
        :param crop_x2: коорд. X нижнего правого угла для обрезки изображения
        :param crop_y2: коорд. Y нижнего правого угла для обрезки изображения
        """

        values = {
            'group_id': group_id,
            'crop_x': crop_x,
            'crop_y': crop_y,
            'crop_x2': crop_x2,
            'crop_y2': crop_y2
        }

        url = self.vk.photos.getOwnerCoverPhotoUploadServer(
            **values)['upload_url']

        with FilesOpener(photo, key_format='file') as photo_files:
            response = self.http.post(url, files=photo_files)

        return self.vk.photos.saveOwnerCoverPhoto(
            **response.json()
        )

    def story(self, file, file_type, add_to_news=True, user_ids=None,
              reply_to_story=None, link_text=None,
              link_url=None, group_id=None):
        """ Загрузка истории

        :param file: путь к изображению, гифке или видео или file-like объект
        :param file_type: тип истории (photo или video)
        :param add_to_news: размещать ли историю в новостях
        :param user_ids: идентификаторы пользователей,
                         которые будут видеть историю
        :param reply_to_story: идентификатор истории,
                               в ответ на которую создается новая
        :param link_text: текст ссылки для перехода из истории
        :param link_url: адрес ссылки для перехода из истории
        :param group_id: идентификатор сообщества,
                         в которое должна быть загружена история
        """

        if user_ids is None:
            user_ids = []

        if file_type == 'photo':
            method = self.vk.stories.getPhotoUploadServer
        elif file_type == 'video':
            method = self.vk.stories.getVideoUploadServer
        else:
            raise ValueError('type should be either photo or video')

        if not add_to_news and not user_ids:
            raise ValueError(
                'add_to_news and/or user_ids param is required'
            )

        if (link_text or link_url) and not group_id:
            raise ValueError('Link params available only for communities')

        if (not link_text) != (not link_url):
            raise ValueError(
                'Either both link_text and link_url or neither one are required'
            )

        if link_text and link_text not in STORY_ALLOWED_LINK_TEXTS:
            raise ValueError('Invalid link_text')

        if link_url and not link_url.startswith('https://vk.com'):
            raise ValueError(
                'Only internal https://vk.com links are allowed for link_url'
            )

        if link_url and len(link_url) > 2048:
            raise ValueError('link_url is too long. Max length - 2048')

        values = {
            'add_to_news': int(add_to_news),
            'user_ids': ','.join(map(str, user_ids)),
            'reply_to_story': reply_to_story,
            'link_text': link_text,
            'link_url': link_url,
            'group_id': group_id
        }

        url = method(**values)['upload_url']

        with FilesOpener(file, key_format='file') as files:
            return self.http.post(url, files=files)


class FilesOpener(object):
    def __init__(self, paths, key_format='file{}'):
        if not isinstance(paths, list):
            paths = [paths]

        self.paths = paths
        self.key_format = key_format
        self.opened_files = []

    def __enter__(self):
        return self.open_files()

    def __exit__(self, type, value, traceback):
        self.close_files()

    def open_files(self):
        self.close_files()

        files = []

        for x, file in enumerate(self.paths):
            if hasattr(file, 'read'):
                f = file

                filename = file.name if hasattr(file, 'name') else '.jpg'
            else:
                filename = file
                f = open(filename, 'rb')
                self.opened_files.append(f)

            ext = filename.split('.')[-1]
            files.append((self.key_format.format(x), (f'file{x}.{ext}', f)))

        return files

    def close_files(self):
        for f in self.opened_files:
            f.close()

        self.opened_files = []
