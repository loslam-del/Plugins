# NPC WORLD RPG — story-driven dark fantasy RPG for AyuGram/exteraGram
# Version 1.0.0 — local single-player campaign.
# Online co-op, guilds and live PvP require a shared backend and are intentionally not simulated.

import json
import random
import re

from base_plugin import BasePlugin, HookResult, HookStrategy
from ui.settings import Header, Switch, Text
from ui.bulletin import BulletinHelper

__id__ = "npc_world_rpg"
__name__ = "NPC WORLD RPG"
__description__ = "Сюжетная тёмное фэнтези RPG: кампания, выборы, боссы, экипировка и развитие."
__author__ = "loslam-del"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__app_version__ = ">=12.5.1"
__sdk_version__ = ">=1.4.4.3"
__category__ = ["fun"]

SAVE_KEY = "npc_world_save"
ENABLED_KEY = "npc_world_enabled"

CLASSES = {
    "warrior": ("Воин", {"power": 6, "mind": 2, "will": 4}, "Сильные удары и крепкая защита."),
    "mage": ("Маг", {"power": 2, "mind": 7, "will": 3}, "Высокий урон заклинаниями."),
    "rogue": ("Плут", {"power": 5, "mind": 4, "will": 3}, "Критические удары и ловкость."),
    "paladin": ("Паладин", {"power": 4, "mind": 3, "will": 6}, "Выживаемость и лечение."),
    "necromancer": ("Некромант", {"power": 3, "mind": 6, "will": 4}, "Магия праха и истощение врагов."),
}

REGIONS = [
    "Пепельные земли", "Шепчущий лес", "Затонувший край",
    "Чёрный собор", "Трон Пустоты"
]

