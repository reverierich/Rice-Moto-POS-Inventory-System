
import sys
import os
import mysql.connector

# Add the project root to sys.path
sys.path.append(os.path.abspath("c:/Users/Garden/OneDrive/Desktop/RiceMoto_Final/ricemoto_pos"))

from database.database_manager import DataController

dc = DataController()
this_week, last_week = dc.get_sales_data()

print(f"This Week: {this_week}")
print(f"Last Week: {last_week}")
