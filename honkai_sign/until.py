import copy
import random
import asyncio
import re

from gsuid_core.gss import gss
from ..gsuid_utils.api.mys.request import _HEADER
from ..gsuid_utils.api.mys.tools import random_hex,get_web_ds_token
from ..utils.mys_api import mys_api
from ..utils.database import get_sqla
web_api = "https://api-takumi.mihoyo.com"
honkai3rd_Act_id = "e202207181446311"
honkai3rd_checkin_rewards = f'{web_api}/event/luna/home?lang=zh-cn&act_id={honkai3rd_Act_id}'
honkai3rd_Is_signurl = web_api + "/event/luna/info?lang=zh-cn&act_id={}&region={}&uid={}"
honkai3rd_Sign_url = web_api + "/event/luna/sign"
account_Info_url = web_api + "/binding/api/getUserGameRolesByCookie?game_biz="




async def get_account_list(cookie,game_id= "bh3_cn") -> list:
    print(f"正在获取米哈游账号绑定的{game_id}账号列表...")
    HEADER = copy.deepcopy(_HEADER)
    HEADER['Cookie'] = cookie
    HEADER['DS'] = get_web_ds_token(True)
    temp_list = []
    data = await mys_api._mys_request(
            url=account_Info_url+ game_id,
            method='GET',
            header=HEADER
        )
    if data["retcode"] != 0:
        print(f"获取{game_id}账号列表失败！")
    for i in data["data"]["list"]:
        temp_list.append([i["nickname"], i["game_uid"], i["region"]])
    print(f"已获取到{len(temp_list)}个{game_id}账号信息")
    return temp_list



async def sign_bh3(qid,bot_id = "onebot"):
    sqla = get_sqla(bot_id)
    uid = await sqla.get_bind_uid(qid)
    return_data = f"[CQ:at,qq={qid}] "
    flag = False
    if uid is None:
        return return_data + "你没有绑定过原神uid嗷~",flag
    cookie = await mys_api.get_ck(uid, 'OWNER')
    if cookie is None:
        return return_data + "你没有绑定过Cookies噢~",flag
    account_list = await get_account_list(cookie)
    # print(account_list)
    if len(account_list) == 0:
        return return_data + "未获取到崩坏3账号信息",flag
    checkin_rewards = await get_checkin_rewards()
    for i in account_list:
        match = "^玩家[0-9]{8,9}"
        if re.match(match, i[0]):
            continue
        is_data = await is_sign(region = i[2], uid = i[1], cookie = cookie)
        if is_data["is_sign"]:
            getitem = checkin_rewards[int(is_data['total_sign_day']) - 1]
            return_data += f"舰长:{i[0]}今天已经签到过了~\r\n今天获得的奖励是{getitem['name']}x{getitem['cnt']}\n"
            flag = True
            return return_data,flag
        elif is_data["is_sign"] == False:
            Header = {}
            for index in range(4):
                # 进行一次签到
                sign_data = await sign(uid=i[1], server_id = i[2], cookie = cookie, Header=Header)
                # print(sign_data)
                # 检测数据
                if sign_data and 'data' in sign_data and sign_data['data']:
                    if 'risk_code' in sign_data['data']:
                        if sign_data['data']['risk_code'] == 375 or sign_data['data']['risk_code'] == 5001:
                        # 出现校验码                       
                            gt = sign_data['data']['gt']
                            ch = sign_data['data']['challenge']
                            vl, ch = await mys_api._pass(gt, ch, Header)
                            if vl:
                                delay = 1
                                Header['x-rpc-challenge'] = ch
                                Header['x-rpc-validate'] = vl
                                Header['x-rpc-seccode'] = f'{vl}|jordan'
                                print(f'[签到] {i[0]} 已获取验证码, 等待时间{delay}秒')
                                await asyncio.sleep(delay)
                            else:
                                delay = 300 + random.randint(1, 120)
                                print(f'[签到] {i[0]} 未获取验证码,等待{delay}秒后重试...')
                                await asyncio.sleep(delay)
                            continue
                        else:
                            if index == 0:
                                print(f'[签到] {i[0]} 该用户无校验码!')
                            else:
                                print(f'[签到] [无感验证] {i[0]} 该用户重试 {index} 次验证成功!')
                            flag = True
                            getitem = checkin_rewards[int(is_data['total_sign_day']) - 1 + 1]
                            return_data += f"舰长:{i[0]}签到成功~\r\n今天获得的奖励是{getitem['name']}x{getitem['cnt']}\n"
                            break
                    else:
                        # 重试超过阈值
                        print('[签到] 超过请求阈值...')
                        return_data += f"舰长:{i[0]}签到失败~出现验证码\r\n{sign_data['data'].text}\n"
                # 签到失败
            else:
                return_data += f"舰长:{i[0]}签到失败~"
        else:
            return_data += f"舰长:{i[0]}签到失败\r\n{is_data.text}\n"
    return return_data,flag


async def get_checkin_rewards():
    print("正在获取签到奖励列表...")
    data = await mys_api._mys_request(
            url=honkai3rd_checkin_rewards,
            method='GET',
            header=_HEADER
            )
    if data["retcode"] != 0:
        print("获取签到奖励列表失败")
        print(data.text)
    return data["data"]["awards"]

async def is_sign(region: str, uid: str,cookie) -> dict:
    url = honkai3rd_Is_signurl.format(honkai3rd_Act_id, region, uid)
    HEADER = copy.deepcopy(_HEADER)
    HEADER['Cookie'] = cookie
    data = await mys_api._mys_request(
            url=url,
            method='GET',
            header=HEADER
            )
    # print(data)
    if data["retcode"] != 0:
        print("获取账号签到信息失败！")
        print(data)
    return data["data"]

async def sign(uid,server_id = "pc01", cookie = None ,Header={}):
    HEADER = copy.deepcopy(_HEADER)
    HEADER['Cookie'] = cookie
    HEADER['x-rpc-device_id'] = random_hex(32)
    HEADER['x-rpc-app_version'] = '2.44.1'
    HEADER['x-rpc-client_type'] = '5'
    HEADER['X_Requested_With'] = 'com.mihoyo.hyperion'
    HEADER['DS'] = get_web_ds_token(True)
    HEADER['Referer'] = ('https://webstatic.mihoyo.com/bbs/event/signin/bh3/index.html?bbs_auth_required' \
                        f'=true&act_id={honkai3rd_Act_id}&bbs_presentation_style=fullscreen' \
                        '&utm_source=bbs&utm_medium=mys&utm_campaign=icon')
    HEADER.update(Header)
    data = await mys_api._mys_request(
        url=honkai3rd_Sign_url,
        method='POST',
        header=HEADER,
        data={
            'act_id': honkai3rd_Act_id,
            'uid': uid,
            'region': server_id,
        },
    )
    return data
