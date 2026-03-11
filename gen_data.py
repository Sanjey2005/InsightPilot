import csv
import random
from datetime import datetime, timedelta

def generate_csv(filename, num_rows=500):
    categories = ["Electronics", "Clothing", "Software", "Food"]
    products = {
        "Electronics": ["Wireless Headphones", "Bluetooth Speaker", "Laptop Stand", "Monitor 27inch", "Wireless Mouse", "Mechanical Keyboard", "Phone Case"],
        "Clothing": ["Running Shoes", "Winter Jacket", "Yoga Pants", "Casual T-Shirt", "Denim Jeans"],
        "Software": ["Project Management Tool", "Accounting Software", "CRM Platform", "Analytics Dashboard"],
        "Food": ["Protein Bars Pack", "Office Snack Box", "Coffee Subscription"]
    }
    segments = ["Enterprise", "SMB", "Consumer"]
    regions = ["North", "South", "East", "West"]
    methods = ["Credit Card", "PayPal", "Bank Transfer"]
    statuses = ["completed", "completed", "completed", "completed", "refunded"]

    base_date = datetime(2023, 1, 1)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "order_date", "customer_id", "customer_segment", "product_category", "product_name", "quantity", "unit_price", "total_revenue", "region", "payment_method", "status"])
        
        for i in range(1, num_rows + 1):
            # simulate a trend: more sales in later months
            days_offset = random.randint(0, 365)
            # Create an anomaly around mid-July (day 200)
            if 195 <= days_offset <= 205:
                # Spike in sales volume
                qty = random.randint(10, 50)
                cat = "Electronics"
            else:
                qty = random.randint(1, 10)
                cat = random.choice(categories)
                
            order_date = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            customer_id = f"C{(i % 200) + 1:03d}"
            segment = random.choice(segments)
            prod = random.choice(products[cat])
            
            # semi-realistic prices
            if cat == "Software": price = random.choice([299.99, 499.99, 599.99, 999.99])
            elif cat == "Electronics": price = random.choice([29.99, 49.99, 149.99, 349.99])
            elif cat == "Clothing": price = random.choice([19.99, 49.99, 79.99, 199.99])
            else: price = random.choice([14.99, 24.99, 39.99, 49.99])
            
            total = qty * price
            region = random.choice(regions)
            method = random.choice(methods)
            status = random.choice(statuses)
            
            writer.writerow([1000 + i, order_date, customer_id, segment, cat, prod, qty, price, total, region, method, status])

if __name__ == "__main__":
    generate_csv('c:/Users/acer/Desktop/InsightPilot/sample_ecommerce.csv', 800)
    print("Generated 800-row sample_ecommerce.csv!")

