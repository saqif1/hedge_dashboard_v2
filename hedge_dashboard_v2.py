import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
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
</style>
""", unsafe_allow_html=True)

# ============================
# 🚀 Initialize Session State
# ============================
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}
if 'position_size' not in st.session_state:
    st.session_state.position_size = 200
if 'price_per_lot' not in st.session_state:
    st.session_state.price_per_lot = 20000.0
if 'capital' not in st.session_state:
    st.session_state.capital = 15000000.0
if 'max_loss' not in st.session_state:
    st.session_state.max_loss = 3000.0
if 'margin_per_dollar' not in st.session_state:
    st.session_state.margin_per_dollar = 25.0

# ============================
# 🧮 Black Model for Futures Options (LME Compliant)
# ============================
def black_price(S, K, T, r, sigma, option_type="Put"):
    """Calculate option price and delta using Black Model for futures options."""
    if T <= 0 or sigma <= 0:
        return 0.0, 0.0
    d1 = (np.log(S / K) + (0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

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
        ['Capital (USD)', f"${report_data.get('capital', 0):,.0f}"],
        ['Position Size (Lots)', f"{report_data.get('position_size', 0):,}"],
        ['Current Price (USD/tonne)', f"${report_data.get('current_price', 0):,.1f}"],
        ['Contract Value (USD)', f"${report_data.get('contract_value', 0):,.0f}"],
        ['Margin Requirement (USD)', f"${report_data.get('margin_requirement', 0):,.0f}"],
        ['Margin Buffer (USD)', f"${report_data.get('margin_buffer', 0):,.0f}"],
        ['Margin Call Price (USD/tonne)', f"${report_data.get('margin_call_price', 0):,.1f}"],
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
    
    # Hedging Strategy
    elements.append(Paragraph("Hedging Strategy", styles['Heading2']))
    hedging_data = [
        ['Parameter', 'Value'],
        ['Hedging Ratio', f"{report_data.get('hedge_ratio', 0)*100:.1f}%"],
        ['Hedge Tenor', report_data.get('hedge_tenor', 'N/A')],
        ['Margin Reduction (USD)', f"${report_data.get('margin_reduction', 0):,.0f}"],
        ['Risk Reduction (USD)', f"${report_data.get('risk_reduction', 0):,.0f}"],
        ['Improved Margin Call Price (USD/tonne)', f"${report_data.get('hedged_margin_call', 0):,.1f}"],
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
            'Metric': ['Capital (USD)', 'Position Size (Lots)', 'Current Price (USD/tonne)', 
                      'Contract Value (USD)', 'Margin Requirement (USD)', 
                      'Margin Buffer (USD)', 'Margin Call Price (USD/tonne)'],
            'Value': [f"${report_data.get('capital', 0):,.0f}", 
                     f"{report_data.get('position_size', 0):,}",
                     f"${report_data.get('current_price', 0):,.1f}",
                     f"${report_data.get('contract_value', 0):,.0f}",
                     f"${report_data.get('margin_requirement', 0):,.0f}",
                     f"${report_data.get('margin_buffer', 0):,.0f}",
                     f"${report_data.get('margin_call_price', 0):,.1f}"]
        })
        position_summary.to_excel(writer, sheet_name='Position Summary', index=False)
        
        # Hedging Strategy sheet
        hedging_strategy = pd.DataFrame({
            'Parameter': ['Hedging Ratio', 'Hedge Tenor', 'Margin Reduction (USD)', 
                         'Risk Reduction (USD)', 'Improved Margin Call Price (USD/tonne)'],
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
        
        # Market Data sheet
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

# Sidebar for inputs
with st.sidebar:
    st.image("logo.png", width=80)
    st.divider()
    
    st.header("📊 Position Details")
    st.session_state.position_size = st.number_input(
        "Position Size (lots)", 
        min_value=1, 
        value=st.session_state.position_size, 
        step=10,
        help="1 lot = 25 tons of copper. LME standard."
    )
    st.session_state.price_per_lot = st.number_input(
        "Price per Lot ($)", 
        value=float(st.session_state.price_per_lot), 
        step=100.0,
        help="Current market price per futures contract (lot)."
    )
    st.session_state.capital = st.number_input(
        "Capital ($)", 
        value=float(st.session_state.capital), 
        step=100000.0,
        help="Total available capital for this position."
    )
    st.session_state.max_loss = st.number_input(
        "Max Loss Before Margin Call ($)", 
        value=float(st.session_state.max_loss), 
        step=100.0,
        help="Threshold beyond which margin call is triggered."
    )
    st.session_state.margin_per_dollar = st.number_input(
        "Margin per $1 Move per Contract ($)", 
        value=float(st.session_state.margin_per_dollar), 
        step=1.0,
        help="LME rule: $25 per $1 move per lot for copper."
    )
    
    st.header("📈 Market Data Inputs")
    # User inputs for forward curve
    st.subheader("Forward Curve")
    months_input = st.text_input(
        "Months (comma-separated)", 
        value="Spot,1M,2M,3M,Dec25,Mar26,Jun26",
        help="Enter contract months (e.g., Spot,1M,2M,3M,Dec25,Mar26)"
    )
    prices_input = st.text_input(
        "Prices (comma-separated)", 
        value="9400,9410,9420,9430,9450,9500,9550",
        help="Enter prices for each month (e.g., 9400,9410,9420,9430,9450,9500)"
    )
    
    # User inputs for spreads
    st.subheader("Market Spreads")
    spread_labels_input = st.text_input(
        "Spread Labels (comma-separated)", 
        value="Cash-3M,Oct25-3M,Nov25-3M,Dec25-3M,3M-Mar26,3M-Jun26",
        help="Enter spread labels (e.g., Cash-3M,Oct25-3M,Dec25-3M)"
    )
    spread_bids_input = st.text_input(
        "Bid Spreads (comma-separated)", 
        value="-70,-43,-16,3,-18,-40",
        help="Enter bid spreads (e.g., -70,-43,-16,3,-18,-40)"
    )
    spread_asks_input = st.text_input(
        "Ask Spreads (comma-separated)", 
        value="-73,-43,-17,2.7,-19,-48",
        help="Enter ask spreads (e.g., -73,-43,-17,2.7,-19,-48)"
    )
    
    # Market parameters
    vol_ask = st.number_input("Volatility Ask (%)", min_value=0.0, value=17.92, step=0.1)
    vol_bid = st.number_input("Volatility Bid (%)", min_value=0.0, value=17.92, step=0.1)
    risk_free_rate = st.number_input("Risk-Free Rate (%)", min_value=0.0, value=4.027, step=0.1)
    
    st.header("🛡️ Hedging Preferences")
    hedge_ratio = st.slider("Hedging Ratio", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
    hedge_tenor = st.selectbox("Hedge Tenor", ["3M", "6M", "Dec-2025", "Mar-2026", "Jun-2026"])
    
    st.header("📤 Report Options")
    include_charts = st.checkbox("Include Charts in Report", value=True)
    report_format = st.selectbox("Report Format", ["PDF", "Excel"])

# ============================
# 📊 Main Tabs
# ============================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Position Overview", 
    "📈 Hedging Strategies", 
    "📊 Options Analysis", 
    "📉 Market Data", 
    "📥 Export Report"
])

# ============================
# 🎯 Tab 1: Position Overview
# ============================
with tab1:
    st.markdown('<p class="section-header">Current Position Analysis</p>', unsafe_allow_html=True)
    
    # Calculate position metrics
    contract_value = st.session_state.position_size * 25 * (st.session_state.price_per_lot / 25)  # Convert to per ton
    margin_requirement = st.session_state.position_size * st.session_state.margin_per_dollar * 25  # per contract
    margin_buffer = st.session_state.capital - margin_requirement
    price_buffer = margin_buffer / (st.session_state.position_size * 25)
    margin_call_price = (st.session_state.price_per_lot / 25) - price_buffer  # per ton
    
    # Store in session state for report generation
    st.session_state.report_data.update({
        'capital': st.session_state.capital,
        'position_size': st.session_state.position_size,
        'current_price': st.session_state.price_per_lot / 25,
        'contract_value': contract_value,
        'margin_requirement': margin_requirement,
        'margin_buffer': margin_buffer,
        'margin_call_price': margin_call_price
    })
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Contract Value", f"${contract_value:,.0f}")
    with col2:
        st.metric("Margin Requirement", f"${margin_requirement:,.0f}")
    with col3:
        st.metric("Margin Buffer", f"${margin_buffer:,.0f}")
    with col4:
        st.metric("Margin Call Price", f"${margin_call_price:,.1f}")
    
    # Price simulation
    st.markdown("#### Price Impact Simulation")
    price_change = st.slider("Price Change (USD)", min_value=-500, max_value=500, value=-100, step=10)
    
    new_price = (st.session_state.price_per_lot / 25) + price_change
    pnl_change = price_change * st.session_state.position_size * 25
    new_margin_buffer = margin_buffer + pnl_change
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("New Price", f"${new_price:,.1f}", f"{price_change:,.1f}")
    with col2:
        st.metric("PnL Impact", f"${pnl_change:,.0f}")
    with col3:
        status = "Margin Call Risk" if new_margin_buffer < 0 else "Within Limits"
        color = "inverse" if new_margin_buffer < 0 else "normal"
        st.metric("New Margin Buffer", f"${new_margin_buffer:,.0f}", delta=status, delta_color=color)
    
    # Visualize price impact
    prices = np.linspace((st.session_state.price_per_lot / 25) - 1000, (st.session_state.price_per_lot / 25) + 1000, 50)
    pnl_values = (prices - (st.session_state.price_per_lot / 25)) * st.session_state.position_size * 25
    margin_values = margin_buffer + pnl_values
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=pnl_values, name="PnL Impact", line=dict(color='royalblue')))
    fig.add_trace(go.Scatter(x=prices, y=margin_values, name="Margin Buffer", line=dict(color='firebrick')))
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Margin Call Level")
    fig.add_vline(x=(st.session_state.price_per_lot / 25), line_dash="dash", line_color="green", annotation_text="Current Price")
    fig.update_layout(title="Price Impact on PnL and Margin Buffer",
                     xaxis_title="Copper Price (USD/tonne)",
                     yaxis_title="USD",
                     hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)

# ============================
# 📈 Tab 2: Hedging Strategies
# ============================
with tab2:
    st.markdown('<p class="section-header">Futures Hedging Strategies</p>', unsafe_allow_html=True)
    
    # Parse forward curve data
    try:
        months_list = [m.strip() for m in months_input.split(',')]
        prices_list = [float(p.strip()) for p in prices_input.split(',')]
        
        if len(months_list) != len(prices_list):
            st.error("Number of months must match number of prices!")
        else:
            # Create forward curve dataframe
            forward_curve = pd.DataFrame({
                'Tenor': months_list,
                'Price': prices_list
            })
            
            # Display forward curve
            fig = px.line(forward_curve, x='Tenor', y='Price', title='Copper Forward Curve')
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)
            
            # Hedging recommendations
            st.markdown("#### Hedging Recommendations")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Spread Trade")
                st.write(f"Buy Dec-2025, Sell {hedge_tenor}")
                
                # Calculate approximate spread if both months exist
                if 'Dec25' in months_list and hedge_tenor.replace('-2025', '25').replace('-2026', '26') in [m.replace('-', '') for m in months_list]:
                    try:
                        dec_price = forward_curve[forward_curve['Tenor'] == 'Dec25']['Price'].iloc[0]
                        hedge_month = hedge_tenor.replace('-2025', '25').replace('-2026', '26')
                        hedge_price = forward_curve[forward_curve['Tenor'] == hedge_month]['Price'].iloc[0]
                        spread = dec_price - hedge_price
                        spread_per_lot = spread * 25
                        
                        st.metric("Estimated Spread", f"${spread:.2f}", f"${spread_per_lot:.0f} per lot")
                        
                        # Calculate margin impact
                        spread_margin = st.session_state.margin_per_dollar * 0.2  # Assuming 20% of outright margin for spread
                        total_margin = (st.session_state.position_size * st.session_state.margin_per_dollar * 25 * (1 - hedge_ratio)) + (st.session_state.position_size * spread_margin * 25 * hedge_ratio)
                        margin_reduction = margin_requirement - total_margin
                        
                        st.metric("Margin Reduction", f"${margin_reduction:,.0f}", f"{margin_reduction/margin_requirement*100:.1f}%")
                    except:
                        st.warning("Could not calculate spread - check month names")
                else:
                    st.info("Enter valid months to calculate spread")
            
            with col2:
                st.markdown("##### Hedge Effectiveness")
                st.write(f"Hedging Ratio: {hedge_ratio*100:.0f}%")
                
                # Calculate risk reduction
                unhedged_risk = st.session_state.position_size * 25 * (st.session_state.price_per_lot / 25) * (vol_bid/100)
                hedged_risk = unhedged_risk * (1 - hedge_ratio)
                risk_reduction = unhedged_risk - hedged_risk
                
                st.metric("Risk Reduction", f"${risk_reduction:,.0f}", f"{risk_reduction/unhedged_risk*100:.1f}%")
                
                # Calculate new margin call price
                hedged_margin_call = (st.session_state.price_per_lot / 25) - (margin_buffer / (st.session_state.position_size * 25 * (1 - hedge_ratio)))
                improvement = hedged_margin_call - margin_call_price
                
                st.metric("Improved Margin Call Price", f"${hedged_margin_call:,.1f}", f"+${improvement:.1f}")
            
            # Store hedging data for report
            st.session_state.report_data.update({
                'hedge_ratio': hedge_ratio,
                'hedge_tenor': hedge_tenor,
                'margin_reduction': margin_reduction if 'margin_reduction' in locals() else 0,
                'risk_reduction': risk_reduction if 'risk_reduction' in locals() else 0,
                'hedged_margin_call': hedged_margin_call if 'hedged_margin_call' in locals() else margin_call_price
            })
    except Exception as e:
        st.error(f"Error parsing forward curve data: {str(e)}")

# ============================
# 📊 Tab 3: Options Analysis
# ============================
with tab3:
    st.markdown('<p class="section-header">Options Hedging Strategies</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Protective Put Strategy")
        st.write("Buy puts to protect against downside risk")
        
        # Calculate put option parameters
        put_strike = st.slider("Put Strike (% OTM)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, key="put_strike")
        strike_price = (st.session_state.price_per_lot / 25) * (1 - put_strike/100)
        
        # Option expiry selection
        option_expiry_days = st.selectbox("Option Expiry", [30, 60, 90, 180], index=2, key="put_expiry")
        T = option_expiry_days / 365.0
        
        # Use accurate Black model
        S = st.session_state.price_per_lot / 25
        K = strike_price
        r = risk_free_rate / 100
        sigma = vol_bid / 100
        
        put_price, put_delta = black_price(S, K, T, r, sigma, "Put")
        put_premium_per_lot = put_price * 25
        
        st.metric("Put Premium", f"${put_price:.2f}", f"${put_premium_per_lot:.0f} per lot")
        
        # Calculate cost of protection
        protection_cost = st.session_state.position_size * put_premium_per_lot
        st.metric("Total Protection Cost", f"${protection_cost:,.0f}")
    
    with col2:
        st.markdown("##### Risk Reversal Strategy")
        st.write("Sell OTM calls to finance OTM puts")
        
        call_strike = st.slider("Call Strike (% OTM)", min_value=0.0, max_value=10.0, value=5.0, step=0.5, key="call_strike")
        call_strike_price = (st.session_state.price_per_lot / 25) * (1 + call_strike/100)
        
        # Option expiry selection
        option_expiry_days_call = st.selectbox("Call Option Expiry", [30, 60, 90, 180], index=2, key="call_expiry")
        T_call = option_expiry_days_call / 365.0
        
        # Use accurate Black model
        S = st.session_state.price_per_lot / 25
        K = call_strike_price
        r = risk_free_rate / 100
        sigma = vol_ask / 100
        
        call_price, call_delta = black_price(S, K, T_call, r, sigma, "Call")
        call_premium_per_lot = call_price * 25
        
        st.metric("Call Premium", f"${call_price:.2f}", f"${call_premium_per_lot:.0f} per lot")
        
        # Calculate net cost
        net_cost = (put_premium_per_lot - call_premium_per_lot) * st.session_state.position_size
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
    
    # Parse spread data
    try:
        spread_labels = [s.strip() for s in spread_labels_input.split(',')]
        spread_bids = [float(b.strip()) for b in spread_bids_input.split(',')]
        spread_asks = [float(a.strip()) for a in spread_asks_input.split(',')]
        
        if len(spread_labels) != len(spread_bids) or len(spread_labels) != len(spread_asks):
            st.error("Number of labels, bids, and asks must match!")
        else:
            # Create spreads dataframe
            spreads_df = pd.DataFrame({
                'Spread': spread_labels,
                'Bid': spread_bids,
                'Ask': spread_asks
            })
            
            # Calculate mid and change (assuming last = mid for simplicity)
            spreads_df['Last'] = (spreads_df['Bid'] + spreads_df['Ask']) / 2
            spreads_df['Change'] = 0.0  # Would be calculated from previous data
            
            st.markdown("#### LME Copper Spreads")
            st.dataframe(spreads_df, use_container_width=True)
            
            # Visualize spreads
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Bid', x=spreads_df['Spread'], y=spreads_df['Bid'])) 
            fig.add_trace(go.Bar(name='Ask', x=spreads_df['Spread'], y=spreads_df['Ask']))
            fig.update_layout(title="LME Copper Spreads", barmode='group')
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error parsing spread data: {str(e)}")

# ============================
# 📥 Tab 5: Export Report
# ============================
with tab5:
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
        include_exec_summary = st.checkbox("Include Executive Summary", value=True)
    
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
            <li>Schedule a meeting to discuss implementation</li>
            <li>Monitor positions and adjust strategies as market conditions change</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

# ============================
# 🧾 Footer
# ============================
st.markdown("---")
st.sidebar.divider()
st.sidebar.caption("LME Copper Hedging Dashboard v2.0")