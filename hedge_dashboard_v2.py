import streamlit as st
import plotly.graph_objects as go

# ----------------------------
# Dashboard Title & Description
# ----------------------------
st.set_page_config(page_title="Advanced Options Hedge Dashboard", layout="wide")
st.title("Advanced Options Strategy Analyser for Futures Positions")

# ----------------------------
# Sidebar Inputs
# ----------------------------
st.sidebar.header("Basic Parameters")
cost_per_lot = st.sidebar.number_input("Initial Margin (USD/lot)", value=20000.0, step=1000.0)
lot_size_ton = st.sidebar.number_input("Lot Size (Tons)", value=25.0, step=1.0)
max_capital = st.sidebar.number_input("Max Capital for Futures (USD)", value=29200000.0, step=100000.0)

# Calculate maximum possible MT based on capital
max_mt = int((max_capital / cost_per_lot) * lot_size_ton)

# Position sizing in MT instead of lots
st.sidebar.subheader("Futures Position")
futures_position = st.sidebar.radio(
    "Futures Position Direction",
    ["Short", "Long"],
    index=0,
    help="Choose whether you are short or long futures"
)

exposure_mt = st.sidebar.number_input(
    "Futures Exposure (Metric Tons)",
    min_value=25,  # Minimum 1 lot
    max_value=max_mt,
    value=min(14000, max_mt),
    step=25,
    help=f"Maximum possible based on capital: {max_mt:,} ton"
)

# Calculate lots from MT exposure
actual_lots_used = exposure_mt / lot_size_ton

entry_price = st.sidebar.number_input("Futures Entry Price (USD/ton)", value=10130.0, step=10.0)
worst_case_price = st.sidebar.number_input("Scenario Analysis Price (USD/ton)", value=11550.0, step=10.0)

# ----------------------------
# OPTIONS STRATEGY CONFIGURATION
# ----------------------------
st.sidebar.header("Options Strategy Configuration")

st.sidebar.subheader("Call Option Position")
call_position = st.sidebar.radio(
    "Call Option Position",
    ["None", "Long", "Short"],
    index=1,
    help="Choose long (buy), short (sell), or none for call option"
)

if call_position != "None":
    strike_price_call = st.sidebar.number_input("Call Option Strike Price (USD/ton)", value=10500.0, step=50.0)
    premium_call_per_lot = st.sidebar.number_input("Call Option Premium (USD/lot)", value=3279.28, step=10.0)
    premium_call_per_ton = premium_call_per_lot / lot_size_ton
else:
    strike_price_call = 0
    premium_call_per_lot = 0
    premium_call_per_ton = 0

st.sidebar.subheader("Put Option Position")
put_position = st.sidebar.radio(
    "Put Option Position",
    ["None", "Long", "Short"],
    index=2,
    help="Choose long (buy), short (sell), or none for put option"
)

if put_position != "None":
    strike_price_put = st.sidebar.number_input("Put Option Strike Price (USD/ton)", value=9200.0, step=50.0)
    premium_put_per_lot = st.sidebar.number_input("Put Option Premium (USD/lot)", value=1840.88, step=10.0)
    premium_put_per_ton = premium_put_per_lot / lot_size_ton
else:
    strike_price_put = 0
    premium_put_per_lot = 0
    premium_put_per_ton = 0

# ----------------------------
# DYNAMIC STRATEGY CALCULATIONS
# ----------------------------

total_tons = exposure_mt
capital_used = actual_lots_used * cost_per_lot

def calculate_option_payoff(price, strike, option_type, position_type):
    """Calculate option payoff for any combination of option type and position"""
    if strike == 0:  # No option
        return 0
    
    if option_type == "call":
        if price > strike:
            intrinsic_value = price - strike
        else:
            intrinsic_value = 0
    else:  # put
        if price < strike:
            intrinsic_value = strike - price
        else:
            intrinsic_value = 0
    
    # Adjust for position type (long/short)
    if position_type == "long":
        return intrinsic_value
    else:  # short
        return -intrinsic_value

def calculate_option_premium_flow(position_type, premium_per_ton):
    """Calculate premium cash flow for option position"""
    if position_type == "long":
        return -premium_per_ton  # Pay premium
    elif position_type == "short":
        return premium_per_ton   # Receive premium
    else:
        return 0

# Calculate futures P&L based on position direction
if futures_position == "Short":
    futures_pnl_per_ton = entry_price - worst_case_price  # Gain if price falls
else:  # Long
    futures_pnl_per_ton = worst_case_price - entry_price  # Gain if price rises

# Calculate option payoffs
call_payoff_per_ton = calculate_option_payoff(worst_case_price, strike_price_call, "call", call_position)
put_payoff_per_ton = calculate_option_payoff(worst_case_price, strike_price_put, "put", put_position)

