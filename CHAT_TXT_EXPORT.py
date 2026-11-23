# CHAT TXT EXPORT — export one selected Telegram chat to a .txt file
# Flow:
# 1) In the source chat, open a message context menu -> "Экспортировать чат в TXT".
# 2) The plugin exports up to the latest 1000 text messages locally.
# 3) Open the destination chat and send .txtsend; confirm the recipient before upload.
# Media files are not downloaded or embedded. Only messages accessible to this account are exported.

from datetime import datetime
import os

from base_plugin import BasePlugin, HookResult, HookStrategy, MenuItemData, MenuItemType
from client_utils import (
    get_last_fragment,
    get_messages_controller,
    get_selected_account,
    send_document,
    send_request,
)
from file_utils import ensure_dir_exists, get_plugins_dir, write_file
from ui.alert import AlertDialogBuilder
from ui.bulletin import BulletinHelper
from ui.settings import Header, Text
from org.telegram.tgnet import TLRPC

__id__ = "chat_txt_export"
__name__ = "Chat TXT Export"
__description__ = "Экспорт выбранной переписки в TXT и отправка выбранному контакту."
__author__ = "loslam-del"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"
__category__ = ["chats", "tools"]

PAGE_SIZE = 100
MAX_MESSAGES = 1000
SEND_COMMAND = ".txtsend"


def _peer_dialog_id(peer):
    if peer is None:
        return 0
    try:
        name = str(peer.getClass().getSimpleName())
        if "PeerUser" in name:
            return int(peer.user_id)
        if "PeerChannel" in name:
            return -(1000000000000 + int(peer.channel_id))
        if "PeerChat" in name:
            return -int(peer.chat_id)
    except Exception:
        pass
    return 0


