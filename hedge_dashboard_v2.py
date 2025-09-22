import streamlit as st
import plotly.graph_objects as go

# ----------------------------
# Dashboard Title & Description
# ----------------------------
st.set_page_config(page_title="Copper Short Hedge Dashboard", layout="wide")
st.title("Scenario Analyser on Future Shorts Hedged with Collar Strategy")

# ----------------------------
# Sidebar Inputs
# ----------------------------
#st.sidebar.image("logo.png")
st.sidebar.header("Input Parameters")
cost_per_lot = st.sidebar.number_input("Initial Margin (USD/lot)", value=20000.0, step=1000.0)
lot_size_ton = st.sidebar.number_input("Lot Size (Tons)", value=25.0, step=1.0)
max_capital = st.sidebar.number_input("Max Capital for Futures (USD)", value=29200000.0, step=100000.0)

# Calculate maximum possible MT based on capital
max_mt = int((max_capital / cost_per_lot) * lot_size_ton)

# Position sizing in MT instead of lots
st.sidebar.subheader("Position Sizing")
exposure_mt = st.sidebar.number_input(
    "Short Exposure (Metric Tons)",
    min_value=25,  # Minimum 1 lot
    max_value=max_mt,
    value=min(14000, max_mt),  # Default to 25,000 MT or max, whichever is smaller
    step=25,  # Step by 1 lot equivalent (25 tons)
    help=f"Maximum possible based on capital: {max_mt:,} ton"
)

# Calculate lots from MT exposure
actual_lots_used = exposure_mt / lot_size_ton

entry_price = st.sidebar.number_input("Futures Entry Price (Short at USD/ton)", value=10130.0, step=10.0)
worst_case_price = st.sidebar.number_input("Worst Case Price (USD/ton)", value=11550.0, step=10.0)

# Input validation
if worst_case_price <= entry_price:
    st.sidebar.warning("Worst case price should be higher than entry price for short position analysis")

# Option parameters — UPDATED FOR COLLAR
st.sidebar.subheader("Collar Strategy: Buy Call + Sell Put")
strike_price_call = st.sidebar.number_input("Call Option Strike Price (USD/ton)", value=10350.0, step=50.0)
premium_call_per_lot = st.sidebar.number_input("Call Option Premium Paid (USD/lot)", value=4151.64, step=10.0)
premium_call_per_ton = premium_call_per_lot / lot_size_ton

strike_price_put = st.sidebar.number_input("Put Option Strike Price (USD/ton)", value=9270.0, step=50.0)
premium_put_per_lot = st.sidebar.number_input("Put Option Premium Received (USD/lot)", value=1840.88, step=10.0)
premium_put_per_ton = premium_put_per_lot / lot_size_ton

# Add strike price validations
if strike_price_call < entry_price:
    st.sidebar.warning("⚠️ Call strike below entry — only protects above call strike!")
if strike_price_put > entry_price:
    st.sidebar.warning("⚠️ Put strike above entry — exposes you to downside below put strike!")

# ----------------------------
# Calculations
# ----------------------------

total_tons = exposure_mt
capital_used = actual_lots_used * cost_per_lot

# Unhedged loss
loss_per_ton_unhedged = worst_case_price - entry_price
total_loss_unhedged = loss_per_ton_unhedged * total_tons

# Collar strategy calculations
net_option_premium_per_ton = premium_call_per_ton - premium_put_per_ton
net_option_premium_per_lot = premium_call_per_lot - premium_put_per_lot

# Initialize variables
option_gain_call_per_ton = 0
option_loss_put_per_ton = 0

if worst_case_price > strike_price_call:
    # Call is ITM → gain offsets futures loss
    option_gain_call_per_ton = worst_case_price - strike_price_call
    futures_loss_per_ton = worst_case_price - entry_price
    hedged_loss_per_ton = futures_loss_per_ton - option_gain_call_per_ton + net_option_premium_per_ton
