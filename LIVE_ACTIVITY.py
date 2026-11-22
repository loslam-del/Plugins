# LIVE ACTIVITY — typing and activity indicators for exteraGram/AyuGram
# Shows Telegram's normal typing/action updates. It cannot reveal unsent draft text
# or identify other private conversations a person may be having.

from time import monotonic

from base_plugin import BasePlugin, HookResult
from ui.settings import Header, Switch, Text
from ui.bulletin import BulletinHelper
from client_utils import get_messages_controller

__id__ = "live_activity"
__name__ = "Live Activity"
__description__ = "Показывает, кто печатает или записывает голосовое в доступных чатах."
__author__ = "loslam-del"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"
__category__ = ["chats", "privacy"]

TYPING_UPDATES = (
    "TL_updateUserTyping",
    "TL_updateChatUserTyping",
    "TL_updateChannelUserTyping",
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


class LiveActivityPlugin(BasePlugin):
    def on_plugin_load(self):
        self._last_notice = {}
        for update_name in TYPING_UPDATES:
            self.add_hook(update_name)
        self.logger.info("Live Activity loaded")

    def on_plugin_unload(self):
        self._last_notice = {}

    def create_settings(self):
        return [
            Header(text="Live Activity"),
            Switch(
                key="live_activity_enabled",
                text="Показывать активность",
                default=True,
                subtext="Уведомления о печати и действиях, которые Telegram передаёт клиенту.",
            ),
            Switch(
                key="live_activity_details",
                text="Показывать тип действия",
                default=True,
                subtext="Например: печатает, записывает голосовое, отправляет фото.",
            ),
            Text(
                text="Ограничения Telegram",
                subtext="Плагин не видит текст, который человек ещё не отправил, и не показывает, с кем он общается в других личных чатах. Видны только стандартные статусы активности, доступные твоему аккаунту.",
            ),
        ]

    def _user_id(self, update):
        value = getattr(update, "user_id", None)
        if value is not None:
            return int(value)

        peer = getattr(update, "from_id", None)
        if peer is not None:
            value = getattr(peer, "user_id", None)
            if value is not None:
                return int(value)
        return None

    def _display_name(self, account, user_id):
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
            self.logger.debug("Could not resolve typing user %s", user_id)
        return "Пользователь " + str(user_id)

    def _action_text(self, update):
        action = getattr(update, "action", None)
        if action is None:
            return "печатает…"
        action_name = type(action).__name__
        return ACTION_LABELS.get(action_name, "активен…")

    def on_update_hook(self, update_name, account, update):
        if not self.get_setting("live_activity_enabled", True):
            return HookResult()
        if update_name not in TYPING_UPDATES:
            return HookResult()

        try:
            user_id = self._user_id(update)
            if user_id is None:
                return HookResult()

            # Telegram can repeat typing updates frequently. Avoid spamming
            # the user with the same notice more than once every few seconds.
            chat_id = getattr(update, "chat_id", None)
            if chat_id is None:
                chat_id = getattr(update, "channel_id", None)
            key = (int(account), int(chat_id or 0), user_id)
            now = monotonic()
            previous = self._last_notice.get(key, 0)
            if now - previous < 4:
                return HookResult()
            self._last_notice[key] = now

            name = self._display_name(account, user_id)
            if self.get_setting("live_activity_details", True):
                action = self._action_text(update)
            else:
                action = "активен…"

            BulletinHelper.show_info(name + " " + action)
        except Exception:
            self.logger.exception("Failed to process activity update")

        return HookResult()