# Calculate premium flows
call_premium_flow_per_ton = calculate_option_premium_flow(call_position, premium_call_per_ton)
put_premium_flow_per_ton = calculate_option_premium_flow(put_position, premium_put_per_ton)

# Total premium flow
total_premium_flow_per_ton = call_premium_flow_per_ton + put_premium_flow_per_ton

# Calculate total strategy P&L per ton
strategy_pnl_per_ton = (futures_pnl_per_ton + call_payoff_per_ton + 
                        put_payoff_per_ton + total_premium_flow_per_ton)

# Convert to total values
total_futures_pnl = futures_pnl_per_ton * total_tons
total_call_payoff = call_payoff_per_ton * total_tons
total_put_payoff = put_payoff_per_ton * total_tons
total_premium_flow = total_premium_flow_per_ton * total_tons
total_strategy_pnl = strategy_pnl_per_ton * total_tons

# For display purposes
total_pnl_unhedged = total_futures_pnl
total_pnl_hedged = total_strategy_pnl
pnl_per_ton_unhedged = futures_pnl_per_ton
pnl_per_ton_hedged = strategy_pnl_per_ton

# ----------------------------
# STRATEGY IDENTIFICATION
# ----------------------------

def identify_strategy(futures_pos, call_pos, put_pos):
    """Identify the strategy based on positions"""
    strategies = {
        ("Short", "Long", "Short"): "Collar (Protective)",
        ("Short", "Long", "None"): "Protective Call",
        ("Short", "None", "Short"): "Covered Put",
        ("Short", "None", "None"): "Naked Short",
        ("Long", "Short", "Long"): "Reverse Collar",
        ("Long", "Short", "None"): "Covered Call",
        ("Long", "None", "Long"): "Protective Put",
        ("Long", "None", "None"): "Naked Long"
    }
    
    return strategies.get((futures_pos, call_pos, put_pos), f"Custom {futures_pos} + Options")

current_strategy = identify_strategy(futures_position, call_position, put_position)

# ----------------------------
# DYNAMIC DISPLAY RESULTS
# ----------------------------

st.header(f"📊 {current_strategy} Strategy Analysis at ${worst_case_price:,.0f}")

col1, col2, col3 = st.columns(3)
col1.metric("Futures Exposure", f"{exposure_mt:,.0f} ton", f"{actual_lots_used:,.0f} lots")
col1.metric("Futures Position", futures_position, f"Entry: ${entry_price:,.0f}")

# Dynamic delta colors and labels
unhedged_color = "inverse" if futures_pnl_per_ton < 0 else "normal"
hedged_color = "inverse" if strategy_pnl_per_ton < 0 else "normal"

unhedged_label = "Loss" if futures_pnl_per_ton < 0 else "Gain"
hedged_label = "Loss" if strategy_pnl_per_ton < 0 else "Gain"

col2.metric("P&L/Ton (Futures Only)", f"${futures_pnl_per_ton:,.0f}", 
           delta=unhedged_label, delta_color=unhedged_color)
col3.metric("P&L/Ton (With Options)", f"${strategy_pnl_per_ton:,.0f}", 
           delta=hedged_label, delta_color=hedged_color)

st.markdown("---")

col4, col5 = st.columns(2)
col4.metric("Total P&L (Futures Only)", f"${total_futures_pnl:,.0f}", 
           delta="Unprotected", delta_color=unhedged_color)
col5.metric("Total P&L (With Options)", f"${total_strategy_pnl:,.0f}", 
           delta=current_strategy, delta_color="off")

# ----------------------------
# OPTIONS PREMIUM BREAKDOWN
# ----------------------------

premium_info = "💰 **Options Premium Cash Flow**\n"

if call_position != "None":
    direction = "Paid" if call_position == "Long" else "Received"
    premium_info += f"- Call Premium {direction}: **\\${premium_call_per_lot * actual_lots_used:,.0f}** (\\${premium_call_per_ton:,.2f}/ton)\n"

if put_position != "None":
    direction = "Paid" if put_position == "Long" else "Received"
    premium_info += f"- Put Premium {direction}: **\\${premium_put_per_lot * actual_lots_used:,.0f}** (\\${premium_put_per_ton:,.2f}/ton)\n"

if call_position != "None" or put_position != "None":
    net_direction = "Net Outflow" if total_premium_flow < 0 else "Net Inflow"
    premium_info += f"- {net_direction}: **\\${abs(total_premium_flow):,.0f}** (\\${total_premium_flow_per_ton:,.2f}/ton)\n"

if total_strategy_pnl > total_futures_pnl:
    improvement = total_strategy_pnl - total_futures_pnl
    premium_info += f"- Options improve outcome by **\\${improvement:,.0f}**"
