# SPAW — shared-group activity viewer for exteraGram/AyuGram
# Each installation only displays updates already delivered to that user's account.
# It does not upload data, read private chats the account cannot access, or reveal drafts.

from time import monotonic

from base_plugin import BasePlugin, HookResult
from ui.settings import Header, Switch, Text
from ui.bulletin import BulletinHelper
from client_utils import get_messages_controller

__id__ = "spaw"
__name__ = "SPAW"
__description__ = "Показывает активность и новые сообщения в общих группах."
__author__ = "loslam-del"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"
__category__ = ["chats", "tools"]

TYPING_UPDATES = (
    "TL_updateUserTyping",
    "TL_updateChatUserTyping",
    "TL_updateChannelUserTyping",
)
MESSAGE_UPDATES = (
    "TL_updateNewMessage",
    "TL_updateNewChannelMessage",
)

ACTION_LABELS = {
    "TL_sendMessageTypingAction": "печатает…",
    "TL_sendMessageRecordAudioAction": "записывает голосовое…",
    "TL_sendMessageUploadAudioAction": "отправляет аудио…",
    "TL_sendMessageRecordRoundAction": "записывает видеосообщение…",
    "TL_sendMessageUploadRoundAction": "отправляет видеосообщение…",
    "TL_sendMessageUploadVideoAction": "отправляет видео…",
    "TL_sendMessageUploadPhotoAction": "отправляет фото…",
    "TL_sendMessageUploadDocumentAction": "отправляет файл…",
    "TL_sendMessageChooseContactAction": "выбирает контакт…",
    "TL_sendMessageGeoLocationAction": "отправляет геопозицию…",
    "TL_sendMessageGamePlayAction": "играет…",
    "TL_sendMessageCancelAction": "прекратил действие",
}


class SPAWPlugin(BasePlugin):
    def on_plugin_load(self):
        self._last_typing = {}
        self._last_messages = {}
        for name in TYPING_UPDATES + MESSAGE_UPDATES:
            self.add_hook(name)
        self.logger.info("SPAW loaded")

    def on_plugin_unload(self):
        self._last_typing = {}
        self._last_messages = {}

    def create_settings(self):
        return [
            Header(text="SPAW — активность в общих группах"),
            Switch(
                key="spaw_typing",
                text="Показывать, кто печатает",
                default=True,
                subtext="Показывает стандартные статусы Telegram в доступных группах и чатах.",
            ),
            Switch(
                key="spaw_messages",
                text="Уведомлять о новых сообщениях в группах",
                default=True,
                subtext="Показывает отправителя, название группы и текст уже отправленного сообщения.",
            ),
            Switch(
                key="spaw_message_text",
                text="Показывать текст сообщений",
                default=True,
                subtext="Если выключить, будут показываться только отправитель и группа.",
            ),
            Text(
                text="Как это работает",
                subtext="Вы оба устанавливаете плагин. Каждый видит только те групповые обновления, которые Telegram доставляет его аккаунту. Личные переписки других людей и неотправленные черновики недоступны. Никакие данные на внешний сервер не отправляются.",
            ),
        ]

    def _user_id(self, obj):
        value = getattr(obj, "user_id", None)
        if value is not None:
            return int(value)
        peer = getattr(obj, "from_id", None)
        if peer is not None:
            value = getattr(peer, "user_id", None)
            if value is not None:
                return int(value)
        return None

    def _name(self, account, user_id):
        if user_id is None:
            return "Участник"
        try:
            user = get_messages_controller(account).getUser(user_id)
            if user is not None:
                first = str(getattr(user, "first_name", "") or "").strip()
                last = str(getattr(user, "last_name", "") or "").strip()
                name = (first + " " + last).strip()
                if name:
                    return name
                username = str(getattr(user, "username", "") or "").strip()
                if username:
                    return "@" + username
        except Exception:
            self.logger.debug("Could not resolve user %s", user_id)
        return "Пользователь " + str(user_id)

    def _group_id(self, peer):
        if peer is None:
            return None
        chat_id = getattr(peer, "chat_id", None)
        if chat_id is not None:
            return int(chat_id)
        channel_id = getattr(peer, "channel_id", None)
        if channel_id is not None:
            return int(channel_id)
        return None

    def _group_title(self, account, group_id):
        if group_id is None:
            return "группе"
        try:
            chat = get_messages_controller(account).getChat(group_id)
            if chat is not None:
                title = str(getattr(chat, "title", "") or "").strip()
                if title:
                    return title
        except Exception:
            self.logger.debug("Could not resolve group %s", group_id)
        return "группе " + str(group_id)

    def _typing_action(self, update):
        action = getattr(update, "action", None)
        if action is None:
            return "печатает…"
        return ACTION_LABELS.get(type(action).__name__, "активен…")

    def _handle_typing(self, update_name, account, update):
        user_id = self._user_id(update)
        if user_id is None:
            return
        group_id = getattr(update, "chat_id", None)
        if group_id is None:
            group_id = getattr(update, "channel_id", None)
        group_id = int(group_id or 0)

        key = (int(account), group_id, user_id)
        now = monotonic()
        if now - self._last_typing.get(key, 0) < 4:
            return
        self._last_typing[key] = now

        name = self._name(account, user_id)
        title = self._group_title(account, group_id)
        action = self._typing_action(update)
        BulletinHelper.show_info(name + " " + action + " В чате: " + title)

    def _handle_message(self, update_name, account, update):
        message = getattr(update, "message", None)
        if message is None:
            return

        peer = getattr(message, "peer_id", None)
        group_id = self._group_id(peer)
        # Only group chats and channels/supergroups. Skip private dialogs.
        if group_id is None:
            return

        sender_id = self._user_id(message)
        name = self._name(account, sender_id)
        title = self._group_title(account, group_id)
        message_id = getattr(message, "id", None)
        key = (int(account), group_id, int(message_id or 0))
        now = monotonic()
        if now - self._last_messages.get(key, 0) < 30:
            return
        self._last_messages[key] = now

        text = str(getattr(message, "message", "") or "").strip()
        if self.get_setting("spaw_message_text", True) and text:
            if len(text) > 140:
                text = text[:137] + "..."
            notice = name + " в «" + title + "»: " + text
        else:
            notice = name + " отправил сообщение в «" + title + "»"
        BulletinHelper.show_info(notice)

    def on_update_hook(self, update_name, account, update):
        try:
            if update_name in TYPING_UPDATES:
                if self.get_setting("spaw_typing", True):
                    self._handle_typing(update_name, account, update)
            elif update_name in MESSAGE_UPDATES:
                if self.get_setting("spaw_messages", True):
                    self._handle_message(update_name, account, update)
        except Exception:
            self.logger.exception("SPAW failed to process %s", update_name)
        return HookResult()
