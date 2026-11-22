# NPC WORLD RPG — standalone AyuGram/exteraGram plugin
# Version 0.1.0 — playable local RPG prototype.
# Multiplayer, guilds and shared raids require a backend and are not included yet.

import json
import random

from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Header, Switch, Text
from ui.bulletin import BulletinHelper

__id__ = "npc_world_rpg"
__name__ = "NPC WORLD RPG"
__description__ = "Dark fantasy RPG: character progression, quests, exploration and battles."
__author__ = "loslam-del"
__version__ = "0.1.0"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"
__category__ = ["fun"]

SAVE_KEY = "npc_world_save"
ENABLED_KEY = "npc_world_enabled"

CLASSES = {
    "warrior": ("Воин", {"power": 5, "mind": 2, "will": 3}),
    "mage": ("Маг", {"power": 2, "mind": 5, "will": 3}),
    "rogue": ("Убийца", {"power": 4, "mind": 3, "will": 3}),
    "paladin": ("Паладин", {"power": 3, "mind": 2, "will": 5}),
    "necromancer": ("Некромант", {"power": 2, "mind": 4, "will": 4}),
}

QUESTS = [
    ("ash_road", "Дорога сквозь пепел", "Исследуй Пепельные земли.", 45, 20),
    ("lost_page", "Потерянная страница", "Отыщи следы старого королевства.", 55, 25),
    ("night_watch", "Ночной дозор", "Одолей обитателя тумана.", 65, 30),
    ("old_shrine", "Забытое святилище", "Исследуй древнее святилище.", 80, 40),
    ("black_gate", "Чёрные врата", "Победи хранителя руин.", 100, 55),
]

ENEMIES = [
    ("Пепельный слизень", 24, 6, 18, 25),
    ("Туманный страж", 32, 8, 25, 35),
    ("Проклятый дух", 40, 10, 32, 45),
    ("Хранитель руин", 55, 13, 45, 60),
]

def new_save():
    return {
        "name": "Путник", "class_id": "warrior", "level": 1, "xp": 0,
        "gold": 30, "hp": 50, "max_hp": 50, "stamina": 20,
        "max_stamina": 20, "points": 0,
        "stats": {"power": 5, "mind": 2, "will": 3},
        "region": "Пепельные земли", "done": [], "active": None,
        "inventory": ["Плащ странника", "Сухой паёк"],
        "wins": 0, "explores": 0,
    }

