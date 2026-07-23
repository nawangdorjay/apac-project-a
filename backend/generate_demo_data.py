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

# Smarter Communities: Healthcare Access & Wellness
HEALTHCARE_WELLNESS_DATA = {
    "quarter": ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"] * 7,
    "neighborhood": [
        "North District", "South District", "West End", "East Side", "Downtown", "Central Valley", "Blue Ridge"
    ] * 4,
    "population": [
        38500, 42100, 18600, 63700, 52000, 31000, 24500,
        39200, 41800, 19200, 62900, 51400, 30500, 24900,
        38100, 42500, 18100, 64200, 52600, 31200, 24100,
        39500, 41200, 18900, 63100, 51800, 30900, 24700
    ],
    "clinics_within_5km": [4, 6, 2, 8, 5, 3, 1, 4, 7, 2, 9, 5, 3, 1, 4, 6, 1, 8, 6, 3, 2, 5, 7, 2, 8, 5, 3, 1],
    "avg_wait_minutes": [
        45, 38, 72, 19, 52, 60, 82,
        48, 35, 70, 21, 50, 58, 80,
        42, 40, 75, 20, 54, 62, 81,
        44, 37, 71, 18, 51, 59, 79
    ],
    "preventive_visit_pct": [
        52, 60, 32, 70, 48, 40, 30,
        50, 62, 34, 68, 49, 41, 31,
        55, 58, 30, 72, 46, 38, 32,
        51, 61, 33, 69, 47, 39, 33
    ],
    "emergency_visits": [
        720, 580, 1150, 350, 890, 980, 1240,
        710, 590, 1120, 360, 880, 970, 1210,
        730, 570, 1180, 340, 910, 990, 1230,
        715, 585, 1140, 355, 885, 975, 1220
    ],
    "telehealth_pct": [
        18, 24, 10, 36, 22, 15, 8,
        19, 23, 11, 35, 21, 16, 9,
        17, 25, 9, 36, 23, 14, 8,
        20, 22, 12, 34, 20, 17, 9
    ],
    "chronic_disease_pct": [
        28, 22, 38, 19, 32, 35, 42,
        29, 21, 39, 20, 31, 36, 41,
        27, 23, 37, 19, 33, 34, 42,
        28, 22, 38, 18, 32, 35, 40
    ],
    "senior_pop_pct": [
        18, 15, 24, 12, 20, 22, 26,
        19, 14, 25, 13, 19, 21, 25,
        17, 16, 23, 12, 21, 23, 26,
        18, 15, 24, 12, 20, 22, 25
    ],
    "insurance_coverage_pct": [
        85, 90, 70, 97, 82, 75, 68,
        84, 91, 71, 96, 83, 74, 69,
        86, 89, 69, 97, 81, 76, 68,
        85, 90, 70, 95, 82, 75, 67
    ]
}

# Student Performance: Grades & Habits
STUDENT_PERFORMANCE_DATA = {
    "student_id": [f"STU{i:03d}" for i in range(1, 31)],
    "attendance_pct": [
        95, 98, 88, 75, 92, 100, 84, 96, 91, 78,
        99, 85, 93, 90, 97, 82, 94, 89, 76, 95,
        100, 87, 91, 93, 98, 80, 96, 92, 85, 99
    ],
    "study_hours": [
        12, 18, 8, 4, 10, 22, 6, 15, 9, 3,
        20, 5, 14, 11, 16, 7, 13, 10, 2, 17,
        24, 6, 12, 11, 19, 4, 15, 10, 8, 21
    ],
    "sleep_hours": [
        7, 8, 6, 5, 7, 8, 5, 7, 7, 4,
        8, 6, 7, 7, 8, 6, 7, 7, 5, 8,
        9, 6, 7, 7, 8, 5, 7, 7, 6, 8
    ],
    "final_score": [
        82, 94, 68, 55, 76, 98, 60, 88, 74, 50,
        95, 62, 80, 78, 90, 65, 81, 77, 52, 91,
        100, 64, 79, 82, 93, 58, 89, 79, 69, 96
    ],
    "gpa": [
        3.2, 3.8, 2.7, 2.1, 2.9, 4.0, 2.3, 3.5, 2.8, 2.0,
        3.9, 2.4, 3.1, 3.0, 3.6, 2.5, 3.2, 2.9, 2.0, 3.7,
        4.0, 2.5, 3.0, 3.3, 3.8, 2.2, 3.6, 3.1, 2.7, 3.9
    ],
    "screentime_hours": [
        3, 2, 5, 7, 4, 1, 6, 3, 4, 8,
        2, 6, 3, 4, 2, 5, 3, 4, 8, 2,
        1, 6, 4, 3, 2, 7, 3, 4, 5, 2
    ],
    "absences": [
        2, 1, 4, 9, 3, 0, 7, 1, 3, 10,
        0, 6, 2, 3, 1, 7, 2, 3, 9, 1,
        0, 5, 3, 2, 1, 8, 2, 3, 5, 1
    ]
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

    df_healthcare = pd.DataFrame(HEALTHCARE_WELLNESS_DATA)
    df_healthcare.to_csv("demo_data/healthcare_wellness.csv", index=False)

    df_student = pd.DataFrame(STUDENT_PERFORMANCE_DATA)
    df_student.to_csv("demo_data/student_performance.csv", index=False)
    
    print("Demo datasets generated successfully.")

if __name__ == "__main__":
    generate_demo_datasets()
