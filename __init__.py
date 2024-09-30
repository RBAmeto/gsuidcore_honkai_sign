import asyncio
import json
import os
from datetime import datetime
from . import until

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.gss import gss
from gsuid_core.logger import logger
from gsuid_core.aps import scheduler

sv_bh_sign = SV("崩坏3米游社签到")
sv_bh_sign_config = SV("崩坏3米游社签到配置", pm=1)


SIGN_PATH_bh3rd = os.path.join(os.path.dirname(__file__), "./sign_on.json")
SIGN_PATH_bh2 = os.path.join(os.path.dirname(__file__), "./sign_on_bh2.json")

def load_data(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf8") as f:
            json.dump({}, f)
            return {}
    with open(path, "r", encoding="utf8") as f:
        data: dict = json.load(f)
        return data


def save_data(path, data):
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



@sv_bh_sign.on_prefix(('崩3开启','崩3关闭','崩2开启','崩2关闭'))
async def switch_autosign(bot: Bot, ev: Event):
    """自动签到开关"""
    today = datetime.today().day
    qid = str(ev.user_id)
    gid = str(ev.group_id)
    bid = str(ev.bot_id)
    config_name = ev.text
    
    if not config_name =='自动签到':
        return
    if ev.command.startswith('崩3'):
        sign_path = SIGN_PATH_bh3rd
        game_id = "bh3_cn"
    elif ev.command.startswith('崩2'):
        sign_path = SIGN_PATH_bh2
        game_id = "bh2_cn"
    sign_data = load_data(sign_path)
    if ev.command.endswith('关闭') :
        if not qid in sign_data:
            return
        sign_data.pop(qid)
        save_data(sign_path, sign_data)
        await bot.send(f"[CQ:at,qq={qid}]{ev.command}自动签到已执行.")
        return
    flag = False
    result = ""
    if ev.command.endswith('开启') :
        try:
            result,flag = await until.sign(qid, bid, game_id)
            print(result)
        except Exception as e: 
            print(e)
    if flag:
        today = datetime.today().day
        sign_data.update({qid: {"bid":bid,"gid": gid, "date": today, "status": True, "result": result}})
        save_data(sign_path, sign_data)
        await bot.send(result)
        await asyncio.sleep(60)
    else:
        await bot.send(f"[CQ:at,qq={qid}]签到失败{result}")




async def send_notice(bid: str,gid: str, context: str):
    try:
        for bot_id in gss.active_bot:
            await gss.active_bot[bot_id].target_send(
                    context,
                    'group',
                    gid,
                    bid,
                    '',
                    '',
                )
    except Exception as e:
        logger.warning(f'[崩坏签到]群 {gid} 推送失败!错误信息:{e}')
    return


async def schedule_sign(game_id = "bh3_cn"):
    if game_id == "bh3_cn" :
        sign_path = SIGN_PATH_bh3rd
    else:
        sign_path = SIGN_PATH_bh2
    today = datetime.today().day
    sign_data = load_data(sign_path)
    cnt = 0
    sum = len(sign_data)
    for qid in sign_data:
        await asyncio.sleep(10)
        if sign_data[qid].get("date") != today or not sign_data[qid].get("status"):
            flag = False
            bid = sign_data[qid].get("bid")
            result = ""
            try:
                result,flag = await until.sign(qid,bid,game_id)
                print(result)
            except Exception as e: 
                result = str(e)[:20]
            gid = sign_data[qid].get("gid")
            if flag:
                today = datetime.today().day
                sign_data.update({qid: {"bid":bid,"gid": gid, "date": today, "status": True, "result": result}})
                save_data(sign_path, sign_data)
                await send_notice(bid,gid, result)
                cnt += 1
            else:
                await send_notice(bid,gid, f"[CQ:at,qq={qid}] 签到失败{result}")
    return cnt, sum


@sv_bh_sign_config.on_suffix("全部重签")
async def reload_sign(bot: Bot, ev: Event):
    if ev.text == "崩3":
        game_id = "bh3_cn"
    elif ev.text == "崩2":
        game_id = "bh2_cn"
    elif ev.text == "崩坏":
        await schedule_sign_all()
        return
    else:
        return
    await bot.send("开始重执行。")
    cnt=0
    sum=0
    try:
        cnt, sum = await schedule_sign(game_id)
    except:
        cnt, sum = await schedule_sign(game_id)
    await bot.send(f"{ev.text}重执行完成，状态刷新{cnt}条，共{sum}条")


@scheduler.scheduled_job("cron", hour="0", minute="30")
async def schedule_sign_all():
    await schedule_sign("bh3_cn")
    await schedule_sign("bh2_cn")
    
