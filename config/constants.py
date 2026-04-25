TRANSACTION_TYPES = ['Income', 'Expense', 'To Receive', 'To Pay']

CATEGORIES = {
    'Expense': {
        'Food': [
            'Groceries', 'Dining Out', 'Snacks', 'Coffee', 'Swiggy',
            'Zomato', 'Fast Food', 'Fruits & Vegetables', 'Beverages',
            'Milk & Dairy', 'Bakery', 'Tiffin Service'
        ],
        'Transportation': [
            'Fuel', 'Petrol', 'Diesel', 'CNG', 'Public Transit',
            'Uber', 'Ola', 'Rapido', 'Auto Rickshaw', 'Taxi',
            'Train', 'Bus', 'Flight', 'Parking', 'Toll',
            'Bike Service', 'Car Service', 'Vehicle Maintenance',
            'Tyre Change', 'Vehicle Insurance', 'Vehicle EMI'
        ],
        'Housing': [
            'Rent', 'Society Charges', 'Maintenance Fee',
            'Home Repair', 'Plumber', 'Electrician', 'Carpenter',
            'Painter', 'Cleaning Service', 'Pest Control',
            'Furniture', 'Home Appliances', 'Interior Work'
        ],
        'Recharge & Bills': [
            'Mobile Recharge', 'Prepaid Recharge', 'Postpaid Bill',
            'DTH Recharge', 'Broadband Bill', 'Internet Bill',
            'Electricity Bill', 'Water Bill', 'Gas Bill', 'Piped Gas',
            'LPG Cylinder', 'OTT Recharge', 'Landline Bill',
            'Municipal Tax', 'Property Tax'
        ],
        'Entertainment': [
            'Movies', 'Games', 'Events', 'Netflix', 'Amazon Prime',
            'Disney Hotstar', 'Spotify', 'YouTube Premium', 'JioCinema',
            'SonyLiv', 'Concerts', 'Sports', 'Hobbies',
            'OTT Subscription', 'Books', 'Theme Park'
        ],
        'Shopping': [
            'Clothes', 'Electronics', 'Home Items', 'Amazon', 'Flipkart',
            'Meesho', 'Myntra', 'Accessories', 'Footwear', 'Cosmetics',
            'Personal Care', 'Stationery', 'Gifts Purchased',
            'Online Shopping', 'Offline Shopping'
        ],
        'Healthcare': [
            'Doctor Consultation', 'Hospital', 'Lab Tests', 'Medicines',
            'Pharmacy', 'Dental', 'Eye Care', 'Mental Health',
            'Gym', 'Fitness', 'Yoga', 'Health Insurance Premium',
            'Ambulance', 'Medical Equipment'
        ],
        'Education': [
            'Tuition', 'Course Fees', 'Books', 'Coaching', 'Online Course',
            'Udemy', 'Coursera', 'Exam Fees', 'Stationery',
            'College Fees', 'School Fees', 'Hostel Fees',
            'Library Fees', 'Certification'
        ],
        'Investment': [
            'Stocks', 'Mutual Funds', 'SIP', 'Fixed Deposit', 'PPF',
            'NPS', 'Crypto', 'Gold', 'Digital Gold', 'Real Estate',
            'Recurring Deposit', 'ELSS'
        ],
        'Gift & Donations': [
            'Birthday Gift', 'Wedding Gift', 'Anniversary Gift',
            'Festival Gift', 'Diwali', 'Christmas', 'Eid',
            'Donation', 'Charity', 'Temple', 'Religious Expense'
        ],
        'Travel': [
            'Hotel', 'Flight', 'Train Ticket', 'Bus Ticket', 'Cab',
            'Food During Travel', 'Sightseeing', 'Visa Fees',
            'Travel Insurance', 'Passport Fees', 'Luggage'
        ],
        'EMI & Loans': [
            'Home Loan EMI', 'Car Loan EMI', 'Personal Loan EMI',
            'Credit Card EMI', 'Education Loan EMI', 'Two Wheeler EMI',
            'Consumer Loan EMI', 'Gold Loan EMI', 'Other EMI'
        ],
        'Maintenance & Repair': [
            'Mobile Repair', 'Laptop Repair', 'TV Repair',
            'AC Service', 'AC Repair', 'Washing Machine Repair',
            'Refrigerator Repair', 'Inverter Service', 'Generator Service',
            'Plumbing', 'Electrical Work', 'General Maintenance',
            'Annual Maintenance Contract', 'Appliance Service'
        ],
        'Personal Care': [
            'Haircut', 'Salon', 'Spa', 'Parlour', 'Grooming',
            'Skincare', 'Perfume', 'Cosmetics', 'Laundry', 'Dry Cleaning'
        ],
        'Other': [
            'Miscellaneous', 'Unspecified', 'Cash Withdrawal',
            'Bank Charges', 'ATM Charges', 'Late Fee',
            'Penalty', 'Fine', 'Legal Fees', 'Government Fees'
        ]
    },
    'Income': {
        'Salary': [
            'Regular', 'Bonus', 'Overtime', 'Increment',
            'Arrears', 'Performance Pay', 'Allowances', 'Gratuity'
        ],
        'Freelance': [
            'Project Payment', 'Consulting', 'Design', 'Development',
            'Writing', 'Teaching', 'Coaching', 'Photography',
            'Video Editing', 'Social Media', 'Content Creation'
        ],
        'Investment Returns': [
            'Dividends', 'Interest', 'Capital Gains', 'Mutual Fund Returns',
            'Stock Returns', 'FD Interest', 'RD Maturity',
            'PPF Returns', 'NPS Returns', 'Rental Income'
        ],
        'Business': [
            'Sales Revenue', 'Service Income', 'Commission',
            'Partnership Income', 'Shop Income', 'Online Business'
        ],
        'Other': [
            'Gifts Received', 'Refunds', 'Cashback', 'Lottery',
            'Insurance Claim', 'Tax Refund', 'Scholarship',
            'Stipend', 'Pocket Money', 'Miscellaneous'
        ]
    },
    'To Receive': {
        'Pending Income': [
            'Salary', 'Freelance Payment', 'Investment Returns',
            'Loan Given', 'Security Deposit Return', 'Refund Expected',
            'Cashback Expected', 'Commission Due', 'Other'
        ]
    },
    'To Pay': {
        'Bills': [
            'Electricity Bill', 'Water Bill', 'Gas Bill',
            'Internet Bill', 'Mobile Bill', 'DTH Bill',
            'Broadband Bill', 'Rent', 'Society Maintenance',
            'Municipal Tax', 'Other'
        ],
        'Debt': [
            'Credit Card', 'Personal Loan', 'Home Loan',
            'Car Loan', 'Education Loan', 'Two Wheeler Loan',
            'Friend Loan', 'Family Loan', 'Gold Loan', 'Other'
        ],
        'Subscriptions': [
            'Netflix', 'Amazon Prime', 'Disney Hotstar', 'Spotify',
            'Gym Membership', 'Magazine', 'Software Subscription',
            'Cloud Storage', 'Domain Renewal', 'Hosting', 'Other'
        ],
        'Maintenance': [
            'Vehicle Service Due', 'AC Service Due', 'Appliance Service Due',
            'Home Maintenance Due', 'Annual Maintenance Contract', 'Other'
        ],
        'Other': [
            'Miscellaneous', 'Advance Payment',
            'Security Deposit', 'Event Booking', 'Other'
        ]
    }
}
