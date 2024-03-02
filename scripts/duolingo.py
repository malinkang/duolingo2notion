#!/usr/bin/python
# -*- coding: UTF-8 -*-
import argparse
import datetime
import json
import os
import time
from datetime import datetime
import pendulum
from notion_helper import NotionHelper
import requests
import utils
from config import workout_properties_type_dict
headers = {
    "Accept": "*/*",
    "User-Agent": "request",
}


def get_lastest():
    sorts=[
        {
            "property": "日期",
            "direction": "descending"
        }
    ]
    response = notion_helper.query(database_id=notion_helper.day_database_id, sorts=sorts,page_size=1)
    results = response.get("results")
    if len(results)>0:
        return (utils.get_property_value(response.get("results")[0].get("properties").get("标题")),response.get("results")[0].get("id"))
    else:
        return ("2011-01-01",None)


def get_run_data():
    start,id = get_lastest()
    end = pendulum.now("Asia/Shanghai").to_date_string()
    headers["Authorization"] = f"Bearer {os.getenv("JWT")}"
    r = requests.get(f"https://ios-api-2.duolingo.com/2017-06-30/users/29975083/xp_summaries?endDate={end}&startDate={start}&timezone=Asia/Shanghai",headers=headers)
    if r.ok:
        workout = {}
        summaries = r.json()["summaries"]
        summaries.sort(key=lambda x: x['date'])
        print(summaries)
        for item in summaries:
            date = pendulum.from_timestamp(item.get("date"), tz="Asia/Shanghai")
            title = date.to_date_string()
            print(title)
            workout["标题"] = date.to_date_string()
            workout["经验"] =  item.get("gainedXp")
            workout["学习时长"] = item.get("totalSessionTime")
            workout["单元"] =item.get("numSessions")
            workout["日期"] = item.get("date")
            is_update = title == start and id
            add_to_notion(workout,date,is_update,id)

def add_to_notion(workout,date,is_update,page_id):
    properties = utils.get_properties(workout, workout_properties_type_dict)
    notion_helper.get_date_relation(properties,date)
    parent = {
            "database_id": notion_helper.day_database_id,
            "type": "database_id",
        }
    icon = {"type": "emoji", "emoji": "🏝️"}
    if is_update:
        notion_helper.update_page(page_id=page_id, properties=properties)
    else:
        notion_helper.create_page(parent=parent, properties=properties, icon=icon)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    notion_helper=NotionHelper()
    get_run_data()