elif worst_case_price < strike_price_put:
    # CORRECTED: Put is ITM → you're forced to buy at put strike, which limits your futures gain
    # Short futures would normally gain: (entry_price - worst_case_price)
    # But short put loses: (strike_price_put - worst_case_price)
    # Net effect: (entry_price - strike_price_put)
    net_futures_put_pnl_per_ton = entry_price - strike_price_put
    hedged_loss_per_ton = net_futures_put_pnl_per_ton + net_option_premium_per_ton
    option_loss_put_per_ton = strike_price_put - worst_case_price
else:
    # Between strikes → no option payoff, only pay net premium
    futures_loss_per_ton = worst_case_price - entry_price
    hedged_loss_per_ton = futures_loss_per_ton + net_option_premium_per_ton

total_loss_hedged = hedged_loss_per_ton * total_tons

# Calculate effectiveness metrics
if worst_case_price > strike_price_call:
    option_intrinsic_value = worst_case_price - strike_price_call
    protection_effectiveness = option_intrinsic_value / loss_per_ton_unhedged if loss_per_ton_unhedged > 0 else 0
else:
    option_intrinsic_value = 0
    protection_effectiveness = 0

# ----------------------------
# Display Results
# ----------------------------

st.header(f"📉 Loss Exposure at ${worst_case_price:,.0f} Copper Price")

col1, col2, col3 = st.columns(3)
col1.metric("Short Exposure", f"{exposure_mt:,.0f} ton", f"{actual_lots_used:,.0f} lots")
col2.metric("Loss/Ton (No Hedge)", f"${loss_per_ton_unhedged:,.0f}", delta="Danger", delta_color="inverse")
col3.metric("P&L/Ton (With Collar)", f"${hedged_loss_per_ton:,.0f}", delta="Capped", delta_color="normal")

st.markdown("---")

col4, col5 = st.columns(2)
col4.metric("Total Loss (Unhedged)", f"${total_loss_unhedged:,.0f}", delta="Margin Call Risk", delta_color="inverse")
col5.metric("Net P&L (With Collar)", f"${total_loss_hedged:,.0f}", delta="Controlled", delta_color="off")

# Net cost of collar - FIXED CALCULATION
net_premium_cost_per_ton = net_option_premium_per_ton * total_tons
net_premium_cost_per_lot = net_option_premium_per_lot * actual_lots_used

st.info(f"""
💰 **Collar Strategy Cost & Benefit**
- Paid Premiums for Call: **\\${premium_call_per_lot * actual_lots_used:,.0f}** (\\${premium_call_per_ton:,.2f}/ton)
- Received Premiums from Put: **\\${premium_put_per_lot * actual_lots_used:,.0f}** (\\${premium_put_per_ton:,.2f}/ton)
- Net Option Premiums Flow: **\\${net_premium_cost_per_lot:,.0f}** (\\${net_option_premium_per_ton:,.2f}/ton)
- You save **\\${total_loss_unhedged - total_loss_hedged:,.0f}**.
- Total net P&L with collar: **\\${total_loss_hedged:,.0f}**
""")

# ----------------------------
# Visualization
# ----------------------------