QUESTS = [
    {"id":"q01","chapter":1,"region":0,"name":"Следы в пепле","objective":"explore","target":1,"xp":45,"gold":20,
     "intro":"ЭЛЬДРАГОР, 413 ГОД ПОСЛЕ ПАДЕНИЯ.\n\nТы приходишь в себя у дороги, покрытой серым пеплом. Над горизонтом висит багровое солнце. На запястье — незнакомый знак, который пульсирует в такт далёкому колоколу.\n\nСтарик в дорожном плаще шепчет: «Если колокол прозвучит семь раз, мёртвые вспомнят свои имена. И тогда мир закончится». Он указывает на следы, ведущие к заброшенному лагерю.\n\nНайди лагерь. Используй .rpg explore."},
    {"id":"q02","chapter":1,"region":0,"name":"Тот, кто не дышит","objective":"wins","target":1,"xp":65,"gold":25,
     "intro":"В лагере ты находишь дневник дозорного. Последняя запись оборвана: «Они идут за светом… не за людьми». Из-под обломков поднимается Пепельный ходок. Старик отступает: «Теперь ты понял, почему я не ушёл?»\n\nПобеди противника командой .rpg battle."},
    {"id":"q03","chapter":1,"region":0,"name":"Колокол без языка","objective":"boss","target":1,"xp":100,"gold":50,
     "intro":"За лагерем стоит башня без дверей. Внутри висит колокол, но у него нет языка. Его охраняет Пепельный рыцарь — бывший капитан королевской стражи.\n\nПодготовься и используй .rpg battle. В бою атакуй командой .rpg attack."},
    {"id":"q04","chapter":2,"region":1,"name":"Дорога шёпота","objective":"explore","target":2,"xp":75,"gold":35,
     "intro":"Колокол умолкает. На его поверхности проступает карта Шепчущего леса. Старик признаётся, что когда-то служил королевскому архивариусу.\n\n«Знак на твоей руке — печать наследника. Но наследник может спасти королевство… или открыть ему могилу».\n\nДоберись до лесного святилища: .rpg explore."},
    {"id":"q05","chapter":2,"region":1,"name":"Долг лесных духов","objective":"wins","target":2,"xp":90,"gold":45,
     "intro":"Духи леса не доверяют людям. Они принимают тебя за вора, укравшего их имена. Два стража преграждают путь. Докажи, что ты не слуга Пустоты.\n\nПобеди двух врагов: .rpg battle."},
    {"id":"q06","chapter":2,"region":1,"name":"Матерь корней","objective":"boss","target":1,"xp":140,"gold":70,
     "intro":"В центре святилища корни образуют лицо древней Матери. Она знает правду о печати: семь колоколов удерживают Пустоту, а последний звон разрушит границу миров.\n\nМатерь не отдаст ключ добровольно. .rpg battle"},
    {"id":"q07","chapter":3,"region":2,"name":"Город под водой","objective":"explore","target":2,"xp":110,"gold":55,
     "intro":"Ключ открывает путь к Затонувшему краю. Под водой сохранились улицы старой столицы. В затопленном архиве ты находишь имя человека, создавшего печать: король Эдран.\n\nИсследуй затонувшие руины: .rpg explore."},
    {"id":"q08","chapter":3,"region":2,"name":"Память утопленников","objective":"wins","target":3,"xp":130,"gold":65,
     "intro":"Мёртвые жители города повторяют одну фразу: «Король не умер. Он ждёт». Их воспоминания охраняют три утопленника.\n\nПобеди трёх врагов: .rpg battle."},
    {"id":"q09","chapter":3,"region":2,"name":"Адмирал без лица","objective":"boss","target":1,"xp":180,"gold":90,
     "intro":"На дне гавани стоит флагманский корабль. Его капитан — Адмирал без лица — хранит проход к Чёрному собору.\n\nСразись с ним: .rpg battle."},
    {"id":"q10","chapter":4,"region":3,"name":"Семь ступеней","objective":"explore","target":2,"xp":150,"gold":75,
     "intro":"В Чёрном соборе семь колоколов звучат сами по себе. Каждый звон показывает тебе чужую жизнь: король, который боялся смерти; маги, которые предали его; люди, которых забыли принести в жертву.\n\nПоднимись по собору: .rpg explore."},
    {"id":"q11","chapter":4,"region":3,"name":"Последний исповедник","objective":"boss","target":1,"xp":220,"gold":110,
     "intro":"Исповедник снимает маску. Под ней — лицо старика, который встретил тебя у дороги. «Я не мог сказать правду. Я был первым, кто позвонил в колокол».\n\nОн просит остановить его. .rpg battle."},
    {"id":"q12","chapter":5,"region":4,"name":"Король Пустоты","objective":"boss","target":1,"xp":350,"gold":200,
     "intro":"За последними вратами находится трон. На нём сидит Эдран — король, который связал свою душу с Пустотой.\n\n«Ты пришёл решить судьбу мира. Но сначала реши, кем являешься сам».\n\nЭто финальная битва. Победи короля: .rpg battle."},
]

ENEMIES = {
    0: [("Пепельный ходок",34,7,15,22),("Голодный ворон",28,8,12,20)],
    1: [("Лесной одержимый",48,10,22,30),("Корневой страж",55,9,25,34)],
    2: [("Утопленник",66,12,30,40),("Солдат глубин",72,13,32,44)],
    3: [("Соборный фанатик",85,15,40,55),("Проклятый рыцарь",95,17,45,60)],
    4: [("Тень трона",110,19,55,75)],
}
BOSSES = {
    "q03": ("Пепельный рыцарь",105,14,80,100),
    "q06": ("Матерь корней",145,17,110,140),
    "q09": ("Адмирал без лица",185,20,140,180),
    "q11": ("Последний исповедник",220,22,170,220),
    "q12": ("Эдран, король Пустоты",300,27,300,350),
}
ITEMS = {
    "potion": {"name":"Малое зелье","price":18,"kind":"consumable"},
    "greater_potion": {"name":"Большое зелье","price":45,"kind":"consumable"},
    "iron_sword": {"name":"Железный клинок","price":65,"kind":"weapon","power":3},
    "sage_staff": {"name":"Посох мудреца","price":65,"kind":"weapon","mind":3},
    "rune_armor": {"name":"Рунная броня","price":80,"kind":"armor","will":3},
    "ring": {"name":"Кольцо странника","price":55,"kind":"trinket","hp":12},
}

