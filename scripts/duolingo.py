#!/usr/bin/python
# -*- coding: UTF-8 -*-
import argparse
import json
import os
import pendulum
from notion_helper import NotionHelper
import requests
import utils
from config import xp_properties_type_dict,mistake_properties_type_dict
from dotenv import load_dotenv
from config import (
    TARGET_ICON_URL
)
load_dotenv()
headers = {
    "Accept": "*/*",
    "User-Agent": "request",
}


def get_lastest():
    sorts = [{"property": "日期", "direction": "descending"}]
    response = notion_helper.query(
        database_id=notion_helper.day_database_id, sorts=sorts, page_size=1
    )
    results = response.get("results")
    if len(results) > 0:
        title = utils.get_property_value(
                response.get("results")[0].get("properties").get("标题")
            )
        if title:
            return (
                utils.get_property_value(
                    response.get("results")[0].get("properties").get("标题")
                ),
                response.get("results")[0].get("id"),
            )
        else:
            return ("2011-01-01", None)
    else:
        return ("2011-01-01", None)
def check_exist(id):
    filter = {"property": "ID", "rich_text": {"equals": id}}
    response = notion_helper.query(database_id=notion_helper.mistake_database_id,filter=filter)
    results = response.get("results")
    if(len(results)>0):
        return results[0].get("id")
    else:
        return None



def get_mistakes(id):
    r = requests.get(f"https://android-api.duolingo.cn/2017-06-30/mistakes/users/{duolingo_id}/courses/{id}?fields=&includeSpeaking=true&limit=100&requestType=INBOX&includeListening=true",headers=headers)
    if r.ok:
        for item in r.json():
            mistake = {}
            mistake["问题"] = item.get("prompt")
            mistake["答案"] = item.get("solutionTranslation")
            timestamp = item.get("timestamp")/1000
            date = pendulum.from_timestamp(timestamp, tz="Asia/Shanghai")
            mistake["时间"] = item.get("timestamp")/1000
            mistake["课程"] = item.get("courseId")
            generatorId  = item.get("challengeIdentifier").get("generatorId")
            mistake["ID"] = generatorId
            properties = utils.get_properties(mistake, mistake_properties_type_dict)
            notion_helper.get_date_relation(properties, date,True)
            parent = {
                "database_id": notion_helper.mistake_database_id,
                "type": "database_id",
            }
            if not check_exist(generatorId):
                notion_helper.create_page(parent=parent, properties=properties, icon={"type": "emoji", "emoji": "📓"})
    else:
        print(f"get mistakes error {r.text}")


def get_user_data():
    """获取用户数据"""
    r = requests.get(f"https://android-api.duolingo.cn/2023-05-23/users/{duolingo_id}",headers=headers)
    if r.ok:
        data = r.json()
        streak_length = data.get("streakData").get("length")
        id = notion_helper.get_relation_id("全部",notion_helper.all_database_id,TARGET_ICON_URL)
        if id:
            properties = {}
            properties["Streak"] = {"number": streak_length}
            notion_helper.update_page(page_id=id, properties=properties)
        courses = data.get("courses")
        for course in courses:
            get_mistakes(course.get("id"))
    else:
        print(f"get_user_data failed")

def get_duolingo_data():
    """获取多邻国每日学习数据"""
    start, id = get_lastest()
    end = pendulum.now("Asia/Shanghai").to_date_string()
    r = requests.get(
        f"https://android-api.duolingo.com/2017-06-30/users/{duolingo_id}/xp_summaries?endDate={end}&startDate={start}&timezone=Asia/Shanghai",
        headers=headers,
    )
    if r.ok:
        xp = {}
        summaries = r.json()["summaries"]
        summaries.sort(key=lambda x: x["date"])
        for item in summaries:
            date = pendulum.from_timestamp(item.get("date"), tz="Asia/Shanghai")
            title = date.to_date_string()
            xp["标题"] = date.to_date_string()
            xp["经验"] = item.get("gainedXp")
            xp["学习时长"] = item.get("totalSessionTime")
            xp["单元"] = item.get("numSessions")
            xp["日期"] = item.get("date")
            is_update = title == start and id
            add_to_notion(xp, date, is_update, id)
    else:
        print(f"{r.text}")


def add_to_notion(xp, date, is_update, page_id):
    properties = utils.get_properties(xp, xp_properties_type_dict)
    notion_helper.get_date_relation(properties, date)
    parent = {
        "database_id": notion_helper.day_database_id,
        "type": "database_id",
    }
    if is_update:
        notion_helper.update_page(page_id=page_id, properties=properties)
    else:
        notion_helper.create_page(parent=parent, properties=properties, icon=utils.get_icon(f"https://notion-icon.malinkang.com/?typ=day&date={date.to_date_string()}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    notion_helper = NotionHelper()
    headers["Authorization"] = f"Bearer {os.getenv('JWT').strip()}"
    response = requests.get(
        f"https://www.duolingo.com/users/{os.getenv('USER_NAME').strip()}",
        headers=headers,
    )
    duolingo_id = response.json()["id"]
    get_duolingo_data()
    get_user_data()