class ChatTxtExportPlugin(BasePlugin):
    def on_plugin_load(self):
        self._exporting = False
        self._pending_file = ""
        self._pending_title = ""
        self._source_dialog_id = 0
        self._account = get_selected_account()
        self.add_on_send_message_hook()
        self.menu_item_id = self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.MESSAGE_CONTEXT_MENU,
                text="Экспортировать чат в TXT",
                on_click=self._on_export_menu,
                icon="msg_file",
                subtext="Сохранить до 1000 последних текстовых сообщений",
                priority=5,
            )
        )
        self.logger.info("Chat TXT Export loaded")

    def create_settings(self):
        return [
            Header(text="Chat TXT Export"),
            Text(
                text="Как пользоваться",
                subtext=(
                    "В исходном чате открой меню любого сообщения и выбери "
                    "«Экспортировать чат в TXT». После экспорта открой чат получателя "
                    "и отправь команду .txtsend. Перед отправкой появится подтверждение. "
                    "В файл попадут до 1000 последних сообщений; фото, видео, файлы "
                    "и голосовые не скачиваются."
                ),
            ),
            Text(
                text="Конфиденциальность",
                subtext=(
                    "Экспорт создаётся локально на устройстве. Файл отправляется "
                    "только после твоего подтверждения в выбранном чате."
                ),
            ),
        ]

    def _activity(self):
        fragment = get_last_fragment()
        if fragment is None:
            return None
        try:
            return fragment.getParentActivity()
        except Exception:
            return None

    def _show_confirm(self, title, message, positive_text, callback):
        activity = self._activity()
        if activity is None:
            BulletinHelper.show_error("Не удалось открыть окно подтверждения")
            return
        builder = AlertDialogBuilder(activity)
        builder.set_title(title)
        builder.set_message(message)
        builder.set_positive_button(positive_text, lambda b, w: (b.dismiss(), callback()))
        builder.set_negative_button("Отмена", lambda b, w: b.dismiss())
        builder.set_cancelable(True)
        builder.show()

    def _on_export_menu(self, context):
        try:
            dialog_id = int(context.get("dialog_id") or 0)
        except Exception:
            dialog_id = 0
        if not dialog_id:
            BulletinHelper.show_error("Не удалось определить исходный чат")
            return
        if self._exporting:
            BulletinHelper.show_info("Экспорт уже выполняется")
            return

        account = int(context.get("account", get_selected_account()))
        title = self._chat_title(dialog_id, account)
        self._show_confirm(
            "Экспорт переписки",
            "Будет создан TXT-файл с максимум 1000 последними сообщениями из «%s». "
            "Медиафайлы не включаются. После экспорта файл останется на устройстве. "
            "Для отправки открой чат получателя и введи .txtsend." % title,
            "Экспортировать",
            lambda: self._start_export(dialog_id, title, account),
        )

    def _chat_title(self, dialog_id, account):
        try:
            controller = get_messages_controller(account)
            if dialog_id > 0:
                user = controller.getUser(dialog_id)
                if user is not None:
                    name = (str(getattr(user, "first_name", "") or "") + " " +
                            str(getattr(user, "last_name", "") or "")).strip()
                    return name or ("ID " + str(dialog_id))
            elif dialog_id < -1000000000000:
                channel = controller.getChannel(-dialog_id - 1000000000000)
                if channel is not None:
                    return str(getattr(channel, "title", "") or ("ID " + str(dialog_id)))
            else:
                chat = controller.getChat(-dialog_id)
                if chat is not None:
                    return str(getattr(chat, "title", "") or ("ID " + str(dialog_id)))
        except Exception:
            self.logger.exception("Could not resolve chat title")
        return "чат " + str(dialog_id)

    def _resolve_peer(self, dialog_id, account):
        controller = get_messages_controller(account)
        if controller is None:
            return None
        try:
            if dialog_id > 0:
                user = controller.getUser(dialog_id)
                if user is None:
                    return None
                peer = TLRPC.TL_inputPeerUser()
                peer.user_id = dialog_id
                peer.access_hash = int(getattr(user, "access_hash", 0) or 0)
                return peer
            if dialog_id < -1000000000000:
                channel_id = -dialog_id - 1000000000000
                channel = controller.getChannel(channel_id)
                if channel is None:
                    return None
                peer = TLRPC.TL_inputPeerChannel()
                peer.channel_id = channel_id
                peer.access_hash = int(getattr(channel, "access_hash", 0) or 0)
                return peer
            peer = TLRPC.TL_inputPeerChat()
            peer.chat_id = -dialog_id
            return peer
        except Exception:
            self.logger.exception("Could not resolve input peer")
            return None

    def _start_export(self, dialog_id, title, account):
        peer = self._resolve_peer(dialog_id, account)
        if peer is None:
            BulletinHelper.show_error("Не удалось получить доступ к этому чату")
            return
        self._exporting = True
        self._source_dialog_id = dialog_id
        self._account = account
        self._pending_title = title
        self._collected = []
        self._seen_ids = set()
        BulletinHelper.show_info("Начинаю экспорт: " + title)
        self._request_page(peer, dialog_id, account, 0)

    def _request_page(self, peer, dialog_id, account, offset_id):
        try:
            request = TLRPC.TL_messages_getHistory()
            request.peer = peer
            request.limit = PAGE_SIZE
            request.offset_id = int(offset_id)
            request.add_offset = 0
            request.offset_date = 0
            request.max_id = 0
            request.min_id = 0
            request.hash = 0
            send_request(
                request,
                lambda response, error: self._on_history_page(
                    peer, dialog_id, account, response, error
                ),
                account=account,
            )
        except Exception:
            self.logger.exception("Failed to request chat history")
            self._exporting = False
            BulletinHelper.show_error("Не удалось запросить историю чата")

    def _sender_name(self, message, account):
        if bool(getattr(message, "out", False)):
            return "Вы"
        try:
            from_peer = getattr(message, "from_id", None)
            user_id = int(getattr(from_peer, "user_id", 0) or 0) if from_peer else 0
            if user_id:
                user = get_messages_controller(account).getUser(user_id)
                if user is not None:
                    name = (str(getattr(user, "first_name", "") or "") + " " +
                            str(getattr(user, "last_name", "") or "")).strip()
                    if name:
                        return name
                    username = str(getattr(user, "username", "") or "").strip()
                    if username:
                        return "@" + username
        except Exception:
            pass
        return "Участник"

    def _on_history_page(self, peer, dialog_id, account, response, error):
        if error:
            self.logger.warning("History request error: %s", getattr(error, "text", error))
            self._finish_export()
            BulletinHelper.show_error("Telegram не смог загрузить часть истории")
            return
        try:
            messages = list(getattr(response, "messages", []) or [])
            if not messages:
                self._finish_export()
                return

            oldest_id = None
            added = 0
            for message in messages:
                message_id = int(getattr(message, "id", 0) or 0)
                if message_id <= 0:
                    continue
                oldest_id = message_id if oldest_id is None else min(oldest_id, message_id)
                if message_id in self._seen_ids:
                    continue
                self._seen_ids.add(message_id)
                text = str(getattr(message, "message", "") or "").strip()
                if not text:
                    media = getattr(message, "media", None)
                    if media is not None:
                        text = "[медиафайл или вложение — не включено в экспорт]"
                    else:
                        action = getattr(message, "action", None)
                        if action is not None:
                            text = "[событие чата]"
                        else:
                            continue
                date_value = int(getattr(message, "date", 0) or 0)
                try:
                    date_text = datetime.fromtimestamp(date_value).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_text = "неизвестная дата"
                sender = self._sender_name(message, account)
                self._collected.append((date_value, message_id, sender, text))
                added += 1

            if len(self._seen_ids) >= MAX_MESSAGES or len(messages) < PAGE_SIZE:
                self._finish_export()
                return
            if oldest_id is None or oldest_id <= 0:
                self._finish_export()
                return
            # offset_id is exclusive: the next request continues with older messages.
            self._request_page(peer, dialog_id, account, oldest_id)
        except Exception:
            self.logger.exception("Failed to parse history response")
            self._exporting = False
            BulletinHelper.show_error("Ошибка при обработке истории чата")

    def _finish_export(self):
        try:
            entries = sorted(self._collected, key=lambda item: (item[0], item[1]))
            lines = [
                "Экспорт чата: " + self._pending_title,
                "Экспортировано сообщений: " + str(len(entries)),
                "Примечание: вложения не скачивались; в файле сохранён только текст и подписи.",
                "=" * 60,
            ]
            for date_value, message_id, sender, message_text in entries:
                try:
                    date_text = datetime.fromtimestamp(date_value).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_text = "неизвестная дата"
                lines.append("[%s] %s (ID %s):" % (date_text, sender, message_id))
                lines.append(message_text)
                lines.append("")
            safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in self._pending_title)
            safe_title = safe_title[:40] or "chat"
            folder = os.path.join(get_plugins_dir(), "chat_txt_export")
            ensure_dir_exists(folder)
            path = os.path.join(folder, "%s_%s.txt" % (safe_title, self._source_dialog_id))
            write_file(path, "\n".join(lines))
            self._pending_file = path
            self._exporting = False
            BulletinHelper.show_success(
                "Экспорт готов: %d сообщений. Открой чат получателя и отправь .txtsend." % len(entries)
            )
        except Exception:
            self._exporting = False
            self.logger.exception("Could not write export file")
            BulletinHelper.show_error("Не удалось сохранить TXT-файл")

    def on_send_message_hook(self, account, params):
        try:
            text = getattr(params, "message", None)
            if not isinstance(text, str) or text.strip().lower() != SEND_COMMAND:
                return HookResult()
            result = HookResult()
            result.strategy = HookStrategy.CANCEL
            result.params = params
            if not self._pending_file or not os.path.isfile(self._pending_file):
                BulletinHelper.show_error("Сначала экспортируй чат через меню сообщения")
                return result

            destination = int(getattr(params, "peer", 0) or 0)
            # Telegram send params peer is the currently open destination dialog id.
            destination_title = self._chat_title(destination, account) if destination else "текущий чат"
            self._show_confirm(
                "Отправить TXT-файл?",
                "Файл содержит переписку «%s» и будет отправлен в «%s». "
                "Проверь, что выбрал правильного получателя." %
                (self._pending_title, destination_title),
                "Отправить файл",
                lambda: self._send_pending_file(destination),
            )
            return result
        except Exception:
            self.logger.exception("Failed to handle .txtsend")
            return HookResult()

    def _send_pending_file(self, destination):
        if not destination:
            BulletinHelper.show_error("Не удалось определить чат-получатель")
            return
        try:
            send_document(destination, self._pending_file,
                          caption="Экспорт переписки: " + self._pending_title)
            BulletinHelper.show_success("Файл отправлен")
        except Exception:
            self.logger.exception("Failed to send exported TXT")
            BulletinHelper.show_error("Не удалось отправить файл")