class NPCWorldRPG(BasePlugin):
    def on_plugin_load(self):
        self.add_on_send_message_hook()
        self.logger.info("NPC WORLD RPG loaded")

    def create_settings(self):
        return [
            Header(text="NPC WORLD RPG"),
            Switch(
                key=ENABLED_KEY, text="Включить NPC WORLD",
                default=True,
                subtext="Главный переключатель. Выключение не удаляет сохранение.",
            ),
            Switch(
                key="npc_world_notifications", text="Игровые уведомления",
                default=True, subtext="Показывать результаты игровых команд.",
            ),
            Text(
                text="Команды",
                subtext=".rpg · .rpg create ИМЯ · .rpg class · .rpg quest · .rpg accept · .rpg explore · .rpg battle · .rpg train · .rpg inventory · .rpg rest · .rpg help",
            ),
            Text(
                text="Сохранение и мультиплеер",
                subtext="Прогресс хранится локально. Совместная игра, гильдии и рейды появятся после подключения сервера.",
            ),
        ]

    def load_game(self):
        raw = self.get_setting(SAVE_KEY, "")
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and "level" in data:
                    return data
            except Exception:
                self.logger.exception("Invalid NPC WORLD save")
        return new_save()

    def save_game(self, data):
        self.set_setting(SAVE_KEY, json.dumps(data, ensure_ascii=False))

    def notify(self, message, success=False):
        if not self.get_setting("npc_world_notifications", True):
            return
        try:
            if success:
                BulletinHelper.show_success(message)
            else:
                BulletinHelper.show_info(message)
        except Exception:
            self.logger.info(message)

    def xp_required(self, level):
        return 100 + (level - 1) * 45

    def add_xp(self, data, amount):
        data["xp"] += amount
        messages = []
        while data["level"] < 100 and data["xp"] >= self.xp_required(data["level"]):
            data["xp"] -= self.xp_required(data["level"])
            data["level"] += 1
            data["points"] += 2
            data["max_hp"] += 5
            data["hp"] = data["max_hp"]
            data["max_stamina"] += 2
            data["stamina"] = data["max_stamina"]
            messages.append("Новый уровень: %d! Получено 2 очка характеристик." % data["level"])
        return messages

    def status(self, data):
        class_name = CLASSES.get(data["class_id"], CLASSES["warrior"])[0]
        return (
            "☾ NPC WORLD ☽\n%s · %s\nУровень: %d · XP: %d/%d\n"
            "HP: %d/%d · Выносливость: %d/%d\n"
            "Сила: %d · Разум: %d · Воля: %d\n"
            "Золото: %d · Очки развития: %d\nРегион: %s\n"
            "Победы: %d · Исследования: %d"
        ) % (
            data["name"], class_name, data["level"], data["xp"],
            self.xp_required(data["level"]), data["hp"], data["max_hp"],
            data["stamina"], data["max_stamina"], data["stats"]["power"],
            data["stats"]["mind"], data["stats"]["will"], data["gold"],
            data["points"], data["region"], data["wins"], data["explores"],
        )

    def help_text(self):
        return (
            "☾ NPC WORLD — КОМАНДЫ ☽\n"
            ".rpg — персонаж\n"
            ".rpg create ИМЯ — создать героя\n"
            ".rpg class warrior|mage|rogue|paladin|necromancer\n"
            ".rpg quest — посмотреть следующее задание\n"
            ".rpg accept — принять задание\n"
            ".rpg explore — исследовать регион\n"
            ".rpg battle — сразиться с монстром\n"
            ".rpg complete — сдать задание после действия\n"
            ".rpg train power|mind|will — потратить очко\n"
            ".rpg inventory — инвентарь\n"
            ".rpg rest — восстановить HP и выносливость за 10 золота\n"
            ".rpg help — помощь\n\n"
            "Команды не отправляются в чат собеседнику."
        )

    def handle_command(self, message):
        args = message.strip().split()
        if len(args) == 1 or (len(args) > 1 and args[1].lower() in ("help", "?")):
            return self.help_text()

        data = self.load_game()
        cmd = args[1].lower()

        if cmd == "create":
            if len(args) < 3:
                return "Использование: .rpg create ИМЯ"
            data = new_save()
            data["name"] = " ".join(args[2:])[:24]
            self.save_game(data)
            return "Герой %s создан. Добро пожаловать в Эльдрагор! Выбери класс: .rpg class" % data["name"]

        if cmd == "class":
            if len(args) < 3:
                return "Классы: warrior, mage, rogue, paladin, necromancer"
            key = args[2].lower()
            if key not in CLASSES:
                return "Неизвестный класс. Доступно: warrior, mage, rogue, paladin, necromancer."
            data["class_id"] = key
            data["stats"] = dict(CLASSES[key][1])
            self.save_game(data)
            return "Выбран класс: %s." % CLASSES[key][0]

        if cmd in ("stats", "status"):
            return self.status(data)

        if cmd == "quest":
            if data["active"]:
                q = data["active"]
                return "📜 %s\n%s\nНаграда: %d XP, %d золота.\nСдать: .rpg complete" % (q["name"], q["desc"], q["xp"], q["gold"])
            for q in QUESTS:
                if q[0] not in data["done"]:
                    return "Следующее задание: %s\n%s\nНаграда: %d XP, %d золота.\nПринять: .rpg accept" % (q[1], q[2], q[3], q[4])
            return "Все задания первой главы завершены."

        if cmd == "accept":
            if data["active"]:
                return "Сначала заверши текущее задание."
            for q in QUESTS:
                if q[0] not in data["done"]:
                    data["active"] = {"id": q[0], "name": q[1], "desc": q[2], "xp": q[3], "gold": q[4]}
                    self.save_game(data)
                    return "Задание принято: %s\n%s" % (q[1], q[2])
            return "Нет доступных заданий в этой главе."

        if cmd == "explore":
            if data["stamina"] < 3:
                return "Недостаточно выносливости. Используй .rpg rest."
            data["stamina"] -= 3
            data["explores"] += 1
            event = random.choice([
                ("Ты находишь дорожный сундук.", 12, 18),
                ("В руинах обнаружен тайник.", 18, 22),
                ("Ты изучаешь древнюю надпись.", 5, 28),
                ("Туман скрывает добычу, но опыт получен.", 0, 12),
            ])
            data["gold"] += event[1]
            gained = self.add_xp(data, event[2])
            self.save_game(data)
            return "🗺️ %s\n+%d золота · +%d XP\n%s" % (event[0], event[1], event[2], "\n".join(gained))

        if cmd == "battle":
            if data["stamina"] < 5:
                return "Недостаточно выносливости. Используй .rpg rest."
            name, enemy_hp, enemy_attack, gold, xp = random.choice(ENEMIES)
            attack = data["stats"]["power"] + data["level"] // 3 + random.randint(3, 9)
            enemy_hp -= attack
            if enemy_hp <= 0:
                data["stamina"] -= 5
                data["wins"] += 1
                data["gold"] += gold
                gained = self.add_xp(data, xp)
                self.save_game(data)
                return "⚔️ Победа! Противник: %s\n+%d XP · +%d золота\n%s" % (name, xp, gold, "\n".join(gained))
            damage = max(1, enemy_attack - data["stats"]["will"] // 2)
            data["hp"] = max(0, data["hp"] - damage)
            data["stamina"] -= 5
            if data["hp"] == 0:
                data["hp"] = max(1, data["max_hp"] // 2)
                data["gold"] = max(0, data["gold"] - 5)
                outcome = "Ты потерпел поражение и вернулся в убежище. Потеряно 5 золота."
            else:
                outcome = "Противник ранил тебя на %d HP. Он пока не повержен." % damage
            self.save_game(data)
            return "⚔️ Враг: %s\n%s\nHP: %d/%d" % (name, outcome, data["hp"], data["max_hp"])

        if cmd == "complete":
            q = data["active"]
            if not q:
                return "Нет активного задания. Используй .rpg quest."
            if data["explores"] < 1 and data["wins"] < 1:
                return "Сначала исследуй регион или победи врага."
            data["gold"] += q["gold"]
            gained = self.add_xp(data, q["xp"])
            data["done"].append(q["id"])
            data["active"] = None
            self.save_game(data)
            return "☑ Задание завершено: %s\n+%d XP · +%d золота\n%s" % (q["name"], q["xp"], q["gold"], "\n".join(gained))

        if cmd == "train":
            if len(args) < 3 or args[2] not in ("power", "mind", "will"):
                return "Использование: .rpg train power|mind|will"
            if data["points"] < 1:
                return "Нет очков развития. Получи новый уровень."
            stat = args[2]
            data["stats"][stat] += 1
            data["points"] -= 1
            self.save_game(data)
            return "%s повышена до %d. Осталось очков: %d." % (stat, data["stats"][stat], data["points"])

        if cmd == "inventory":
            return "🎒 ИНВЕНТАРЬ\n" + "\n".join("• " + item for item in data["inventory"]) + "\nЗолото: %d" % data["gold"]

        if cmd == "rest":
            if data["gold"] < 10:
                return "Для отдыха нужно 10 золота."
            data["gold"] -= 10
            data["hp"] = data["max_hp"]
            data["stamina"] = data["max_stamina"]
            self.save_game(data)
            return "Ты отдохнул в убежище. HP и выносливость восстановлены."

        return "Неизвестная команда. Напиши .rpg help."

    def on_send_message_hook(self, account, params):
        if not self.get_setting(ENABLED_KEY, True):
            return HookResult()
        message = getattr(params, "message", None)
        if not isinstance(message, str) or not message.strip().lower().startswith(".rpg"):
            return HookResult()
        try:
            result = self.handle_command(message)
            self.notify(result, success=("победа" in result.lower() or "завершено" in result.lower() or "создан" in result.lower()))
        except Exception as exc:
            self.logger.exception("NPC WORLD command error")
            self.notify("Ошибка NPC WORLD: %s" % str(exc))
        return HookResult(strategy=HookStrategy.CANCEL)
