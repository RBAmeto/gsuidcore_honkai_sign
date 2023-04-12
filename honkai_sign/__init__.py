import asyncio
import json
import os
from datetime import datetime
# import honkai3rd
# import setting
from . import until

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event
# from ..utils.database import get_sqla
# from ..utils.error_reply import UID_HINT
from gsuid_core.gss import gss
from gsuid_core.logger import logger
from gsuid_core.aps import scheduler

sv_hk_sign = SV("崩坏3米游社签到")
sv_hk_sign_config = SV("崩坏3米游社签到配置", pm=1)
# _bot = sv.bot


# async def autosign(hk3: Honkai3rd, qid: str):
#     sign_data = load_data()
#     today = datetime.today().day
#     try:
#         result_list = await hk3.sign_account()
#         print(result_list)
#     except Exception as e:
#         sign_data.update({qid: {"date": today, "status": False, "result": None}})
#         return f"{e}\n自动签到失败."
#     ret_list = ""
#     ret_list += result_list
#     print(ret_list)
#     sign_data.update({qid: {"date": today, "status": True, "result": ret_list}})
#     save_data(sign_data)
#     return ret_list


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


# async def check_cookie(qid: str):
#     uid = await select_db(qid, mode='uid')
#     cookie = await owner_cookies(uid)
#     if not cookie:
#         return f"自动签到需要绑定cookie,发送'bhf?'查看如何绑定."
#     hk3 = Honkai3rd(cookie=cookie)
#     try:
#         role_info = hk3.roles_info
#     except GenshinHelperException as e:
#         return f"{e}\ncookie不可用,请重新绑定."
#     if not role_info:
#         return f"未找到崩坏3角色信息,请确认cookie对应账号是否已绑定崩坏3角色."
#     return hk3


# @sv.on_prefix(r"bh(开启|关闭|on|off)?\s?自动签到")
@sv_hk_sign.on_prefix(('bh开启','bh关闭'))
async def switch_autosign(bot: Bot, ev: Event):
    """自动签到开关"""
    today = datetime.today().day
    qid = str(ev.user_id)
    gid = str(ev.group_id)
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
        sign_data.update({qid: {"bid":ev.bot_id,"gid": gid, "date": today, "status": True, "result": result}})
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
            try:
                result,flag = await until.sign_bh3(qid)
                print(result)
            except Exception as e: 
                print(e)
            gid = sign_data[qid].get("gid")
            bid = sign_data[qid].get("bid")
            if flag:
                today = datetime.today().day
                sign_data.update({qid: {"bid":bid,"gid": gid, "date": today, "status": True, "result": result}})
                save_data(sign_data)
                await send_notice(bid,gid, result)
                cnt += 1
            else:
                await send_notice(bid,gid, f"[CQ:at,qq={qid}] 签到失败")
    return cnt, sum


@sv_hk_sign_config.on_fullmatch("崩3全部重签")
async def reload_sign(bot: Bot, ev: Event):
    await bot.send("开始重执行。")
    try:
        cnt, sum = await schedule_sign()
    except:
        cnt, sum = await schedule_sign()
    await bot.send(f"重执行完成，状态刷新{cnt}条，共{sum}条")

# @sv.on_prefix("删除uid")
# async def delete_uid(bot: HoshinoBot, ev: CQEvent):
#     if not priv.check_priv(ev, priv.SUPERUSER):
#         return
#     qid = str(ev.message.extract_plain_text()).strip()
#     if not qid.isnumeric():
#         await bot.send(ev, "参数错误")
#         return
#     im = await delete_cookies(qid)
#     await bot.send(ev, im)


# @sv.on_prefix("gs拉黑")
# async def delete_uid(bot: HoshinoBot, ev: CQEvent):
#     if not priv.check_priv(ev, priv.SUPERUSER):
#         return
#     qid = str(ev.message.extract_plain_text()).strip()
#     if not qid.isnumeric():
#         await bot.send(ev, "参数错误")
#         return
#     user_id = int(qid)
#     uid_list = await select_db(user_id,'list')
#     im=""
#     if len(uid_list) >= 1:
#         for i in uid_list:
#             im += await delete_db(user_id, {'UID': i})
#             im += await delete_cookies(i)
#             im += await set_config_func(
#                 config_name="自动签到",
#                 uid=i,  # type: ignore
#                 qid=qid,  # type: ignore
#                 option='off',
#                 query = 'CLOSED',
#                 is_admin=True,
#             )
#             im += await set_config_func(
#                 config_name="推送",
#                 uid=i,  # type: ignore
#                 qid=qid,  # type: ignore
#                 option='off',
#                 query = 'CLOSED',
#                 is_admin=True,
#             )
#             im += await set_config_func(
#                 config_name="自动米游币",
#                 uid=i,  # type: ignore
#                 qid=qid,  # type: ignore
#                 option='off',
#                 query = 'CLOSED',
#                 is_admin=True,
#             )
#     await bot.send(ev, im)