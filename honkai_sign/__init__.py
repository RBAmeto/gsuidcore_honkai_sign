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

sv_hk_sign = SV("崩坏3米游社签到")
sv_hk_sign_config = SV("崩坏3米游社签到配置", pm=1)


SIGN_PATH = os.path.join(os.path.dirname(__file__), "./sign_on.json")


def load_data():
    if not os.path.exists(SIGN_PATH):
        with open(SIGN_PATH, "w", encoding="utf8") as f:
            json.dump({}, f)
            return {}
    with open(SIGN_PATH, "r", encoding="utf8") as f:
        data: dict = json.load(f)
        return data


def save_data(data):
    with open(SIGN_PATH, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



@sv_hk_sign.on_prefix(('bh开启','bh关闭'))
async def switch_autosign(bot: Bot, ev: Event):
    """自动签到开关"""
    today = datetime.today().day
    qid = str(ev.user_id)
    gid = str(ev.group_id)
    bid = str(ev.bot_id)
    config_name = ev.text
    sign_data = load_data()
    if not config_name =='自动签到':
        return
    if ev.command == 'bh关闭':
        if not qid in sign_data:
            return
        sign_data.pop(qid)
        save_data(sign_data)
        await bot.send(f"[CQ:at,qq={qid}]崩3签到已关闭.")
        return
    flag = False
    try:
        result,flag = await until.sign_bh3(qid)
    except Exception as e: 
        print(e)
    if flag:
        today = datetime.today().day
        sign_data.update({qid: {"bid":bid,"gid": gid, "date": today, "status": True, "result": result}})
        save_data(sign_data)
        await bot.send(result)
    else:
        await bot.send(f"[CQ:at,qq={qid}]签到失败")






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
            logger.warning(f'[崩3签到]群 {gid} 推送失败!错误信息:{e}')
    return


@scheduler.scheduled_job("cron", hour="0", minute="10,40")
async def schedule_sign():
    today = datetime.today().day
    sign_data = load_data()
    cnt = 0
    sum = len(sign_data)
    for qid in sign_data:
        await asyncio.sleep(5)
        if sign_data[qid].get("date") != today or not sign_data[qid].get("status"):
            flag = False
            bid = sign_data[qid].get("bid")
            try:
                result,flag = await until.sign_bh3(qid,bid)
                print(result)
            except Exception as e: 
                print(e)
            gid = sign_data[qid].get("gid")
            if flag:
                today = datetime.today().day
                sign_data.update({qid: {"bid":bid,"gid": gid, "date": today, "status": True, "result": result}})
                save_data(sign_data)
                await send_notice(bid,gid, result)
                cnt += 1
            else:
                await send_notice(bid,gid, f"[CQ:at,qq={qid}] 签到失败{result}")
    return cnt, sum


@sv_hk_sign_config.on_fullmatch("崩3全部重签")
async def reload_sign(bot: Bot, ev: Event):
    await bot.send("开始重执行。")
    try:
        cnt, sum = await schedule_sign()
    except:
        cnt, sum = await schedule_sign()
    await bot.send(f"重执行完成，状态刷新{cnt}条，共{sum}条")