else:
    improvement = total_futures_pnl - total_strategy_pnl
    premium_info += f"- Options reduce loss by **\\${improvement:,.0f}**"

st.info(premium_info)

# ----------------------------
# DYNAMIC VISUALIZATION
# ----------------------------

fig = go.Figure(data=[
    go.Bar(
        name='Futures Only',
        x=['Scenario'],
        y=[total_futures_pnl],
        marker_color='firebrick' if total_futures_pnl < 0 else 'green',
        text=[f"${total_futures_pnl:,.0f}"],
        textposition='auto'
    ),
    go.Bar(
        name=f'With {current_strategy}',
        x=['Scenario'],
        y=[total_strategy_pnl],
        marker_color='red' if total_strategy_pnl < 0 else 'mediumseagreen',
        text=[f"${total_strategy_pnl:,.0f}"],
        textposition='auto'
    )
])
fig.update_layout(
    title=f"Portfolio Outcome: {current_strategy} vs Futures Only",
    yaxis_title="P&L (USD)",
    template="plotly_white",
    showlegend=True,
    height=400
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# DYNAMIC MARGIN SAFETY CHECK
# ----------------------------

st.header("⚠️ Capital Analysis After Scenario")

unhedged_remaining = max_capital + total_futures_pnl
hedged_remaining = max_capital + total_strategy_pnl

col6, col7 = st.columns(2)

with col6:
    st.markdown(f"**Strategy 1**: {futures_position} Futures Only")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    
    if futures_pnl_per_ton < 0:
        st.markdown(f"- Futures Loss: **${abs(total_futures_pnl):,.0f}**")
    else:
        st.markdown(f"+ Futures Gain: **${total_futures_pnl:,.0f}**")
    
    st.markdown(f"→ Remaining Capital: **${unhedged_remaining:,.0f}**")
    
    if unhedged_remaining < 0:
        st.error(f"🚨 MARGIN CALL! Shortfall: ${abs(unhedged_remaining):,.0f}")
    elif futures_pnl_per_ton < 0:
        st.warning(f"Capital remains: ${unhedged_remaining:,.0f} (Loss)")
    else:
        st.success(f"Capital remains: ${unhedged_remaining:,.0f} (Gain)")

with col7:
    st.markdown(f"**Strategy 2**: {current_strategy}")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    
    # Dynamic breakdown
    components = []
    
    if abs(total_futures_pnl) > 0:
        direction = "-" if total_futures_pnl < 0 else "+"
        label = "Loss" if total_futures_pnl < 0 else "Gain"
        components.append(f"{direction} Futures {label}: **${abs(total_futures_pnl):,.0f}**")
    
    if total_call_payoff != 0:
        direction = "+" if total_call_payoff > 0 else "-"
        label = "Gain" if total_call_payoff > 0 else "Loss"
        components.append(f"{direction} Call {label}: **${abs(total_call_payoff):,.0f}**")
    
    if total_put_payoff != 0:
        direction = "+" if total_put_payoff > 0 else "-"
        label = "Gain" if total_put_payoff > 0 else "Loss"
        components.append(f"{direction} Put {label}: **${abs(total_put_payoff):,.0f}**")
    
    if total_premium_flow != 0:
        direction = "+" if total_premium_flow > 0 else "-"
        label = "Inflow" if total_premium_flow > 0 else "Outflow"
        components.append(f"{direction} Premium {label}: **${abs(total_premium_flow):,.0f}**")
    
    for component in components:
        st.markdown(component)
    
    st.markdown(f"→ Remaining Capital: **${hedged_remaining:,.0f}**")
    
    if hedged_remaining < 0:
        st.error(f"🚨 MARGIN CALL! Shortfall: ${abs(hedged_remaining):,.0f}")
    elif strategy_pnl_per_ton < 0:
        st.warning(f"Capital remains: ${hedged_remaining:,.0f} (Reduced Loss)")
    else:
        st.success(f"Capital remains: ${hedged_remaining:,.0f} (Protected)")

# ----------------------------
# OPTIONS ANALYSIS
# ----------------------------

st.header("📈 Options Position Analysis")

col8, col9 = st.columns(2)

with col8:
    if call_position != "None":
        st.subheader(f"Call Option ({call_position})")
        if strike_price_call > 0:
            status = "ITM" if worst_case_price > strike_price_call else "OTM"
            color = "🟢" if status == "OTM" else "🛡️" if call_position == "Long" else "⚠️"
            
            if call_position == "Long":
                if status == "ITM":
                    st.success(f"{color} **Protection Active (ITM)**")
                    st.info(f"Strike: ${strike_price_call:,.0f} | Moneyness: +${worst_case_price - strike_price_call:,.0f}")
                    st.success(f"Payoff: +${call_payoff_per_ton:,.0f}/ton")
                else:
                    st.info(f"{color} **Protection Ready (OTM)**")
                    st.info(f"Strike: ${strike_price_call:,.0f} | Break-even: ${strike_price_call + premium_call_per_ton:,.0f}")
            else:  # Short call
                if status == "ITM":
                    st.warning(f"{color} **Obligation Active (ITM)**")
                    st.info(f"Strike: ${strike_price_call:,.0f} | Moneyness: +${worst_case_price - strike_price_call:,.0f}")
                    st.warning(f"Payoff: -${abs(call_payoff_per_ton):,.0f}/ton")
                else:
                    st.success(f"{color} **Premium Collected (OTM)**")
                    st.info(f"Strike: ${strike_price_call:,.0f} | Safe below: ${strike_price_call:,.0f}")
    else:
        st.info("No Call Option Position")

with col9:
    if put_position != "None":
        st.subheader(f"Put Option ({put_position})")
        if strike_price_put > 0:
            status = "ITM" if worst_case_price < strike_price_put else "OTM"
            color = "🟢" if status == "OTM" else "🛡️" if put_position == "Long" else "⚠️"
            
            if put_position == "Long":
                if status == "ITM":
                    st.success(f"{color} **Protection Active (ITM)**")
                    st.info(f"Strike: ${strike_price_put:,.0f} | Moneyness: +${strike_price_put - worst_case_price:,.0f}")
                    st.success(f"Payoff: +${put_payoff_per_ton:,.0f}/ton")
                else:
                    st.info(f"{color} **Protection Ready (OTM)**")
                    st.info(f"Strike: ${strike_price_put:,.0f} | Break-even: ${strike_price_put - premium_put_per_ton:,.0f}")
            else:  # Short put
                if status == "ITM":
                    st.warning(f"{color} **Obligation Active (ITM)**")
                    st.info(f"Strike: ${strike_price_put:,.0f} | Moneyness: +${strike_price_put - worst_case_price:,.0f}")
                    st.warning(f"Payoff: -${abs(put_payoff_per_ton):,.0f}/ton")
                else:
                    st.success(f"{color} **Premium Collected (OTM)**")
                    st.info(f"Strike: ${strike_price_put:,.0f} | Safe above: ${strike_price_put:,.0f}")
    else:
        st.info("No Put Option Position")

# ----------------------------
# STRATEGY RECOMMENDATION
# ----------------------------

st.header("🎯 Strategy Assessment")

if total_strategy_pnl > total_futures_pnl:
    improvement = total_strategy_pnl - total_futures_pnl
    if hedged_remaining > 0:
        st.success(f"""
        ✅ **{current_strategy} Is Effective**
        - Improves outcome by **\\${improvement:,.0f}** vs futures only
        - Provides better risk-adjusted returns
        - Strategy is working as intended
        """)
    else:
        st.warning(f"""
        ⚠️ **Strategy Helps But Capital Insufficient**
        - Improves by **\\${improvement:,.0f}** but margin call risk remains
        - Consider reducing position size
        """)
elif total_strategy_pnl == total_futures_pnl:
    st.info(f"""
    🔄 **{current_strategy} Is Cost-Neutral**
    - No significant improvement at current price level
    - Options are at-the-money or out-of-the-money
    - Review strike selection or consider alternative strategies
    """)
else:
    deterioration = total_futures_pnl - total_strategy_pnl
    st.error(f"""
    ❌ **{current_strategy} Reduces Performance**
    - Worse outcome by **\\${deterioration:,.0f}** vs futures only
    - Current options configuration not optimal for this scenario
    - Suggested: Adjust strikes or reconsider strategy
    """)

# ----------------------------
# STRATEGY GUIDE
# ----------------------------

with st.expander("📚 Common Strategies Guide"):
    st.markdown("""
    **Common Futures + Options Strategies:**
    
    **For Short Futures:**
    - **Collar**: Long Call + Short Put (Protects upside, earns premium)
    - **Protective Call**: Long Call only (Upside protection)
    - **Covered Put**: Short Put only (Earn premium, limited downside)
    
    **For Long Futures:**
    - **Reverse Collar**: Short Call + Long Put (Protects downside, earns premium)
    - **Protective Put**: Long Put only (Downside protection)
    - **Covered Call**: Short Call only (Earn premium, limited upside)
    
    **Customize your strategy by mixing long/short options positions!**
    """)

# ----------------------------
# Footer Note
# ----------------------------

st.markdown("---")
st.markdown("### Connect with Me!")

st.markdown("""
<a href="https://www.linkedin.com/in/saqif-juhaimee-17322a119/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20">
    Saqif Juhaimee
</a>
""", unsafe_allow_html=True)