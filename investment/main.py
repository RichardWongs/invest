# encoding: utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
from monitor.abnormal_volume_monitoring import holding_volume_monitor, run_monitor
from security.动量选股 import market_open


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(run_monitor, 'cron', day_of_week="0-4", hour="14", minute="40")
    sched.add_job(market_open, 'cron', day_of_week="0-4", hour="14", minute="45")
    sched.add_job(holding_volume_monitor, 'cron', day_of_week="0-4", hour="14", minute="50")
    sched.start()