fig = go.Figure(data=[
    go.Bar(
        name='Unhedged Loss',
        x=['Scenario'],
        y=[total_loss_unhedged],
        marker_color='firebrick',
        text=[f"${total_loss_unhedged:,.0f}"],
        textposition='auto'
    ),
    go.Bar(
        name='Net P&L (Collar)',
        x=['Scenario'],
        y=[total_loss_hedged],
        marker_color='mediumseagreen',
        text=[f"${total_loss_hedged:,.0f}"],
        textposition='auto'
    )
])
fig.update_layout(
    title="Total Portfolio Outcome: Collar vs Unhedged",
    yaxis_title="P&L (USD)",
    template="plotly_white",
    showlegend=True,
    height=400
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Margin Safety Check
# ----------------------------

st.header("⚠️ Margin Call Risk — CAPITAL AFTER COLLAR")

unhedged_remaining = max_capital - total_loss_unhedged
hedged_remaining = max_capital - total_loss_hedged

col6, col7 = st.columns(2)

with col6:
    st.markdown(f"**Breakdown of Strategy 1**: Unhedged Short Futures Position")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    st.markdown(f"- Minus Short Futures Loss: **${total_loss_unhedged:,.0f}**")
    st.markdown(f"→ Remaining Capital: **${unhedged_remaining:,.0f}**")
    
    if unhedged_remaining < 0:
        st.error(f"🚨 WITHOUT HEDGE: Margin call! You're short ${abs(unhedged_remaining):,.0f}")
    else:
        st.success(f"WITHOUT HEDGE: ${unhedged_remaining:,.0f} capital buffer remains")

with col7:
    st.markdown(f"**Breakdown of Strategy 2**: Short Futures + Collar (Call + Put)")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    
    if worst_case_price > strike_price_call:
        st.markdown(f"- Short Futures Loss: **${(worst_case_price - entry_price) * total_tons:,.0f}**")
        st.markdown(f"+ Call Option Gain: **${option_gain_call_per_ton * total_tons:,.0f}**")
    elif worst_case_price < strike_price_put:
        st.markdown(f"- Short Futures Gain: **${(entry_price - worst_case_price) * total_tons:,.0f}**")
        st.markdown(f"- Put Option Loss: **${option_loss_put_per_ton * total_tons:,.0f}**")
    else:
        st.markdown(f"- Short Futures Loss: **${(worst_case_price - entry_price) * total_tons:,.0f}**")
    
    st.markdown(f"+ Net Option Premium Flow: **${net_premium_cost_per_lot:,.0f}**")
    st.markdown(f"→ Remaining Capital: **${hedged_remaining:,.0f}**")
    
    if hedged_remaining < 0:
        st.error(f"🚨 WITH COLLAR: Still a shortfall of ${abs(hedged_remaining):,.0f}")
    else:
        st.success(f"WITH COLLAR: ${hedged_remaining:,.0f} capital buffer remains")

# ----------------------------
# Collar Effectiveness Analysis
# ----------------------------

st.header("📊 Collar Effectiveness")

if worst_case_price > strike_price_call:
    st.success(f"""
    🛡️ **Call is In-The-Money (ITM)**
    - Strike: **\\${strike_price_call:,.0f}** vs Market: **\\${worst_case_price:,.0f}**
    - Intrinsic Value: **\\${option_gain_call_per_ton:,.0f}/ton**
    """)
else:
    st.info(f"🟢 **Call is Out-of-the-Money (OTM)** — No payoff.")

if worst_case_price < strike_price_put:
    st.success(f"""
    🔒 **Put is In-The-Money (ITM)**
    - Strike: **\\${strike_price_put:,.0f}** vs Market: **\\${worst_case_price:,.0f}**
    - You must buy at **\\${strike_price_put:,.0f}**, limiting futures gain
    """)
else:
    st.info(f"🟢 **Put is Out-of-the-Money (OTM)** — No obligation.")

st.caption(f"🎯 Protection Range: **{strike_price_put:,.0f}** to **{strike_price_call:,.0f} USD/ton**")

# ----------------------------
# Recommendation
# ----------------------------

st.header("🎯 Strategic Recommendation")

if total_loss_hedged < total_loss_unhedged and hedged_remaining > 0:
    st.success(f"""
    ✅ **Strong Buy: Collar Is Effective**
    - Improves your outcome by **\\${total_loss_unhedged - total_loss_hedged:,.0f}** vs unhedged.
    - Net option flow: **${net_premium_cost_per_lot:,.0f}**.
    """)
elif total_loss_hedged < total_loss_unhedged:
    st.warning(f"""
    ⚠️ **Hedge Helps But Capital Is Tight**
    - You avoid catastrophic moves, but net premium doesn't fully cover losses.
    → Try: Adjust strikes, reduce size, or increase put premium.
    """)
else:
    st.error("❌ Current collar does not improve outcome — adjust strikes or premiums.")

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