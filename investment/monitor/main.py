# encoding: utf-8
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from monitor.sell_monitor import sell_signal, buy_signal
logging.basicConfig(level=logging.INFO)


if __name__ == '__main__':
    sched = BlockingScheduler()
    # sched.add_job(sell_signal, 'cron', day_of_week="0-4", hour="09-15", minute="00,50")
    sched.add_job(sell_signal, 'interval', seconds=60)
    sched.add_job(buy_signal, 'interval', seconds=600)
    sched.start()

