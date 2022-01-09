# encoding: utf-8
from parse import *
import logging


def extract_dividend_detail(s: str):
    sendCount = 0
    turnCount = 0
    cash = 0
    if "送" in s:
        profile = search("送{send:f}", s)
        sendCount = profile["send"]
    if "转" in s:
        profile = search("转{turn:f}", s)
        turnCount = profile["turn"]
    if "派" in s:
        profile = search("派{dividend:f}", s)
        cash = profile["dividend"]
    logging.warning(f"送股:{sendCount}\t转股:{turnCount}\t派息:{cash}")
    return {'sendCount': sendCount, 'turnCount': turnCount, 'cash': cash}










