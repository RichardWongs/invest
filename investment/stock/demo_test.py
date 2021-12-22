from datetime import date, datetime, timedelta

a = datetime.strptime("2021-10-01", "%Y-%m-%d").date()
print(type(a))