def new_save():
    return {
        "name":"Путник","class_id":"warrior","level":1,"xp":0,"gold":35,
        "hp":60,"max_hp":60,"stamina":24,"max_stamina":24,"points":0,
        "stats":{"power":6,"mind":2,"will":4},
        "region":0,"quest_index":0,"active":None,"done":[],"progress":0,
        "inventory":["Плащ странника","Сухой паёк","potion"],
        "equipment":{"weapon":None,"armor":None,"trinket":None},
        "flags":{"spared_spirits":None,"trusted_elder":None,"final_choice":None},
        "journal":["Ты очнулся на дороге в Пепельных землях."],
        "wins":0,"explores":0,"battle":None,"ending":None,
    }

class NPCWorldRPG(BasePlugin):
    def on_plugin_load(self):
        self.add_on_send_message_hook()
        self.logger.info("NPC WORLD RPG 1.0 loaded")

    def create_settings(self):
        return [
            Header(text="NPC WORLD RPG — Эльдрагор"),
            Switch(key=ENABLED_KEY,text="Включить игру",default=True,
                   subtext="Выключение команд не удаляет сохранение."),
            Switch(key="npc_world_notifications",text="Игровые уведомления",default=True,
                   subtext="Показывать ответы игры."),
            Text(text="Начало игры",subtext="Напиши .rpg create ИМЯ, затем .rpg class warrior|mage|rogue|paladin|necromancer и .rpg story."),
            Text(text="Сохранение",subtext="Персонаж и сюжетные выборы сохраняются локально на устройстве."),
            Text(text="Мультиплеер",subtext="Эта версия — полноценная одиночная кампания. Для совместной игры нужен отдельный сервер."),
        ]

    def load_game(self):
        raw = self.get_setting(SAVE_KEY,"")
        if raw:
            try:
                data = json.loads(raw)
                base = new_save()
                if isinstance(data,dict):
                    base.update(data)
                    for key in ("stats","equipment","flags"):
                        if not isinstance(base.get(key),dict):
                            base[key] = new_save()[key]
                    return base
            except Exception:
                self.logger.exception("Could not load NPC WORLD save")
        return new_save()

    def save_game(self,data):
        self.set_setting(SAVE_KEY,json.dumps(data,ensure_ascii=False))

    def notify(self,message,success=False):
        if not self.get_setting("npc_world_notifications",True):
            return
        try:
            if success:
                BulletinHelper.show_success(message)
            else:
                BulletinHelper.show_info(message)
        except Exception:
            self.logger.info(message)

    def xp_required(self,level):
        return 100 + (level-1)*55

    def add_xp(self,data,amount):
        data["xp"] += amount
        out=[]
        while data["level"] < 60 and data["xp"] >= self.xp_required(data["level"]):
            data["xp"] -= self.xp_required(data["level"])
            data["level"] += 1
            data["points"] += 2
            data["max_hp"] += 7
            data["max_stamina"] += 2
            data["hp"] = data["max_hp"]
            data["stamina"] = data["max_stamina"]
            out.append("Уровень повышен до %d! +2 очка развития." % data["level"])
        return out

    def item_name(self,key):
        return ITEMS.get(key,{}).get("name",key)

    def gear_bonus(self,data,stat):
        total=0
        for key in data["equipment"].values():
            if key in ITEMS:
                total += ITEMS[key].get(stat,0)
        return total

    def stat(self,data,key):
        return data["stats"].get(key,0)+self.gear_bonus(data,key)

    def status(self,d):
        cls=CLASSES.get(d["class_id"],CLASSES["warrior"])[0]
        return ("☾ ЭЛЬДРАГОР ☽\n%s · %s · Ур. %d\nXP: %d/%d\n"
                "HP: %d/%d · Выносливость: %d/%d\n"
                "Сила: %d · Разум: %d · Воля: %d\n"
                "Золото: %d · Очки развития: %d\nРегион: %s\n"
                "Победы: %d · Исследования: %d") % (
            d["name"],cls,d["level"],d["xp"],self.xp_required(d["level"]),
            d["hp"],d["max_hp"],d["stamina"],d["max_stamina"],
            self.stat(d,"power"),self.stat(d,"mind"),self.stat(d,"will"),
            d["gold"],d["points"],REGIONS[min(max(d["region"],0),4)],
            d["wins"],d["explores"])

    def current_quest(self,d):
        i=d.get("quest_index",0)
        return QUESTS[i] if i < len(QUESTS) else None

    def quest_text(self,d):
        q=self.current_quest(d)
        if not q:
            return "Кампания завершена. Используй .rpg ending, чтобы перечитать свой финал."
        if d.get("active"):
            return ("📜 %s\n%s\nПрогресс: %d/%d\nНаграда: %d XP, %d золота\n"
                    "Действия: .rpg explore / .rpg battle") % (
                q["name"],q["intro"],d["progress"],q["target"],q["xp"],q["gold"])
        return "Следующее задание: %s\n%s\nНаграда: %d XP, %d золота\nПринять: .rpg accept" % (
            q["name"],q["intro"],q["xp"],q["gold"])

    def help_text(self):
        return ("☾ NPC WORLD RPG — КОМАНДЫ ☽\n"
        ".rpg — статус персонажа\n.rpg create ИМЯ — новая игра\n"
        ".rpg story — сюжетная сцена\n.rpg class — выбрать класс\n"
        ".rpg quest — текущее задание\n.rpg accept — начать задание\n"
        ".rpg explore — исследовать область\n.rpg battle — начать бой\n"
        ".rpg attack — атаковать · .rpg defend — защита\n.rpg potion — выпить зелье\n"
        ".rpg choose 1|2 — сюжетный выбор\n.rpg map — карта мира\n"
        ".rpg journal — журнал событий\n.rpg inventory — инвентарь\n"
        ".rpg shop — магазин · .rpg buy ITEM — купить предмет\n"
        ".rpg equip ITEM — экипировать · .rpg skills — развитие\n"
        ".rpg train power|mind|will — потратить очко\n"
        ".rpg rest — восстановиться · .rpg ending — финал\n"
        ".rpg reset — начать заново\n\nВсе команды локальные и не отправляются собеседнику.")

    def add_journal(self,d,line):
        d["journal"].append(line)
        d["journal"]=d["journal"][-30:]

    def start_battle(self,d):
        q=self.current_quest(d)
        if not d.get("active"):
            return "Сначала прими задание: .rpg accept"
        if d.get("battle"):
            return "Бой уже идёт! .rpg attack или .rpg defend"
        if d["stamina"] < 3:
            return "Мало выносливости. Отдохни: .rpg rest"
        if q and q["objective"]=="boss":
            enemy=BOSSES.get(q["id"])
            if not enemy:
                return "Ошибка: босс не найден."
            name,hp,atk,gold,xp=enemy
            boss=True
        else:
            pool=ENEMIES.get(d["region"],ENEMIES[0])
            name,hp,atk,gold,xp=random.choice(pool)
            boss=False
        scale=max(0,d["level"]-1)
        d["battle"]={"name":name,"hp":hp+scale*8,"max_hp":hp+scale*8,
                     "attack":atk+scale*2,"gold":gold,"xp":xp,"boss":boss}
        d["stamina"]-=3
        return "⚔️ На тебя нападает %s!\nHP врага: %d\nТвой ход: .rpg attack" % (name,d["battle"]["hp"])

    def finish_battle(self,d):
        b=d["battle"]
        d["gold"]+=b["gold"]
        d["wins"]+=1
        notes=self.add_xp(d,b["xp"])
        q=self.current_quest(d)
        if q and d.get("active"):
            if q["objective"]=="boss" and b["boss"]:
                d["progress"]=q["target"]
            elif q["objective"]=="wins" and not b["boss"]:
                d["progress"]+=1
        self.add_journal(d,"Победа над: "+b["name"])
        d["battle"]=None
        return "Победа над %s!\n+%d XP · +%d золота\n%s" % (
            b["name"],b["xp"],b["gold"],"\n".join(notes))

    def do_attack(self,d):
        b=d.get("battle")
        if not b:
            return "Сейчас ты не в бою. .rpg battle"
        if d["stamina"] < 1:
            return "Нет выносливости для удара. Используй .rpg potion или .rpg rest"
        d["stamina"]-=1
        power=self.stat(d,"power")
        mind=self.stat(d,"mind")
        cls=d["class_id"]
        base=power*2 + d["level"] + random.randint(2,7)
        if cls in ("mage","necromancer"):
            base += mind*2
        if cls=="rogue" and random.random()<0.25:
            base=int(base*1.8)
            critical=" Критический удар!"
        else:
            critical=""
        b["hp"]=max(0,b["hp"]-base)
        if b["hp"]<=0:
            return self.finish_battle(d)
        damage=max(1,b["attack"]-self.stat(d,"will")//3)
        d["hp"]=max(0,d["hp"]-damage)
        if d["hp"]<=0:
            d["hp"]=max(1,d["max_hp"]//2)
            d["gold"]=max(0,d["gold"]-10)
            d["battle"]=None
            self.add_journal(d,"Поражение в бою; герой вернулся в убежище.")
            return "Ты проиграл бой. Очнулся в убежище с половиной HP. Потеряно 10 золота."
        return ("Ты наносишь %d урона.%s\n%s: %d/%d HP\n"
                "Враг отвечает: -%d HP.\nТвоё HP: %d/%d\nСледующий ход: .rpg attack") % (
            base,critical,b["name"],b["hp"],b["max_hp"],damage,d["hp"],d["max_hp"])

    def handle_command(self,message):
        parts=message.strip().split()
        if len(parts)==1 or parts[1].lower() in ("help","?"):
            return self.help_text()
        cmd=parts[1].lower()
        d=self.load_game()

        if cmd=="create":
            if len(parts)<3:
                return "Напиши: .rpg create ИМЯ"
            d=new_save()
            d["name"]=" ".join(parts[2:])[:24]
            self.save_game(d)
            return "Персонаж %s создан.\nДобро пожаловать в Эльдрагор.\nВыбери класс: .rpg class warrior|mage|rogue|paladin|necromancer\nЗатем начни: .rpg story" % d["name"]

        if cmd=="reset":
            d=new_save()
            self.save_game(d)
            return "Сохранение сброшено. Создай героя: .rpg create ИМЯ"

        if cmd=="class":
            if len(parts)<3:
                return "Классы:\n"+ "\n".join("%s — %s" % (k,v[0]) for k,v in CLASSES.items())
            key=parts[2].lower()
            if key not in CLASSES:
                return "Нет такого класса. Напиши .rpg class"
            if d["level"]>1 or d["done"]:
                return "Класс можно менять только до начала прохождения."
            d["class_id"]=key
            d["stats"]=dict(CLASSES[key][1])
            self.save_game(d)
            return "Выбран класс: %s.\n%s" % (CLASSES[key][0],CLASSES[key][2])

        if cmd in ("status","stats"):
            return self.status(d)
        if cmd=="story":
            if not d["done"] and not d["active"]:
                q=QUESTS[0]
                self.save_game(d)
                return q["intro"]+"\n\nНачни с .rpg accept"
            return self.quest_text(d)
        if cmd=="quest":
            return self.quest_text(d)
        if cmd=="accept":
            q=self.current_quest(d)
            if not q:
                return "Кампания завершена. .rpg ending"
            if d["active"]:
                return "Задание уже активно. .rpg quest"
            d["active"]=True
            d["progress"]=0
            d["region"]=q["region"]
            self.add_journal(d,"Начато задание: "+q["name"])
            self.save_game(d)
            return "📜 Задание начато: "+q["name"]+"\n\n"+q["intro"]

        if cmd=="explore":
            q=self.current_quest(d)
            if not d["active"] or not q:
                return "Сначала прими задание: .rpg accept"
            if q["objective"] not in ("explore",):
                return "Для этого задания нужно другое действие. Посмотри .rpg quest"
            if d["stamina"]<2:
                return "Не хватает выносливости. .rpg rest"
            d["stamina"]-=2
            d["explores"]+=1
            d["progress"]+=1
            found=random.choice(["Ты находишь забытый тайник.","На камне вырезана древняя руна.","В пепле лежит кошель путника.","Ты замечаешь следы неизвестного существа."])
            loot=random.randint(5,14)
            d["gold"]+=loot
            xp=random.randint(8,16)
            levels=self.add_xp(d,xp)
            self.add_journal(d,found)
            self.save_game(d)
            return "%s\n+%d золота · +%d XP\nПрогресс задания: %d/%d\n%s" % (
                found,loot,xp,d["progress"],q["target"],"\n".join(levels))

        if cmd=="battle":
            result=self.start_battle(d)
            self.save_game(d)
            return result
        if cmd=="attack":
            result=self.do_attack(d)
            self.save_game(d)
            return result
        if cmd=="defend":
            if not d.get("battle"):
                return "Ты не в бою."
            damage=max(1,d["battle"]["attack"]//3-self.stat(d,"will")//3)
            d["hp"]=max(1,min(d["max_hp"],d["hp"]-damage+max(0,self.stat(d,"will")//2)))
            d["stamina"]=min(d["max_stamina"],d["stamina"]+2)
            self.save_game(d)
            return "Ты принимаешь защитную стойку. Восстановлено 2 выносливости. HP: %d/%d. Теперь .rpg attack" % (d["hp"],d["max_hp"])

        if cmd=="potion":
            potion="potion" if "potion" in d["inventory"] else ("greater_potion" if "greater_potion" in d["inventory"] else None)
            if not potion:
                return "Нет зелий. Купи в магазине: .rpg shop"
            d["inventory"].remove(potion)
            heal=25 if potion=="potion" else 55
            d["hp"]=min(d["max_hp"],d["hp"]+heal)
            self.save_game(d)
            return "%s использовано. Восстановлено %d HP. Теперь %d/%d." % (ITEMS[potion]["name"],heal,d["hp"],d["max_hp"])

        if cmd=="complete":
            q=self.current_quest(d)
            if not d["active"] or not q:
                return "Нет активного задания."
            if d["progress"]<q["target"]:
                return "Цель ещё не выполнена: %d/%d." % (d["progress"],q["target"])
            d["gold"]+=q["gold"]
            levels=self.add_xp(d,q["xp"])
            d["done"].append(q["id"])
            d["active"]=None
            d["progress"]=0
            d["quest_index"]+=1
            if q["id"]=="q03":
                self.add_journal(d,"Колокол пробудил знак на твоей руке.")
                self.save_game(d)
                return "Задание завершено: %s\n+%d XP · +%d золота\n\nНа обломках колокола появляется видение: две фигуры у алтаря. Одна просит сохранить духов леса, другая — сжечь их ради ключа.\n\nСделай выбор: .rpg choose 1 (пощадить духов) или .rpg choose 2 (забрать силу)." % (q["name"],q["xp"],q["gold"])
            if q["id"]=="q06":
                self.add_journal(d,"Матерь корней рассказала правду о короле.")
                self.save_game(d)
                return "Задание завершено: %s\n+%d XP · +%d золота\n\nМатерь открывает тайну: король Эдран не был захвачен Пустотой — он сам заключил с ней договор.\n\nТы можешь довериться старику или идти один. .rpg choose 1 — довериться, .rpg choose 2 — отказаться." % (q["name"],q["xp"],q["gold"])
            if q["id"]=="q12":
                d["ending"]="sealed" if d["flags"].get("final_choice")=="1" else ("crowned" if d["flags"].get("final_choice")=="2" else "free")
            self.add_journal(d,"Завершено задание: "+q["name"])
            self.save_game(d)
            extra="\n".join(levels)
            if q["id"]=="q12":
                return "Задание завершено: %s\n+%d XP · +%d золота\n\nКампания окончена. .rpg ending" % (q["name"],q["xp"],q["gold"])
            return "Задание завершено: %s\n+%d XP · +%d золота\n%s\nСледующая глава открыта. .rpg quest" % (q["name"],q["xp"],q["gold"],extra)

        if cmd=="choose":
            if len(parts)<3 or parts[2] not in ("1","2"):
                return "Выбери .rpg choose 1 или .rpg choose 2"
            choice=parts[2]
            if "q03" in d["done"] and d["flags"].get("spared_spirits") is None:
                d["flags"]["spared_spirits"]=choice=="1"
                if choice=="1":
                    d["stats"]["will"]+=1
                    outcome="Духи склоняют ветви. Они благословляют тебя: +1 к воле."
                else:
                    d["stats"]["power"]+=1
                    outcome="Ты забираешь силу алтаря: +1 к силе. Лес запоминает твоё решение."
            elif "q06" in d["done"] and d["flags"].get("trusted_elder") is None:
                d["flags"]["trusted_elder"]=choice=="1"
                outcome="Старик идёт с тобой." if choice=="1" else "Ты уходишь один. Старик остаётся у святилища."
            elif "q11" in d["done"] and d["flags"].get("final_choice") is None:
                d["flags"]["final_choice"]=choice
                outcome="Ты выбираешь запечатать Пустоту." if choice=="1" else "Ты решаешь занять трон Эльдрагора."
            else:
                return "Сейчас нет доступного сюжетного выбора. Продолжай .rpg quest"
            self.add_journal(d,"Сюжетный выбор: "+choice)
            self.save_game(d)
            return outcome+"\nВыбор сохранён."

        if cmd=="map":
            q=self.current_quest(d)
            lines=["🗺️ КАРТА ЭЛЬДРАГОРА"]
            for i,name in enumerate(REGIONS):
                mark="✓" if i<d["region"] else ("➤" if i==d["region"] else "🔒")
                lines.append("%s %s" % (mark,name))
            if q:
                lines.append("Текущая цель: "+q["name"])
            return "\n".join(lines)
        if cmd=="journal":
            return "📖 ЖУРНАЛ\n"+"\n".join("• "+x for x in d["journal"][-15:])
        if cmd=="inventory":
            counts={}
            for item in d["inventory"]:
                counts[item]=counts.get(item,0)+1
            gear=d["equipment"]
            lines=["🎒 ИНВЕНТАРЬ"]
            for item,count in counts.items():
                lines.append("%s ×%d" % (self.item_name(item),count))
            lines.append("Оружие: "+self.item_name(gear.get("weapon") or "нет"))
            lines.append("Броня: "+self.item_name(gear.get("armor") or "нет"))
            lines.append("Аксессуар: "+self.item_name(gear.get("trinket") or "нет"))
            lines.append("Золото: %d" % d["gold"])
            return "\n".join(lines)
        if cmd=="shop":
            return "🏚️ ЛАВКА СТРАННИКА\n"+"\n".join(".rpg buy %s — %s (%d золота)" % (k,v["name"],v["price"]) for k,v in ITEMS.items())
        if cmd=="buy":
            if len(parts)<3 or parts[2] not in ITEMS:
                return "Предмет не найден. .rpg shop"
            key=parts[2]
            item=ITEMS[key]
            if d["gold"]<item["price"]:
                return "Не хватает золота. Нужно: %d." % item["price"]
            d["gold"]-=item["price"]
            d["inventory"].append(key)
            self.save_game(d)
            return "Куплено: %s." % item["name"]
        if cmd=="equip":
            if len(parts)<3:
                return "Напиши .rpg equip iron_sword (или другой предмет из магазина)."
            key=parts[2]
            if key not in d["inventory"] or key not in ITEMS or ITEMS[key]["kind"] not in ("weapon","armor","trinket"):
                return "Этого экипируемого предмета нет в инвентаре."
            slot=ITEMS[key]["kind"]
            old=d["equipment"].get(slot)
            if old:
                d["inventory"].append(old)
            d["inventory"].remove(key)
            d["equipment"][slot]=key
            self.save_game(d)
            return "Экипировано: %s." % ITEMS[key]["name"]
        if cmd=="skills":
            return ("🌑 РАЗВИТИЕ\nОчки: %d\nСила: %d — физический урон\nРазум: %d — магический урон\nВоля: %d — защита\n"
                    "Повышение: .rpg train power|mind|will") % (
                d["points"],self.stat(d,"power"),self.stat(d,"mind"),self.stat(d,"will"))
        if cmd=="train":
            if len(parts)<3 or parts[2] not in ("power","mind","will"):
                return "Использование: .rpg train power|mind|will"
            if d["points"]<1:
                return "Нет очков развития. Получи уровень за задания и бои."
            stat=parts[2]
            d["stats"][stat]+=1
            d["points"]-=1
            self.save_game(d)
            return "%s повышена до %d. Осталось очков: %d." % (stat,self.stat(d,stat),d["points"])
        if cmd=="rest":
            d["hp"]=d["max_hp"]
            d["stamina"]=d["max_stamina"]
            d["battle"]=None
            self.save_game(d)
            return "Ты провёл ночь у костра. HP и выносливость восстановлены."
        if cmd=="ending":
            ending=d.get("ending")
            if not ending:
                return "Финал ещё не открыт. Заверши последнюю главу."
            if ending=="sealed":
                return "КОНЦОВКА: ПОСЛЕДНИЙ СТРАЖ\nТы не занял трон. Вместе с духами ты запечатал Пустоту, навсегда оставшись хранителем границы. Колокола замолчали впервые за тысячу лет."
            if ending=="crowned":
                return "КОНЦОВКА: КОРОЛЬ ПЕПЛА\nТы занял опустевший трон и подчинил остатки Пустоты. Эльдрагор выжил, но теперь каждый закон начинается с твоего имени."
            return "КОНЦОВКА: СВОБОДНЫЙ МИР\nТы разрушил печать и отказался от власти. Мир пережил тяжёлую ночь, но впервые получил шанс выбрать собственную судьбу."
        return "Неизвестная команда. Напиши .rpg help"

    def on_send_message_hook(self,account,params):
        if not self.get_setting(ENABLED_KEY,True):
            return HookResult()
        message=getattr(params,"message",None)
        if not isinstance(message,str):
            return HookResult()
        if not re.match(r"^\.rpg(?:\s|$)",message.strip(),re.IGNORECASE):
            return HookResult()
        try:
            result=self.handle_command(message)
            positive=any(word in result.lower() for word in ("победа","завершено","куплено","выбран класс","повышена","кампания окончена"))
            self.notify(result,success=positive)
        except Exception as exc:
            self.logger.exception("NPC WORLD command error")
            self.notify("Ошибка NPC WORLD: %s" % str(exc))
        return HookResult(strategy=HookStrategy.CANCEL)
