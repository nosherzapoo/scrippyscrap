import pandas as pd
import glob

# Define topic keywords and phrases for each category
topic_categories = {
    'Turnover': ['quit', 'fired', 'leaving', 'left', 'resign', 'hiring', 'hire', 'quitting', 'termination', 'terminated', 'laid off', 'layoff', 'new hire', 'turnover', 'walked out', 'walked off', 'no show', 'no call', 'notice', 'two weeks', '2 weeks', 'replacement', 'position open', 'vacancy', 'job opening'],
    'Staffing': ['short staff', 'understaffed', 'coverage', 'schedule', 'call in', 'called in', 'shift', 'hours', 'overtime', 'staff shortage', 'skeleton crew', 'bare bones', 'no coverage', 'call out', 'called out', 'sick call', 'time off', 'pto', 'vacation', 'leave', 'break', 'lunch', 'availability', 'full time', 'part time', 'ft', 'pt', 'overnight', 'morning shift', 'evening shift', 'night shift', 'closing shift', 'opening shift', 'short handed', 'working alone', 'by myself', 'no help', 'need people', 'staffing issue'],
    'Inventory': ['truck', 'stock', 'inventory', 'rolltainer', 'fresh', 'seasonal', 'merchandise', 'cooler', 'freezer', 'delivery', 'shipment', 'vendor', 'overstock', 'backstock', 'topstock', 'endcap', 'planogram', 'pog', 'reset', 'mod', 'damages', 'expired', 'out of date', 'out of stock', 'oos', 'warehouse', 'dc', 'distribution', 'receiving', 'load', 'unload', 'skid', 'pallet', 'tote', 'box', 'case pack', 'shelf', 'aisle', 'section', 'department', 'perishable', 'dairy', 'frozen', 'dry goods', 'hba', 'grocery'],
    'Discount': ['sale', 'clearance', 'discount', 'price', 'deal', 'coupon', 'penny', 'markdown', 'markdowns', 'reduced', 'promotion', 'promo', 'special', 'savings', 'rollback', 'price change', 'price cut', 'bargain', 'cheap', 'digital coupon', 'paper coupon', 'bogo', 'buy one get one', 'percentage off', 'percent off', '% off', 'dollar off', 'rewards', 'points'],
    'Theft': ['steal', 'theft', 'stolen', 'shoplifting', 'shoplifter', 'loss prevention', 'lp', 'shrink', 'security', 'camera', 'surveillance', 'stealing', 'stole', 'robbery', 'robbed', 'break in', 'broke in', 'burglar', 'suspicious', 'suspect', 'concealment', 'concealed', 'pocket', 'purse', 'backpack', 'bag', 'merchandise protection', 'spider wrap', 'alpha box', 'keeper box', 'locked case', 'police', 'cops', 'arrest', 'detained', 'apprehension'],
    'Management': ['manager', 'sm ', 'asm', 'district', 'dm ', 'supervisor', 'lead', 'management', 'key holder', 'keyholder', 'key carrier', 'store manager', 'assistant manager', 'district manager', 'regional manager', 'rm', 'corporate', 'head office', 'higher ups', 'boss', 'superior', 'leadership', 'admin', 'administrator', 'coordinator', 'team lead', 'department head', 'supervisor', 'managed', 'managing', 'oversee', 'overseeing', 'in charge'],
    'Pay': ['pay', 'wage', 'salary', 'raise', 'paycheck', 'bonus', 'compensation', 'paid', 'payment', 'earnings', 'income', 'hourly', 'rate', 'minimum wage', 'min wage', 'payroll', 'direct deposit', 'check', 'payday', 'pay period', 'pay week', 'overtime pay', 'ot pay', 'time and a half', 'holiday pay', 'premium pay', 'differential', 'shift differential', 'benefits', 'insurance', '401k', 'retirement', 'pto', 'paid time off', 'vacation pay', 'sick pay', 'bereavement', 'jury duty', 'living wage', 'fair wage']
}

def categorize_text(row):
    # Combine title and text, handling NaN values
    text = ' '.join(str(x).lower() for x in [row['title'], row['text']] if pd.notna(x))
    
    # Check for each category
    categories = []
    for category, keywords in topic_categories.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
            
    return '|'.join(categories) if categories else 'Other'

# Get all reddit CSV files
reddit_files = glob.glob('reddit_posts_*.csv')

# Process each file
for file in reddit_files:
    print(f"\nProcessing {file}...")
    
    # Read CSV
    df = pd.read_csv(file)
    
    # Add categories column
    df['categories'] = df.apply(categorize_text, axis=1)
    
    # Save updated file
    df.to_csv(file, index=False)
    
    # Print summary for this file
    print(f"\nCategory distribution for {file}:")
    category_counts = pd.Series([cat for cats in df['categories'].str.split('|') 
                               for cat in cats]).value_counts()
    print(category_counts)