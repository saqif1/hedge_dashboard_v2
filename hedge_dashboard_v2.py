# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from scipy.stats import norm

# ============================
# 🎨 Page Configuration
# ============================
st.set_page_config(
    page_title="LME Copper Hedging Dashboard",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================
# 🎨 Custom CSS Styling
# ============================
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; margin-bottom: 1rem;}
    .section-header {font-size: 1.8rem; color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 0.3rem; margin-top: 1.5rem;}
    .highlight-box {background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;}
    .metric-value {font-size: 1.5rem; font-weight: bold;}
    .warning {color: #ff4b4b; font-weight: bold;}
    .positive {color: #00cc96; font-weight: bold;}
    .export-section {background-color: #e6f7ff; padding: 15px; border-radius: 5px; margin: 10px 0;}
    .sidebar .sidebar-content {background-color: #f8f9fa;}
    .limit-warning {background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 10px; margin: 10px 0; border-radius: 4px;}
    .limit-error {background-color: #f8d7da; border-left: 5px solid #dc3545; padding: 10px; margin: 10px 0; border-radius: 4px;}
    .limit-success {background-color: #d4edda; border-left: 5px solid #28a745; padding: 10px; margin: 10px 0; border-radius: 4px;}
    .data-input-section {background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px;}
    /* Tooltip like hover text */
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted black;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

# ============================
# 🚀 Constants
# ============================
EPSILON = 1e-10

# ============================
# 🚀 Initialize Session State
# ============================
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}

# --- Trader's Hard Funding Limit (in USD) ---
if 'funding_limit_usd' not in st.session_state:
    st.session_state.funding_limit_usd = 29_200_000.0  # Trader specified: $29.2 million USD

# --- LME Constants ---
if 'lme_margin_per_lot_usd' not in st.session_state:
    st.session_state.lme_margin_per_lot_usd = 20_000.0  # Initial Margin Requirement (USD per lot)
if 'lme_tons_per_lot' not in st.session_state:
    st.session_state.lme_tons_per_lot = 25.0  # 1 lot = 25 tons

# --- Initialize or Load Position Data ---
default_position_data = pd.DataFrame([
    {"Account": "CIFCO (Mid)", "Tons": 3000.0, "Holding Price (USD/ton)": 10006.59, "Balance Funds (USD)": 4_840_000.0, "Open Position Limit (USD)": 0.0, "Variable Margin (USD)": 0.0, "Initial Margin (USD)": 2_500_000.0, "Unrealized PnL (USD)": -170_000.0},
    {"Account": "SUCDEN", "Tons": 0.0, "Holding Price (USD/ton)": 0.0, "Balance Funds (USD)": 200_000.0, "Open Position Limit (USD)": 0.0, "Variable Margin (USD)": 0.0, "Initial Margin (USD)": 0.0, "Unrealized PnL (USD)": 0.0},
    {"Account": "MAREX", "Tons": 6500.0, "Holding Price (USD/ton)": 9829.41, "Balance Funds (USD)": 6_770_000.0, "Open Position Limit (USD)": 3_000_000.0, "Variable Margin (USD)": 50_000.0, "Initial Margin (USD)": 4_070_000.0, "Unrealized PnL (USD)": -1_330_000.0},
])
# Add a row for Total which will be calculated
default_position_data.loc[len(default_position_data)] = {
    "Account": "Total",
    "Tons": 9500.0,
    "Holding Price (USD/ton)": 9885.36,
    "Balance Funds (USD)": 11_810_000.0,
    "Open Position Limit (USD)": 3_000_000.0,
    "Variable Margin (USD)": 50_000.0,
    "Initial Margin (USD)": 6_570_000.0,
    "Unrealized PnL (USD)": -1_500_000.0
}

if 'position_data_editor' not in st.session_state:
    st.session_state.position_data_editor = default_position_data.copy()

# --- Initialize Forward Curve Data ---
default_forward_curve_data = pd.DataFrame([
    {"Tenor": "Spot", "Price (USD/ton)": 9400.0},
    {"Tenor": "1M", "Price (USD/ton)": 9410.0},
    {"Tenor": "2M", "Price (USD/ton)": 9420.0},
    {"Tenor": "3M", "Price (USD/ton)": 9430.0},
    {"Tenor": "Dec25", "Price (USD/ton)": 9450.0},
    {"Tenor": "Mar26", "Price (USD/ton)": 9500.0},
    {"Tenor": "Jun26", "Price (USD/ton)": 9550.0},
])
if 'forward_curve_data_editor' not in st.session_state:
    st.session_state.forward_curve_data_editor = default_forward_curve_data.copy()

# --- Initialize LME Spread Data ---
default_spread_data = pd.DataFrame([
    {"Spread Label": "Cash-3M", "Bid": -70.0, "Ask": -73.49},
    {"Spread Label": "Oct25-3M", "Bid": -42.83, "Ask": -43.00},
    {"Spread Label": "Nov25-3M", "Bid": -16.26, "Ask": -17.00},
    {"Spread Label": "Dec25-3M", "Bid": 3.00, "Ask": 2.70},
    {"Spread Label": "3M-Mar26", "Bid": -18.00, "Ask": -19.42},
    {"Spread Label": "3M-Jun26", "Bid": -40.25, "Ask": -48.25},
])
if 'spread_data_editor' not in st.session_state:
    st.session_state.spread_data_editor = default_spread_data.copy()

# ============================
# 🧮 Black Model for Futures Options (LME Compliant)
# ============================
def black_price(S, K, T, r, sigma, option_type="Put"):
    """Calculate option price and delta using Black Model for futures options."""
    # Use EPSILON to check for values that are effectively zero or negative
    if T <= EPSILON or sigma <= EPSILON:
        return 0.0, 0.0
    try:
        d1 = (np.log(S / K) + (0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
    except ZeroDivisionError: # Extra safety net
        return 0.0, 0.0

    if option_type == "Call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:  # Put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)  # = norm.cdf(d1) - 1

    return price, delta

# ============================
# 📄 PDF Report Generation
# ============================
def create_pdf_report(report_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
    )
    elements.append(Paragraph("LME Copper Hedging Strategy Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Date and details
    elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Prepared for: Finance Department", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Position Summary
    elements.append(Paragraph("Position Summary", styles['Heading2']))
    position_data = [
        ['Metric', 'Value'],
        ['Position Size (Tons)', f"{report_data.get('position_size_tons', 0):,.0f}"],
        ['Average Holding Price (USD/ton)', f"${report_data.get('avg_holding_price', 0):,.2f}"],
        ['Current Funds (USD)', f"${report_data.get('current_funds_usd', 0):,.0f}"],
        ['Current Margin Requirement (USD)', f"${report_data.get('current_margin_usd', 0):,.0f}"],
        ['Current PnL (USD)', f"${report_data.get('current_pnl_usd', 0):,.0f}"],
        ['Funding Limit (USD)', f"${report_data.get('funding_limit_usd', 0):,.0f}"],
    ]
    position_table = Table(position_data, colWidths=[2.5*inch, 2*inch])
    position_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(position_table)
    elements.append(Spacer(1, 12))
    
    # Planning Scenario (if available)
    if 'planning_scenario' in st.session_state.report_data: # Fixed typo
        elements.append(Paragraph("Future Position Planning Scenario", styles['Heading2']))
        scenario_data = [
            ['Parameter', 'Value'],
            ['Target Price (USD/ton)', f"${st.session_state.report_data['planning_scenario'].get('target_price', 0):,.2f}"],
            ['Additional Tons', f"{st.session_state.report_data['planning_scenario'].get('additional_tons', 0):,.0f}"],
            ['New Total Position (Tons)', f"{st.session_state.report_data['planning_scenario'].get('new_total_tons', 0):,.0f}"],
            ['New Average Price (USD/ton)', f"${st.session_state.report_data['planning_scenario'].get('new_avg_price', 0):,.2f}"],
            ['Required Funds (USD)', f"${st.session_state.report_data['planning_scenario'].get('required_funds_usd', 0):,.0f}"],
            ['Remaining Available Funds (USD)', f"${st.session_state.report_data['planning_scenario'].get('remaining_funds_usd', 0):,.0f}"],
            ['Feasibility', st.session_state.report_data['planning_scenario'].get('feasibility', 'N/A')],
        ]
        scenario_table = Table(scenario_data, colWidths=[2.5*inch, 2*inch])
        scenario_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(scenario_table)
        elements.append(Spacer(1, 12))

    # Hedging Strategy
    elements.append(Paragraph("Hedging Strategy", styles['Heading2']))
    hedging_data = [
        ['Parameter', 'Value'],
        ['Hedging Ratio', f"{report_data.get('hedge_ratio', 0)*100:.1f}%"],
        ['Hedge Tenor', report_data.get('hedge_tenor', 'N/A')],
        ['Margin Reduction (USD)', f"${report_data.get('margin_reduction', 0):,.0f}"],
        ['Risk Reduction (USD)', f"${report_data.get('risk_reduction', 0):,.0f}"],
        ['Improved Margin Call Price (USD/ton)', f"${report_data.get('hedged_margin_call', 0):,.1f}"],
    ]
    hedging_table = Table(hedging_data, colWidths=[2.5*inch, 2*inch])
    hedging_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(hedging_table)
    elements.append(Spacer(1, 12))
    
    # Options Analysis
    elements.append(Paragraph("Options Analysis", styles['Heading2']))
    options_data = [
        ['Strategy', 'Value'],
        ['Protective Put Cost (USD)', f"${report_data.get('protection_cost', 0):,.0f}"],
        ['Risk Reversal Net Cost (USD)', f"${report_data.get('net_cost', 0):,.0f}"],
    ]
    options_table = Table(options_data, colWidths=[2.5*inch, 2*inch])
    options_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(options_table)
    elements.append(Spacer(1, 12))
    
    # Recommendations
    elements.append(Paragraph("Recommendations", styles['Heading2']))
    recommendations = [
        "1. Consider implementing a spread hedge to reduce margin requirements",
        "2. Evaluate options strategies for downside protection",
        "3. Monitor forward curve for optimal hedging opportunities",
        "4. Maintain adequate capital buffer for potential margin calls",
        "5. Regularly review and adjust hedging ratios based on market conditions"
    ]
    
    for rec in recommendations:
        elements.append(Paragraph(rec, styles['Normal']))
        elements.append(Spacer(1, 6))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================
# 📊 Excel Report Generation
# ============================
def create_excel_report(report_data):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Position Summary sheet
        position_summary = pd.DataFrame({
            'Metric': ['Position Size (Tons)', 'Average Holding Price (USD/ton)', 
                      'Current Funds (USD)', 'Current Margin Requirement (USD)', 
                      'Current PnL (USD)', 'Funding Limit (USD)'],
            'Value': [f"{report_data.get('position_size_tons', 0):,.0f}", 
                     f"${report_data.get('avg_holding_price', 0):,.2f}",
                     f"${report_data.get('current_funds_usd', 0):,.0f}",
                     f"${report_data.get('current_margin_usd', 0):,.0f}",
                     f"${report_data.get('current_pnl_usd', 0):,.0f}",
                     f"${report_data.get('funding_limit_usd', 0):,.0f}"]
        })
        position_summary.to_excel(writer, sheet_name='Position Summary', index=False)
        
        # Planning Scenario sheet (if available)
        if 'planning_scenario' in st.session_state.report_data: # Fixed typo
            scenario_data = {
                'Parameter': ['Target Price (USD/ton)', 'Additional Tons', 'New Total Position (Tons)', 
                             'New Average Price (USD/ton)', 'Required Funds (USD)', 
                             'Remaining Available Funds (USD)', 'Feasibility'],
                'Value': [f"${st.session_state.report_data['planning_scenario'].get('target_price', 0):,.2f}",
                         f"{st.session_state.report_data['planning_scenario'].get('additional_tons', 0):,.0f}",
                         f"{st.session_state.report_data['planning_scenario'].get('new_total_tons', 0):,.0f}",
                         f"${st.session_state.report_data['planning_scenario'].get('new_avg_price', 0):,.2f}",
                         f"${st.session_state.report_data['planning_scenario'].get('required_funds_usd', 0):,.0f}",
                         f"${st.session_state.report_data['planning_scenario'].get('remaining_funds_usd', 0):,.0f}",
                         st.session_state.report_data['planning_scenario'].get('feasibility', 'N/A')]
            }
            pd.DataFrame(scenario_data).to_excel(writer, sheet_name='Planning Scenario', index=False)

        # Hedging Strategy sheet
        hedging_strategy = pd.DataFrame({
            'Parameter': ['Hedging Ratio', 'Hedge Tenor', 'Margin Reduction (USD)', 
                         'Risk Reduction (USD)', 'Improved Margin Call Price (USD/ton)'],
            'Value': [f"{report_data.get('hedge_ratio', 0)*100:.1f}%",
                     report_data.get('hedge_tenor', 'N/A'),
                     f"${report_data.get('margin_reduction', 0):,.0f}",
                     f"${report_data.get('risk_reduction', 0):,.0f}",
                     f"${report_data.get('hedged_margin_call', 0):,.1f}"]
        })
        hedging_strategy.to_excel(writer, sheet_name='Hedging Strategy', index=False)
        
        # Options Analysis sheet
        options_analysis = pd.DataFrame({
            'Strategy': ['Protective Put Cost (USD)', 'Risk Reversal Net Cost (USD)'],
            'Value': [f"${report_data.get('protection_cost', 0):,.0f}",
                     f"${report_data.get('net_cost', 0):,.0f}"]
        })
        options_analysis.to_excel(writer, sheet_name='Options Analysis', index=False)
        
        # Market Data sheet (Placeholder, can be enhanced)
        market_data = pd.DataFrame({
            'Spread': ['Cash-3M', 'Oct25-3M', 'Nov25-3M', 'Dec25-3M', '3M-Jan26', '3M-Mar26', '3M-Jun26', '3M-Dec26'],
            'Bid': [-70.01, -42.83, -16.26, 3.00, -18.00, -40.25, -75.25, -139.75],
            'Ask': [-73.49, -43.00, -17.00, 2.70, -19.42, -48.25, -87.75, -166.50],
            'Last': [-70.00, -41.25, -16.50, 2.50, -18.00, -42.00, -81.25, -150.25],
            'Change': [+1.13, +2.96, +2.85, 0.00, -2.03, +2.00, -8.73, -9.73]
        })
        market_data.to_excel(writer, sheet_name='Market Data', index=False)
        
        # Recommendations sheet
        recommendations = pd.DataFrame({
            'Recommendations': [
                "Consider implementing a spread hedge to reduce margin requirements",
                "Evaluate options strategies for downside protection",
                "Monitor forward curve for optimal hedging opportunities",
                "Maintain adequate capital buffer for potential margin calls",
                "Regularly review and adjust hedging ratios based on market conditions"
            ]
        })
        recommendations.to_excel(writer, sheet_name='Recommendations', index=False)
    
    buffer.seek(0)
    return buffer

# ============================
# 🏁 Main App
# ============================
st.markdown('<p class="main-header">LME Copper Hedging Dashboard</p>', unsafe_allow_html=True)

# Sidebar for global inputs
with st.sidebar:
    st.image("logo.png", width=80)
    st.divider()
    
    st.header("💰 Funding Limit")
    # Input in millions for ease, convert to USD
    funding_limit_millions = st.number_input(
        "Funding Limit (Million USD)", 
        min_value=0.0,
        value=st.session_state.funding_limit_usd / 1_000_000.0, 
        step=1.0,
        help="Hard limit on total funds in futures account."
    )
    st.session_state.funding_limit_usd = funding_limit_millions * 1_000_000.0
    
    st.header("🛡️ Hedging Preferences")
    hedge_ratio = st.slider("Hedging Ratio", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
    hedge_tenor = st.selectbox("Hedge Tenor", ["3M", "6M", "Dec-2025", "Mar-2026", "Jun-2026"])
    
    st.header("📤 Report Options")
    report_format = st.selectbox("Report Format", ["PDF", "Excel"])

# ============================
# 📊 Main Tabs
# ============================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Position Overview", 
    "📈 Hedging Strategies", 
    "📊 Options Analysis", 
    "📉 Market Data", 
    "🧮 Future Position Planning",
    "📥 Export Report"
])

# ============================
# 🎯 Tab 1: Position Overview
# ============================
with tab1:
    st.markdown('<p class="section-header">Current Position Analysis</p>', unsafe_allow_html=True)
    
    # --- User-friendly Position Data Input ---
    st.markdown('<div class="data-input-section">', unsafe_allow_html=True)
    st.subheader("📊 Edit Position Data")
    st.caption("Edit the table below and click 'Update Position Data' to refresh the dashboard.")
    
    # Use st.data_editor for a more interactive table
    # Exclude 'Total' row for editing
    editable_df = st.session_state.position_data_editor.drop(st.session_state.position_data_editor.index[-1]).copy()
    edited_df = st.data_editor(
        editable_df,
        use_container_width=True,
        num_rows="dynamic", # Allow adding/removing rows
        key="position_editor"
    )
    
    # Button to update calculations based on edited data
    if st.button("🔄 Update Position Data"):
        # Recalculate 'Total' row
        total_tons = edited_df['Tons'].sum()
        # Weighted average price calculation
        if total_tons > 0:
            total_value = (edited_df['Tons'] * edited_df['Holding Price (USD/ton)']).sum()
            total_avg_price = total_value / total_tons
        else:
            total_avg_price = 0.0
            
        total_balance = edited_df['Balance Funds (USD)'].sum()
        total_credit = edited_df['Open Position Limit (USD)'].sum()
        total_float = edited_df['Variable Margin (USD)'].sum()
        total_margin = edited_df['Initial Margin (USD)'].sum()
        total_pnl = edited_df['Unrealized PnL (USD)'].sum()
        
        # Create new 'Total' row
        total_row = pd.DataFrame([{
            "Account": "Total",
            "Tons": total_tons,
            "Holding Price (USD/ton)": total_avg_price,
            "Balance Funds (USD)": total_balance,
            "Open Position Limit (USD)": total_credit,
            "Variable Margin (USD)": total_float,
            "Initial Margin (USD)": total_margin,
            "Unrealized PnL (USD)": total_pnl
        }])
        
        # Combine edited data with new 'Total' row
        updated_df = pd.concat([edited_df, total_row], ignore_index=True)
        st.session_state.position_data_editor = updated_df
        
        # Update session state variables used throughout the app
        st.session_state.position_size_tons = total_tons
        st.session_state.avg_holding_price = total_avg_price
        st.session_state.current_funds_usd = total_balance + total_credit + total_float
        st.session_state.current_margin_usd = total_margin
        st.session_state.current_pnl_usd = total_pnl
        st.session_state.available_quota_usd = total_credit # Simplified assumption
        
        st.success("Position data updated!")
        st.rerun() # Rerun to reflect changes immediately
    
    st.markdown('</div>', unsafe_allow_html=True)
    # --- End Position Data Input ---

    # Use the latest data from session state for calculations
    # Default to 0 if not yet calculated
    position_size_tons = getattr(st.session_state, 'position_size_tons', 0)
    avg_holding_price = getattr(st.session_state, 'avg_holding_price', 0)
    current_funds_usd = getattr(st.session_state, 'current_funds_usd', 0)
    current_margin_usd = getattr(st.session_state, 'current_margin_usd', 0)
    current_pnl_usd = getattr(st.session_state, 'current_pnl_usd', 0)
    available_quota_usd = getattr(st.session_state, 'available_quota_usd', 0)
    funding_limit_usd = st.session_state.funding_limit_usd
    
    # Store in report data
    st.session_state.report_data.update({
        'position_size_tons': position_size_tons,
        'avg_holding_price': avg_holding_price,
        'current_funds_usd': current_funds_usd,
        'current_margin_usd': current_margin_usd,
        'current_pnl_usd': current_pnl_usd,
        'funding_limit_usd': funding_limit_usd,
    })
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Position Size", f"{position_size_tons:,.0f} tons")
    with col2:
        st.metric("Avg Holding Price", f"${avg_holding_price:,.2f}")
    with col3:
        st.metric("Current Funds", f"${current_funds_usd:,.0f}")
    with col4:
        st.metric("Current Margin", f"${current_margin_usd:,.0f}")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Current PnL", f"${current_pnl_usd:,.0f}")
    with col6:
        st.metric("Available Quota", f"${available_quota_usd:,.0f}")
    with col7:
        st.metric("Funding Limit", f"${funding_limit_usd:,.0f}")
    with col8:
        utilization = (current_funds_usd / funding_limit_usd) * 100 if funding_limit_usd > 0 else 0
        st.metric("Funding Utilization", f"{utilization:.1f}%")

    # Funding Limit Check
    if current_funds_usd > funding_limit_usd:
        st.markdown('<div class="limit-error">❌ <b>ALERT:</b> Current funds exceed the funding limit!</div>', unsafe_allow_html=True)
    elif utilization > 90:
        st.markdown('<div class="limit-warning">⚠️ <b>Warning:</b> Funding utilization is high.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="limit-success">✅ Funding utilization is within acceptable limits.</div>', unsafe_allow_html=True)

    # Price simulation (based on current position)
    st.markdown("#### Price Impact Simulation")
    price_change = st.slider("Price Change (USD/ton)", min_value=-500.0, max_value=500.0, value=-100.0, step=10.0, key="price_sim_slider_tab1")
    
    new_price = avg_holding_price + price_change
    pnl_change = price_change * position_size_tons
    new_pnl = current_pnl_usd + pnl_change
    new_funds = current_funds_usd + pnl_change
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("New Price", f"${new_price:,.2f}", f"{price_change:+,.2f}")
    with col2:
        st.metric("PnL Impact", f"${pnl_change:,.0f}")
    with col3:
        st.metric("New PnL", f"${new_pnl:,.0f}")
    with col4:
        st.metric("New Funds", f"${new_funds:,.0f}")
    
    # Visualize price impact
    prices = np.linspace(avg_holding_price - 1000, avg_holding_price + 1000, 50)
    pnl_values = (prices - avg_holding_price) * position_size_tons
    funds_values = current_funds_usd + pnl_values
    margin_values = [current_margin_usd] * len(prices) # Margin is fixed for current position
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=pnl_values, name="PnL Impact", line=dict(color='royalblue')))
    fig.add_trace(go.Scatter(x=prices, y=funds_values, name="Total Funds", line=dict(color='firebrick')))
    fig.add_trace(go.Scatter(x=prices, y=margin_values, name="Margin Requirement", line=dict(color='orange', dash='dot')))
    fig.add_hline(y=funding_limit_usd, line_dash="dash", line_color="red", annotation_text="Funding Limit")
    fig.add_vline(x=avg_holding_price, line_dash="dash", line_color="green", annotation_text="Current Price")
    fig.update_layout(title="Price Impact on PnL, Funds, and Margin",
                     xaxis_title="Copper Price (USD/tonne)",
                     yaxis_title="USD",
                     hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)

# ============================
# 📈 Tab 2: Hedging Strategies
# ============================
with tab2:
    st.markdown('<p class="section-header">Futures Hedging Strategies</p>', unsafe_allow_html=True)
    
    # Use data from session state
    position_size_tons = getattr(st.session_state, 'position_size_tons', 0)
    avg_holding_price = getattr(st.session_state, 'avg_holding_price', 0)
    current_margin_usd = getattr(st.session_state, 'current_margin_usd', 0)
    
    # --- Editable Forward Curve Data Input ---
    st.markdown('<div class="data-input-section">', unsafe_allow_html=True)
    st.subheader("📈 Edit Forward Curve Data")
    st.caption("Edit the table below and click 'Update Forward Curve' to refresh the chart and calculations.")
    
    edited_forward_curve_df = st.data_editor(
        st.session_state.forward_curve_data_editor,
        use_container_width=True,
        num_rows="dynamic",
        key="forward_curve_editor"
    )
    
    if st.button("🔄 Update Forward Curve"):
        st.session_state.forward_curve_data_editor = edited_forward_curve_df
        st.success("Forward curve data updated!")
        st.rerun() # Rerun to reflect changes immediately
        
    st.markdown('</div>', unsafe_allow_html=True)
    # --- End Forward Curve Data Input ---
    
    forward_curve = st.session_state.forward_curve_data_editor

    # Display forward curve
    if not forward_curve.empty:
        fig = px.line(forward_curve, x='Tenor', y='Price (USD/ton)', title='Copper Forward Curve')
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Please add data to the forward curve table.")
        
    # Hedging recommendations
    st.markdown("#### Hedging Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Spread Trade")
        st.write(f"Buy Dec-2025, Sell {hedge_tenor}")
        
        # Calculate approximate spread if both months exist
        if 'Dec25' in forward_curve['Tenor'].values:
            dec_price = forward_curve[forward_curve['Tenor'] == 'Dec25']['Price (USD/ton)'].iloc[0]
            # Find the hedge tenor in the dataframe
            hedge_month = hedge_tenor.replace('-2025', '25').replace('-2026', '26')
            if hedge_month in forward_curve['Tenor'].values:
                hedge_price = forward_curve[forward_curve['Tenor'] == hedge_month]['Price (USD/ton)'].iloc[0]
                spread = dec_price - hedge_price
                spread_per_lot = spread * st.session_state.lme_tons_per_lot
                
                st.metric("Estimated Spread", f"${spread:.2f}", f"${spread_per_lot:.0f} per lot")
                
                # Calculate margin impact (simplified)
                lots_current = position_size_tons / st.session_state.lme_tons_per_lot
                spread_margin_per_lot = st.session_state.lme_margin_per_lot_usd * 0.2  # Assuming 20% for spread
                lots_to_hedge = lots_current * hedge_ratio
                margin_reduction = lots_to_hedge * spread_margin_per_lot
                
                st.metric("Estimated Margin Reduction", f"${margin_reduction:,.0f}")
            else:
                st.info(f"Hedge tenor {hedge_month} not found in forward curve data.")
        else:
            st.info("Dec-2025 not found in forward curve data.")
    
    with col2:
        st.markdown("##### Hedge Effectiveness")
        st.write(f"Hedging Ratio: {hedge_ratio*100:.0f}%")
        
        # Calculate risk reduction (simplified)
        lots_current = position_size_tons / st.session_state.lme_tons_per_lot
        # Use vol_bid from sidebar inputs (need to get it)
        vol_bid = st.session_state.get('vol_bid_tmp', 17.92) # Default or from temp state
        
        current_risk = lots_current * st.session_state.lme_margin_per_lot_usd * (vol_bid/100)
        hedged_risk = current_risk * (1 - hedge_ratio)
        risk_reduction = current_risk - hedged_risk
        
        # --- FIX: Check for division by zero ---
        if current_risk > 0:
            risk_reduction_pct_str = f"{risk_reduction/current_risk*100:.1f}%"
        else:
            risk_reduction_pct_str = "N/A%" # Or "0.0%" if current_risk is 0, reduction is 0%
        
        st.metric("Risk Reduction", f"${risk_reduction:,.0f}", risk_reduction_pct_str)
        # --- END FIX ---
        
        # Store hedging data for report
        st.session_state.report_data.update({
            'hedge_ratio': hedge_ratio,
            'hedge_tenor': hedge_tenor,
            'margin_reduction': margin_reduction if 'margin_reduction' in locals() else 0,
            'risk_reduction': risk_reduction,
            'hedged_margin_call': avg_holding_price # Placeholder
        })

# ============================
# 📊 Tab 3: Options Analysis
# ============================
with tab3:
    st.markdown('<p class="section-header">Options Hedging Strategies</p>', unsafe_allow_html=True)
    
    # Use data from session state
    position_size_tons = getattr(st.session_state, 'position_size_tons', 0)
    avg_holding_price = getattr(st.session_state, 'avg_holding_price', 0)
    
    # --- Market Data Inputs for Options (Moved here) ---
    st.subheader("📊 Input Market Parameters for Options")
    col1, col2, col3 = st.columns(3)
    with col1:
        vol_ask = st.number_input("Volatility Ask (%)", min_value=0.01, value=17.92, step=0.1, key="vol_ask_tab3", format="%.2f")
        # Store temporarily for use in other tabs
        st.session_state.vol_ask_tmp = vol_ask
    with col2:
        vol_bid = st.number_input("Volatility Bid (%)", min_value=0.01, value=17.92, step=0.1, key="vol_bid_tab3", format="%.2f")
        st.session_state.vol_bid_tmp = vol_bid
    with col3:
        risk_free_rate = st.number_input("Risk-Free Rate (%)", min_value=0.0, value=4.027, step=0.1, key="rfr_tab3")
    st.markdown("---")
    # --- End Market Data Inputs ---
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Protective Put Strategy")
        st.write("Buy puts to protect against downside risk")
        
        # Calculate put option parameters
        put_strike = st.slider("Put Strike (% OTM)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, key="put_strike")
        strike_price = avg_holding_price * (1 - put_strike/100)
        
        # Option expiry selection
        option_expiry_days = st.selectbox("Option Expiry", [30, 60, 90, 180], index=2, key="put_expiry")
        T = option_expiry_days / 365.0
        
        # Use accurate Black model
        S = avg_holding_price
        K = strike_price
        r = risk_free_rate / 100
        sigma = vol_bid / 100
        
        put_price, put_delta = black_price(S, K, T, r, sigma, "Put")
        put_premium_per_ton = put_price
        # Calculate lots for options sizing
        lots_current = position_size_tons / st.session_state.lme_tons_per_lot
        put_premium_per_lot = put_price * st.session_state.lme_tons_per_lot
        
        st.metric("Put Premium", f"${put_price:.2f}", f"${put_premium_per_lot:.0f} per lot")
        
        # Calculate cost of protection
        protection_cost = lots_current * put_premium_per_lot
        st.metric("Total Protection Cost", f"${protection_cost:,.0f}")
    
    with col2:
        st.markdown("##### Risk Reversal Strategy")
        st.write("Sell OTM calls to finance OTM puts")
        
        call_strike = st.slider("Call Strike (% OTM)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, key="call_strike")
        call_strike_price = avg_holding_price * (1 + call_strike/100)
        
        # Option expiry selection
        option_expiry_days_call = st.selectbox("Call Option Expiry", [30, 60, 90, 180], index=2, key="call_expiry")
        T_call = option_expiry_days_call / 365.0
        
        # Use accurate Black model
        S = avg_holding_price
        K = call_strike_price
        r = risk_free_rate / 100
        sigma = vol_ask / 100
        
        call_price, call_delta = black_price(S, K, T_call, r, sigma, "Call")
        call_premium_per_ton = call_price
        call_premium_per_lot = call_price * st.session_state.lme_tons_per_lot
        
        st.metric("Call Premium", f"${call_price:.2f}", f"${call_premium_per_lot:.0f} per lot")
        
        # Calculate net cost
        lots_current = position_size_tons / st.session_state.lme_tons_per_lot
        net_cost = (put_premium_per_lot - call_premium_per_lot) * lots_current
        st.metric("Net Cost of Hedge", f"${net_cost:,.0f}")
    
    # Store options data for report
    st.session_state.report_data.update({
        'protection_cost': protection_cost if 'protection_cost' in locals() else 0,
        'net_cost': net_cost if 'net_cost' in locals() else 0
    })

# ============================
# 📉 Tab 4: Market Data
# ============================
with tab4:
    st.markdown('<p class="section-header">Market Data & LME Spreads</p>', unsafe_allow_html=True)
    
    # --- Editable LME Spread Data Input ---
    st.markdown('<div class="data-input-section">', unsafe_allow_html=True)
    st.subheader("📉 Edit LME Spread Data")
    st.caption("Edit the table below and click 'Update Spreads' to refresh the chart and data.")
    
    edited_spread_df = st.data_editor(
        st.session_state.spread_data_editor,
        use_container_width=True,
        num_rows="dynamic",
        key="spread_editor"
    )
    
    if st.button("🔄 Update Spreads"):
        st.session_state.spread_data_editor = edited_spread_df
        st.success("Spread data updated!")
        st.rerun() # Rerun to reflect changes immediately
        
    st.markdown('</div>', unsafe_allow_html=True)
    # --- End LME Spread Data Input ---
    
    spreads_df = st.session_state.spread_data_editor.copy()
    
    if not spreads_df.empty:
        # Calculate mid and change (assuming last = mid for simplicity)
        spreads_df['Last'] = (spreads_df['Bid'] + spreads_df['Ask']) / 2
        spreads_df['Change'] = 0.0  # Would be calculated from previous data
        
        st.markdown("#### LME Copper Spreads")
        st.dataframe(spreads_df, use_container_width=True)
        
        # Visualize spreads
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Bid', x=spreads_df['Spread Label'], y=spreads_df['Bid'])) 
        fig.add_trace(go.Bar(name='Ask', x=spreads_df['Spread Label'], y=spreads_df['Ask']))
        fig.update_layout(title="LME Copper Spreads", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Please add data to the spread table.")

# ============================
# 🧮 Tab 5: Future Position Planning
# ============================
with tab5:
    st.markdown('<p class="section-header">Future Position Planning</p>', unsafe_allow_html=True)
    
    st.markdown("""
    Plan future trades based on market outlook while respecting the funding limit.
    This replicates the logic from the Excel "资金测算" (Fund Calculation) section.
    """)
    
    # Use data from session state
    position_size_tons = getattr(st.session_state, 'position_size_tons', 0)
    avg_holding_price = getattr(st.session_state, 'avg_holding_price', 0)
    current_funds_usd = getattr(st.session_state, 'current_funds_usd', 0)
    current_margin_usd = getattr(st.session_state, 'current_margin_usd', 0)
    current_pnl_usd = getattr(st.session_state, 'current_pnl_usd', 0)
    funding_limit_usd = st.session_state.funding_limit_usd

    col1, col2 = st.columns(2)
    with col1:
        target_price = st.number_input(
            "Target Price (USD/ton)", 
            value=10130.0, 
            step=10.0,
            help="The hypothetical future copper price for planning."
        )
    with col2:
        additional_tons = st.number_input(
            "Additional Tons", 
            value=500.0, 
            min_value=0.0,
            step=100.0,
            help="The amount of copper (in tons) you plan to add to your position."
        )

    if st.button("Calculate Plan"):
        # --- Perform Calculations based on Excel logic ---
        new_total_tons = position_size_tons + additional_tons
        
        # New Average Price (Weighted Average)
        if new_total_tons > 0:
             new_avg_price = ((position_size_tons * avg_holding_price) + (additional_tons * target_price)) / new_total_tons
        else:
             new_avg_price = avg_holding_price

        # New Margin Requirement (based on LME rules)
        new_total_lots = new_total_tons / st.session_state.lme_tons_per_lot
        new_margin_usd = new_total_lots * st.session_state.lme_margin_per_lot_usd # Convert to USD
        
        # Estimated PnL for the *entire new position* at the target price
        estimated_pnl_per_ton = target_price - new_avg_price
        estimated_pnl_usd = estimated_pnl_per_ton * new_total_tons # Convert to USD
        
        # Required Funds (in USD) - This is the key check against the limit
        # It's the margin needed minus the benefit of PnL (if positive)
        required_funds_usd = new_margin_usd - estimated_pnl_usd
        
        # Remaining Available Funds (in USD) - Aligning with Excel's "资金测算" logic for "剩余可用资金（万美元）":
        # (Original Balance Funds + Original Open Position Limit + Original Variable Margin) - New_Margin - New_PnL
        original_total_funds_usd = current_funds_usd # This already includes all three
        remaining_funds_usd = original_total_funds_usd - new_margin_usd - estimated_pnl_usd

        # --- Feasibility Check ---
        is_feasible = True
        feasibility_message = "✅ Plan is feasible."
        messages = []

        if required_funds_usd > funding_limit_usd:
            is_feasible = False
            messages.append("❌ Required funds exceed the funding limit.")
        
        if remaining_funds_usd < 0:
            is_feasible = False
            messages.append("❌ Plan would result in negative available funds.")
            
        if not is_feasible:
            feasibility_message = "❌ Plan is NOT feasible. " + " ".join(messages)

        # --- Display Results ---
        st.markdown("---")
        st.subheader("Calculation Results")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("New Total Position", f"{new_total_tons:,.0f} tons")
            st.metric("New Average Price", f"${new_avg_price:,.2f}")
            st.metric("New Margin Requirement", f"${new_margin_usd:,.0f}")
            st.metric("Estimated PnL", f"${estimated_pnl_usd:,.0f}")

        with res_col2:
            st.metric("Required Funds", f"${required_funds_usd:,.0f}")
            st.metric("Remaining Funds", f"${remaining_funds_usd:,.0f}")
            st.metric("Funding Limit", f"${funding_limit_usd:,.0f}")
            
        if is_feasible:
            st.markdown(f'<div class="limit-success">{feasibility_message}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="limit-error">{feasibility_message}</div>', unsafe_allow_html=True)
            
        # Store scenario data for report
        st.session_state.report_data['planning_scenario'] = {
            'target_price': target_price,
            'additional_tons': additional_tons,
            'new_total_tons': new_total_tons,
            'new_avg_price': new_avg_price,
            'required_funds_usd': required_funds_usd,
            'remaining_funds_usd': remaining_funds_usd,
            'feasibility': feasibility_message
        }

        # --- Verification against Excel ---
        # Example from Excel row: $10,130, 500 tons
        # Expected from Excel:
        # New Total Position: 10000 tons
        # New Avg Price: 9897.59
        # New Margin: 800 wan USD = 8,000,000 USD
        # Estimated PnL: 232 wan USD = 2,320,000 USD
        # Required Funds (Planned Additional Funds): 568 wan USD = 5,680,000 USD
        # Remaining Funds (Available Funds Remaining): 454 wan USD = 4,540,000 USD
        # Let's check if our calculation matches for this specific case
        if abs(target_price - 10130.0) < 0.1 and abs(additional_tons - 500.0) < 0.1:
            st.markdown("---")
            st.subheader("Verification against Excel Sample")
            excel_checks = [
                (new_total_tons, 10000, "New Total Position"),
                (new_avg_price, 9897.59, "New Average Price"),
                (new_margin_usd, 8_000_000, "New Margin Requirement"),
                (estimated_pnl_usd, 2_320_000, "Estimated PnL"),
                (required_funds_usd, 5_680_000, "Required Funds (Planned Additional Funds)"),
                (remaining_funds_usd, 4_540_000, "Remaining Available Funds")
            ]
            all_match = True
            for calc_val, excel_val, desc in excel_checks:
                tolerance = max(abs(excel_val) * 0.01, 1.0) # 1% tolerance or 1 USD
                if abs(calc_val - excel_val) > tolerance:
                    st.warning(f"⚠️ {desc}: Calculated {calc_val:,.0f}, Excel {excel_val:,.0f}")
                    all_match = False
            if all_match:
                st.success("✅ All calculations match the Excel sample row ($10,130, 500 tons) within tolerance.")


# ============================
# 📥 Tab 6: Export Report
# ============================
with tab6:
    st.markdown('<p class="section-header">Export Report for Finance Department</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="export-section">
    <h3>Generate Comprehensive Report</h3>
    <p>Create a detailed report for the finance department with all position details, 
    hedging strategies, and recommendations. The report will include:</p>
    <ul>
        <li>Position summary and risk metrics</li>
        <li>Hedging strategy analysis</li>
        <li>Options strategy evaluation</li>
        <li>Market data overview</li>
        <li>Professional recommendations</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Report customization
    st.markdown("#### Report Customization")
    col1, col2 = st.columns(2)
    
    with col1:
        report_title = st.text_input("Report Title", "LME Copper Hedging Strategy Analysis")
        # include_exec_summary = st.checkbox("Include Executive Summary", value=True) # Not implemented in current export
    
    with col2:
        company_name = st.text_input("Company Name", "Trading Division")
        preparer_name = st.text_input("Prepared By", st.session_state.get('preparer_name', ''))
    
    # Store preparer name in session state
    if preparer_name:
        st.session_state.preparer_name = preparer_name
    
    # Generate report button
    if st.button("Generate Report", type="primary"):
        with st.spinner("Generating report..."):
            if report_format == "PDF":
                pdf_buffer = create_pdf_report(st.session_state.report_data)
                st.success("PDF report generated successfully!")
                
                # Download button for PDF
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_buffer,
                    file_name=f"lme_copper_hedging_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf"
                )
            else:  # Excel
                excel_buffer = create_excel_report(st.session_state.report_data)
                st.success("Excel report generated successfully!")
                
                # Download button for Excel
                st.download_button(
                    label="Download Excel Report",
                    data=excel_buffer,
                    file_name=f"lme_copper_hedging_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        st.markdown("""
        <div class="highlight-box">
        <h4>Next Steps</h4>
        <ol>
            <li>Download the report using the button above</li>
            <li>Share with the finance department for review</li>
            <li>Monitor positions and adjust strategies as market conditions change</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

# ============================
# 🧾 Footer
# ============================
st.markdown("---")
st.sidebar.divider()
st.sidebar.caption("LME Copper Hedging Dashboard")
st.sidebar.caption("1 lot = 25 tons. Margin per lot = $20,000.")
