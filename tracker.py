import streamlit as st
# import pymysql
# from pymysql.err import MySQLError
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import DictCursor
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar

# Page configuration
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for theme (default is light)
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

# Dynamic CSS based on theme
if st.session_state.theme == 'dark':
    bg_color = '#1a1a1a'
    card_bg = '#2d2d2d'
    text_color = '#ffffff'
    text_secondary = '#b0b0b0'
    border_color = '#404040'
    sidebar_bg = '#2d2d2d'
    input_bg = '#404040'
else:
    bg_color = '#f8f9fa'
    card_bg = '#ffffff'
    text_color = '#1a1a1a'
    text_secondary = '#6c757d'
    border_color = '#e9ecef'
    sidebar_bg = '#ffffff'
    input_bg = '#ffffff'

# Custom CSS with dynamic theme
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {{
        font-family: 'Inter', sans-serif;
    }}
    
    .main {{
        background: {bg_color};
    }}
    
    .stApp {{
        background: {bg_color};
    }}
    
    /* Metric cards styling */
    div[data-testid="stMetricValue"] {{
        font-size: 32px;
        font-weight: 700;
        color: {text_color};
    }}
    
    div[data-testid="stMetricLabel"] {{
        font-size: 14px;
        font-weight: 500;
        color: {text_secondary};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    /* Expense card */
    .expense-card {{
        background: {card_bg};
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin: 8px 0;
        border-left: 4px solid;
        transition: all 0.2s ease;
    }}
    
    .expense-card:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }}
    
    /* Headers */
    h1 {{
        color: {text_color} !important;
        font-weight: 700 !important;
        font-size: 36px !important;
        margin-bottom: 8px !important;
    }}
    
    h2 {{
        color: {text_color} !important;
        font-weight: 600 !important;
        font-size: 24px !important;
        margin-bottom: 16px !important;
    }}
    
    h3 {{
        color: {text_secondary} !important;
        font-weight: 600 !important;
        font-size: 18px !important;
    }}
    
    /* Buttons */
    .stButton>button {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }}
    
    .stButton>button:hover {{
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {sidebar_bg};
        border-right: 1px solid {border_color};
    }}
    
    section[data-testid="stSidebar"] h1 {{
        color: #667eea !important;
    }}
    
    section[data-testid="stSidebar"] label {{
        color: {text_color} !important;
    }}
    
    section[data-testid="stSidebar"] p {{
        color: {text_secondary} !important;
    }}
    
    /* Input fields */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>select {{
        border-radius: 8px;
        border: 2px solid {border_color};
        padding: 10px;
        font-size: 15px;
        background: {input_bg};
        color: {text_color};
    }}
    
    .stTextInput>div>div>input:focus,
    .stNumberInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {{
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }}
    
    /* Remove streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# Database connection
def create_connection():
    try:
        connection = psycopg2.connect(
            host=st.secrets["host"],
            database=st.secrets["db"],
            user=st.secrets["user"],
            password=st.secrets["password"],
            port=st.secrets["port"],
            sslmode="require" 
            # pool_mode='transaction'
        )
        return connection
    except OperationalError as e:
        st.error(f"Error connecting to PostgreSQL: {e}")
        return None

# Initialize database
def init_database():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                id integer generated by default as identity primary key,
                name varchar(100) unique not null,
                color varchar(7) default '#667eea',
                icon varchar(50) default '📦',
                created_at timestamp with time zone default now()
            )
        """)
        
        # Add icon column if it doesn't exist (migration)
        try:
            cursor.execute("""
                    ALTER TABLE categories
                    ADD COLUMN IF NOT EXISTS icon VARCHAR(50) DEFAULT '📦'
            """)
            conn.commit()
        except OperationalError as e:
            # Column already exists, ignore the error
            pass
        
        cursor.execute("""
             CREATE TABLE IF NOT EXISTS expenses (
                id integer generated by default as identity primary key,
                amount numeric(10,2) not null,
                category_id integer references categories(id) on delete set null,
                note text,
                expense_date date not null,
                created_at timestamp with time zone default now()
            )
        """)
        
        # Update existing categories with icons
        icon_mapping = {
            'Food': '🍔',
            'Transport': '🚗',
            'Shopping': '🛍️',
            'Bills': '💡',
            'Entertainment': '🎬',
            'Health': '⚕️',
            'Education': '📚',
            'Others': '📦'
        }
        
        for cat_name, cat_icon in icon_mapping.items():
            cursor.execute("""
                UPDATE categories SET icon = %s WHERE name = %s AND (icon IS NULL OR icon = '📦')
            """, (cat_icon, cat_name))
        
        # Insert default categories if not exists
        default_categories = [
            ('Food', '#FF6B6B', '🍔'),
            ('Transport', '#4ECDC4', '🚗'),
            ('Shopping', '#45B7D1', '🛍️'),
            ('Bills', '#FFA07A', '💡'),
            ('Entertainment', '#98D8C8', '🎬'),
            ('Health', '#F7DC6F', '⚕️'),
            ('Education', '#BB8FCE', '📚'),
            ('Others', '#B19CD9', '📦')
        ]
        
        for cat_name, cat_color, cat_icon in default_categories:
            cursor.execute("""
                INSERT INTO categories (name, color, icon)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (cat_name, cat_color, cat_icon))
        conn.commit()
        cursor.close()
        conn.close()

def add_category(name, color, icon):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute("INSERT INTO categories (name, color, icon) VALUES (%s, %s, %s)", (name, color, icon))
            conn.commit()
            return True
        except OperationalError as e:
            st.error(f"Error: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

def get_categories():
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("SELECT * FROM categories ORDER BY name")
        categories = cursor.fetchall()
        
        # Convert RealDictRow to plain dict
        categories = [dict(row) for row in categories]
        
        cursor.close()
        conn.close()
        return categories
    return []

def add_expense(amount, category_id, note, expense_date):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute("""
                INSERT INTO expenses (amount, category_id, note, expense_date) 
                VALUES (%s, %s, %s, %s)
            """, (amount, category_id, note, expense_date))
            conn.commit()
            return True
        except OperationalError as e:
            st.error(f"Error: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

def get_expenses(start_date=None, end_date=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """
            SELECT e.*, c.name as category_name, c.color, c.icon 
            FROM expenses e 
            LEFT JOIN categories c ON e.category_id = c.id
        """
        params = []
        
        if start_date and end_date:
            query += " WHERE e.expense_date BETWEEN %s AND %s"
            params = [start_date, end_date]
        
        query += " ORDER BY e.expense_date DESC, e.created_at DESC"
        
        cursor.execute(query, params)
        expenses = cursor.fetchall()
        
        # ADD THIS LINE:
        expenses = [dict(row) for row in expenses]
        
        cursor.close()
        conn.close()
        return expenses
    return []
def delete_expense(expense_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
        cursor.close()
        conn.close()

# Initialize database
init_database()

# Sidebar
with st.sidebar:
    st.title("💰 Expense Tracker")
    st.markdown("**Track. Analyze. Save.**")
    st.markdown("---")
    
    menu = st.radio("📍 Navigation", ["➕ Add Expense", "📊 Analytics", "🏷️ Categories"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 📅 Filter Period")
    period = st.selectbox("Period", ["Today", "This Week", "This Month", "This Year", "All Time", "Custom"], label_visibility="collapsed")
    
    today = datetime.now().date()
    
    if period == "Today":
        start_date = end_date = today
    elif period == "This Week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == "This Month":
        start_date = today.replace(day=1)
        end_date = today
    elif period == "This Year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == "Custom":
        st.markdown("**Select Date Range**")
        start_date = st.date_input("From", today - timedelta(days=30))
        end_date = st.date_input("To", today)
    else:
        start_date = end_date = None
    
    st.markdown("---")
    st.markdown(f"<small style='color: #6c757d;'>📆 {datetime.now().strftime('%B %d, %Y')}</small>", unsafe_allow_html=True)
    
    # Theme toggle button at bottom
    st.markdown("<br><br>", unsafe_allow_html=True)
    theme_icon = "🌙" if st.session_state.theme == 'light' else "☀️"
    theme_text = "Dark Mode" if st.session_state.theme == 'light' else "Light Mode"
    
    if st.button(f"{theme_icon} {theme_text}", use_container_width=True, key="theme_toggle"):
        st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
        st.rerun()

# Main content
if menu == "➕ Add Expense":
    st.title("Add New Expense")
    st.markdown("Record your spending quickly and easily")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("expense_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                amount = st.number_input("💵 Amount (₹)", min_value=0, step=10)
            
            with col_b:
                expense_date = st.date_input("📅 Date", value=datetime.now().date())
            
            categories = get_categories()
            category_options = {f"{cat['icon']} {cat['name']}": cat['id'] for cat in categories}
            
            selected_category = st.selectbox("🏷️ Category", options=list(category_options.keys()))
            
            note = st.text_area("📝 Note (Optional)", placeholder="e.g., Lunch with friends at Pizza Hut", height=100)
            
            submitted = st.form_submit_button("💾 Save Expense", use_container_width=True)
            
            if submitted:
                if amount > 0 and selected_category:
                    category_id = category_options[selected_category]
                    if add_expense(amount, category_id, note, expense_date):
                        st.success(f"✅ Expense of ₹{amount:.2f} added successfully!")
                        st.rerun()
                else:
                    st.error("⚠️ Please fill in all required fields")
    
    with col2:
        st.markdown("### 🕒 Recent Expenses")
        recent = get_expenses()[:8]
        
        if recent:
            for exp in recent:
                st.markdown(f"""
                    <div class="expense-card" style="border-left-color: {exp.get('color', '#667eea')};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 20px; font-weight: 700; color: {text_color};">₹{exp['amount']:.2f}</div>
                                <div style="font-size: 13px; color: {text_secondary}; margin-top: 4px;">
                                    {exp.get('icon', '📦')} {exp['category_name']}
                                </div>
                                <div style="font-size: 12px; color: {text_secondary}; margin-top: 2px;">
                                    {exp['expense_date']}
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent expenses")

elif menu == "📊 Analytics":
    st.title("Analytics Dashboard")
    st.markdown("Detailed insights into your spending patterns")
    
    expenses = get_expenses(start_date, end_date) if start_date and end_date else get_expenses()
    
    if expenses:
        df = pd.DataFrame(expenses)
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['expense_date'] = pd.to_datetime(df['expense_date'])
        
        # Summary metrics
        total_amount = df['amount'].sum()
        avg_amount = df['amount'].mean()
        total_transactions = len(df)
        
        # Calculate comparison with previous period
        if start_date and end_date:
            days_diff = (end_date - start_date).days + 1
            prev_start = start_date - timedelta(days=days_diff)
            prev_end = start_date - timedelta(days=1)
            prev_expenses = get_expenses(prev_start, prev_end)
            prev_total = sum([float(exp['amount']) for exp in prev_expenses]) if prev_expenses else 0
            change_pct = ((total_amount - prev_total) / prev_total * 100) if prev_total > 0 else 0
        else:
            change_pct = 0
        
        top_category = df.groupby('category_name')['amount'].sum().idxmax()
        top_category_amount = df.groupby('category_name')['amount'].sum().max()
        
        # Metric cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Total Spent", f"₹{total_amount:,.2f}", 
                     f"{change_pct:+.1f}%" if start_date and end_date else None,
                     delta_color="inverse")
        
        with col2:
            st.metric("📊 Average", f"₹{avg_amount:,.2f}")
        
        with col3:
            st.metric("🔢 Transactions", f"{total_transactions:,}")
        
        with col4:
            st.metric("🏆 Top Category", top_category, f"₹{top_category_amount:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Row 1: Spending Trend
        st.subheader("📈 Spending Trend Over Time")
        
        # Group by date and handle different period views
        daily_expenses = df.groupby(df['expense_date'].dt.date)['amount'].sum().reset_index()
        daily_expenses.columns = ['Date', 'Amount']
        daily_expenses['Date'] = pd.to_datetime(daily_expenses['Date'])
        
        # Format x-axis based on period
        if period == "Today":
            x_title = 'Time'
            daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%b %d, %Y')
        elif period == "This Week":
            x_title = 'Date'
            daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%a, %b %d')
        elif period == "This Month":
            x_title = 'Date'
            daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%b %d')
        elif period == "This Year":
            # Group by month for year view
            daily_expenses = df.groupby(df['expense_date'].dt.to_period('M'))['amount'].sum().reset_index()
            daily_expenses.columns = ['Date', 'Amount']
            daily_expenses['Date'] = daily_expenses['Date'].dt.to_timestamp()
            daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%b %Y')
            x_title = 'Month'
        else:
            # Check date range to decide format
            date_range = (daily_expenses['Date'].max() - daily_expenses['Date'].min()).days
            if date_range <= 7:
                daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%a, %b %d')
                x_title = 'Date'
            elif date_range <= 60:
                daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%b %d')
                x_title = 'Date'
            else:
                # Group by month for long ranges
                daily_expenses = df.groupby(df['expense_date'].dt.to_period('M'))['amount'].sum().reset_index()
                daily_expenses.columns = ['Date', 'Amount']
                daily_expenses['Date'] = daily_expenses['Date'].dt.to_timestamp()
                daily_expenses['Display'] = daily_expenses['Date'].dt.strftime('%b %Y')
                x_title = 'Month'
        
        # Create area chart
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=daily_expenses['Display'],
            y=daily_expenses['Amount'],
            mode='lines+markers',
            name='Daily Spending',
            line=dict(color='#667eea', width=3),
            marker=dict(size=8, color='#667eea'),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.15)',
            hovertemplate='<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>'
        ))
        
        # Add moving average only if enough data points
        if len(daily_expenses) > 3:
            daily_expenses['MA'] = daily_expenses['Amount'].rolling(window=3, min_periods=1).mean()
            fig_trend.add_trace(go.Scatter(
                x=daily_expenses['Display'],
                y=daily_expenses['MA'],
                mode='lines',
                name='3-Period Average',
                line=dict(color='#FF6B6B', width=2, dash='dash'),
                hovertemplate='<b>%{x}</b><br>Avg: ₹%{y:,.2f}<extra></extra>'
            ))
        
        fig_trend.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=True, 
                gridcolor='#e9ecef' if st.session_state.theme == 'light' else '#404040',
                title=x_title,
                color=text_color,
                tickangle=-45 if len(daily_expenses) > 10 else 0
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='#e9ecef' if st.session_state.theme == 'light' else '#404040',
                title='Amount (₹)',
                color=text_color
            ),
            hovermode='x unified',
            font=dict(family='Inter', size=12, color=text_color),
            height=400,
            margin=dict(l=20, r=20, t=20, b=80),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color=text_color)
            )
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Row 2: Category Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Spending by Category")
            
            category_data = df.groupby(['category_name', 'color', 'icon'])['amount'].sum().reset_index()
            category_data = category_data.sort_values('amount', ascending=False)
            
            # Donut chart
            fig_donut = go.Figure(data=[go.Pie(
                labels=category_data['category_name'],
                values=category_data['amount'],
                hole=0.5,
                marker=dict(colors=category_data['color']),
                textposition='inside',
                textinfo='percent',
                hovertemplate='<b>%{label}</b><br>₹%{value:,.2f}<br>%{percent}<extra></extra>'
            )])
            
            fig_donut.update_layout(
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12, color=text_color),
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(font=dict(color=text_color))
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        
        with col2:
            st.subheader("📊 Category Breakdown")
            
            # Horizontal bar chart
            fig_bar = go.Figure(go.Bar(
                y=category_data['category_name'],
                x=category_data['amount'],
                orientation='h',
                marker=dict(color=category_data['color']),
                text=category_data['amount'].apply(lambda x: f'₹{x:,.0f}'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>₹%{x:,.2f}<extra></extra>'
            ))
            
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#e9ecef' if st.session_state.theme == 'light' else '#404040', title='Amount (₹)', color=text_color),
                yaxis=dict(showgrid=False, title='', color=text_color),
                font=dict(family='Inter', size=12, color=text_color),
                height=350,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Row 3: Additional insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Day of Week Analysis")
            
            df['day_of_week'] = df['expense_date'].dt.day_name()
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_expenses = df.groupby('day_of_week')['amount'].sum().reindex(day_order, fill_value=0)
            
            fig_dow = go.Figure(go.Bar(
                x=dow_expenses.index,
                y=dow_expenses.values,
                marker=dict(
                    color=dow_expenses.values,
                    colorscale='Purples',
                    showscale=False
                ),
                text=[f'₹{val:.0f}' for val in dow_expenses.values],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>'
            ))
            
            fig_dow.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, title='', color=text_color),
                yaxis=dict(showgrid=True, gridcolor='#e9ecef' if st.session_state.theme == 'light' else '#404040', title='Amount (₹)', color=text_color),
                font=dict(family='Inter', size=12, color=text_color),
                height=300,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_dow, use_container_width=True)
        
        with col2:
            st.subheader("💳 Top 5 Expenses")
            
            top_expenses = df.nlargest(5, 'amount')[['expense_date', 'category_name', 'amount', 'note', 'color']]
            
            for idx, exp in top_expenses.iterrows():
                note_text = exp['note'][:40] if pd.notna(exp['note']) and exp['note'] else 'No note'
                st.markdown(f"""
                    <div class="expense-card" style="border-left-color: {exp['color']};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 1;">
                                <div style="font-size: 15px; font-weight: 600; color: {text_color};">{exp['category_name']}</div>
                                <div style="font-size: 13px; color: {text_secondary}; margin-top: 2px;">{note_text}</div>
                                <div style="font-size: 12px; color: {text_secondary}; margin-top: 2px;">{exp['expense_date'].strftime('%b %d, %Y')}</div>
                            </div>
                            <div style="font-size: 20px; font-weight: 700; color: {exp['color']};">₹{exp['amount']:,.0f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        
        # Expense table
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 All Transactions")
        
        display_df = df[['expense_date', 'category_name', 'amount', 'note']].copy()
        display_df.columns = ['Date', 'Category', 'Amount (₹)', 'Note']
        display_df['Date'] = display_df['Date'].dt.strftime('%b %d, %Y')
        display_df['Amount (₹)'] = display_df['Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
        display_df['Note'] = display_df['Note'].fillna('-')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            expense_to_delete = st.selectbox("Select expense to delete", 
                                            options=[(exp['id'], f"₹{exp['amount']:.2f} - {exp['category_name']} - {exp['expense_date']}") 
                                                    for exp in expenses],
                                            format_func=lambda x: x[1])
        
        with col2:
            if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                delete_expense(expense_to_delete[0])
                st.success("Deleted!")
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        st.info("📊 No expenses found for the selected period. Start adding expenses to see analytics!")

elif menu == "🏷️ Categories":
    st.title("Manage Categories")
    st.markdown("Customize your expense categories")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Add New Category")
        with st.form("category_form", clear_on_submit=True):
            cat_name = st.text_input("Category Name", placeholder="e.g., Groceries")
            
            col_a, col_b = st.columns(2)
            with col_a:
                cat_color = st.color_picker("Color", "#667eea")
            with col_b:
                cat_icon = st.text_input("Emoji", "📦", max_chars=2)
            
            if st.form_submit_button("Add Category", use_container_width=True):
                if cat_name:
                    if add_category(cat_name, cat_color, cat_icon):
                        st.success(f"✅ Category '{cat_name}' added!")
                        st.rerun()
                else:
                    st.error("Please enter a category name")
    
    with col2:
        st.subheader("📚 Existing Categories")
        categories = get_categories()
        
        # Grid layout for categories
        cols = st.columns(3)
        for idx, cat in enumerate(categories):
            with cols[idx % 3]:
                st.markdown(f"""
                    <div style="background: {card_bg}; padding: 20px; border-radius: 12px; 
                                box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid {border_color};
                                text-align: center; border-top: 4px solid {cat['color']}; margin-bottom: 16px;">
                        <div style="font-size: 32px; margin-bottom: 8px;">{cat.get('icon', '📦')}</div>
                        <div style="font-size: 16px; font-weight: 600; color: {text_color}; margin-bottom: 4px;">{cat['name']}</div>
                        <div style="width: 40px; height: 4px; background: {cat['color']}; margin: 8px auto; border-radius: 2px;"></div>
                    </div>
                """, unsafe_allow_html=True)