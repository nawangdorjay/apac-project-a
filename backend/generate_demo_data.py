import pandas as pd
import numpy as np
import os

# Business sales demo dataset
BUSINESS_SALES_DATA = {
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Revenue": [42000, 38500, 51000, 47200, 53800, 61000, 58400, 62100, 55300, 67800, 72000, 81500],
    "Expenses": [31000, 29500, 33000, 34200, 36800, 38500, 37400, 39100, 36300, 41800, 44000, 47500],
    "Profit": [11000, 9000, 18000, 13000, 17000, 22500, 21000, 23000, 19000, 26000, 28000, 34000],
    "Units_Sold": [420, 385, 510, 472, 538, 610, 584, 621, 553, 678, 720, 815],
    "Customers": [180, 165, 210, 195, 225, 260, 248, 270, 238, 290, 308, 342],
    "Returns": [12, 15, 8, 10, 9, 7, 11, 6, 9, 8, 7, 5],
    "Marketing_Spend": [4200, 3850, 5100, 4720, 5380, 6100, 5840, 6210, 5530, 6780, 7200, 8150],
    "Customer_Satisfaction": [4.2, 4.0, 4.5, 4.3, 4.4, 4.6, 4.5, 4.7, 4.4, 4.8, 4.8, 4.9],
    "Region": ["North", "North", "South", "South", "East", "East", "West", "West", "North", "South", "East", "West"]
}

# Personal finance demo dataset
PERSONAL_FINANCE_DATA = {
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Income": [5800, 5800, 6200, 5800, 5800, 6500, 5800, 5800, 6200, 5800, 5800, 7000],
    "Housing": [1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500],
    "Food_Groceries": [420, 390, 450, 410, 480, 500, 460, 490, 410, 430, 520, 680],
    "Dining_Out": [280, 310, 190, 350, 420, 380, 290, 410, 260, 300, 480, 620],
    "Transport": [180, 175, 190, 185, 170, 160, 165, 175, 180, 190, 185, 195],
    "Entertainment": [120, 95, 150, 200, 180, 220, 190, 175, 140, 160, 250, 380],
    "Savings": [800, 750, 900, 600, 500, 850, 780, 620, 820, 700, 350, 200],
    "Utilities": [180, 210, 160, 140, 120, 100, 95, 100, 130, 150, 175, 210],
    "Healthcare": [50, 120, 50, 50, 80, 50, 50, 200, 50, 50, 50, 50],
    "Subscriptions": [85, 85, 85, 85, 85, 110, 110, 110, 110, 110, 135, 135]
}

# Smart Communities: Urban Mobility & Environmental log
URBAN_ENVIRONMENT_DATA = {
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Air_Quality_Index": [55, 62, 78, 92, 115, 124, 130, 118, 95, 72, 58, 52], # high in summer
    "Traffic_Delay_Pct": [22.4, 24.1, 28.5, 32.2, 35.8, 38.0, 36.5, 34.2, 31.0, 27.5, 23.8, 21.0],
    "Public_Transit_Ridership": [142000, 138000, 149000, 152000, 161000, 165000, 158000, 154000, 162000, 159000, 148000, 140000],
    "Municipal_Energy_MWh": [8500, 8200, 7800, 7400, 8900, 9800, 10500, 10200, 8800, 7600, 8000, 8400], # high summer cooling
    "Citizen_Service_Requests": [1240, 1180, 1350, 1420, 1580, 1720, 1690, 1610, 1480, 1300, 1220, 1150],
    "Waste_Recycled_Tons": [310, 305, 325, 340, 355, 370, 365, 360, 348, 330, 320, 315],
    "Green_Space_Visitors": [12000, 14500, 22000, 28000, 34000, 39000, 42000, 40000, 31000, 24000, 16000, 11000],
    "Water_Consumption_M_Liters": [45.2, 44.8, 48.5, 52.0, 58.5, 64.0, 66.5, 63.2, 54.0, 48.2, 46.0, 45.0],
    "Streetlight_Outages": [42, 38, 45, 32, 28, 24, 26, 31, 35, 40, 48, 52]
}

def generate_demo_datasets():
    """Generate and save demo CSV files."""
    os.makedirs("demo_data", exist_ok=True)
    
    df_business = pd.DataFrame(BUSINESS_SALES_DATA)
    df_business.to_csv("demo_data/business_sales.csv", index=False)
    
    df_personal = pd.DataFrame(PERSONAL_FINANCE_DATA)
    df_personal.to_csv("demo_data/personal_finance.csv", index=False)

    df_urban = pd.DataFrame(URBAN_ENVIRONMENT_DATA)
    df_urban.to_csv("demo_data/urban_environmental.csv", index=False)
    
    print("Demo datasets generated successfully.")

if __name__ == "__main__":
    generate_demo_datasets()
