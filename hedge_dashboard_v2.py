import streamlit as st
import plotly.graph_objects as go

# ----------------------------
# Dashboard Title & Description
# ----------------------------
st.set_page_config(page_title="Copper Short Hedge Dashboard", layout="wide")
st.title("Margin Call Risk Manager for Copper Futures Shorts")

# ----------------------------
# Sidebar Inputs
# ----------------------------
st.sidebar.header("📊 Input Parameters")

cost_per_lot = st.sidebar.number_input("Cost per Future Lot (USD)", value=20000.0, step=1000.0)
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

# Optional: Physical price for context only
physical_price = st.sidebar.number_input("Physical Copper Price (Reference Only, USD/ton)", value=9500.0, step=10.0)
st.sidebar.caption("💡 Physical price doesn't affect futures margin — shown for context only.")

# Option parameters
st.sidebar.subheader("Protective Call Option (to hedge short futures)")
strike_price = st.sidebar.number_input("Call Option Strike Price (USD/ton)", value=10500.0, step=50.0)
option_premium_per_ton = st.sidebar.number_input("Option Premium (USD/ton)", value=200.0, step=10.0)

# Add strike price validation
if strike_price < entry_price:
    st.sidebar.warning("⚠️ Strike price below entry — hedge only protects above strike, not from entry to strike!")

# ----------------------------
# Calculations
# ----------------------------

total_tons = exposure_mt
capital_used = actual_lots_used * cost_per_lot

# Unhedged loss
loss_per_ton_unhedged = worst_case_price - entry_price  # e.g., 11550 - 10130 = 1420
total_loss_unhedged = loss_per_ton_unhedged * total_tons

# FIXED: Hedged loss with call option - proper calculation
if worst_case_price > strike_price:
    # Option provides protection: gain = (market_price - strike_price)
    option_gain_per_ton = worst_case_price - strike_price
    futures_loss_per_ton = worst_case_price - entry_price
    hedged_loss_per_ton = futures_loss_per_ton - option_gain_per_ton + option_premium_per_ton
else:
    # Option expires worthless, only premium paid
    hedged_loss_per_ton = (worst_case_price - entry_price) + option_premium_per_ton

total_loss_hedged = hedged_loss_per_ton * total_tons
total_option_cost = option_premium_per_ton * total_tons

# Calculate option intrinsic value and effectiveness
if worst_case_price > strike_price:
    option_intrinsic_value = worst_case_price - strike_price
    protection_effectiveness = option_intrinsic_value / loss_per_ton_unhedged
else:
    option_intrinsic_value = 0
    protection_effectiveness = 0

# Calculate effective max loss price
effective_max_loss_price = entry_price + hedged_loss_per_ton

# ----------------------------
# Display Results
# ----------------------------

st.header(f"📉 Loss Exposure at ${worst_case_price:,.0f} Copper Price")

col1, col2, col3 = st.columns(3)
col1.metric("Short Exposure", f"{exposure_mt:,.0f} MT", f"{actual_lots_used:,.0f} lots")
col2.metric("Loss/Ton (No Hedge)", f"${loss_per_ton_unhedged:,.0f}", delta="Danger", delta_color="inverse")
col3.metric("Loss/Ton (With Hedge)", f"${hedged_loss_per_ton:,.0f}", delta="Protected", delta_color="normal")
col3.metric("Effective Max Loss Price", f"${effective_max_loss_price:,.0f}/ton", delta="Capped", delta_color="normal")

st.markdown("---")

col4, col5 = st.columns(2)
col4.metric("Total Loss (Unhedged)", f"${total_loss_unhedged:,.0f}", delta="Margin Call Risk", delta_color="inverse")
col5.metric("Total Loss (Hedged)", f"${total_loss_hedged:,.0f}", delta="Controlled", delta_color="off")

st.info(f"""
💰 **Hedging Cost & Benefit**
- You pay **${total_option_cost:,.0f}** in option premiums.
- Option intrinsic value at **\\${worst_case_price:,.0f}**: **\\${option_intrinsic_value:,.0f}/ton**
- Your loss is reduced by **\\${total_loss_unhedged - total_loss_hedged:,.0f}**.
- Total cash outflow with hedge: **\\${total_loss_hedged:,.0f}** (includes premium)
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
        name='Hedged Loss',
        x=['Scenario'],
        y=[total_loss_hedged],
        marker_color='mediumseagreen',
        text=[f"${total_loss_hedged:,.0f}"],
        textposition='auto'
    )
])
fig.update_layout(
    title="Total Portfolio Loss: Hedged vs Unhedged",
    yaxis_title="Loss (USD)",
    template="plotly_white",
    showlegend=True,
    height=400
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Margin Safety Check — FIXED (No double counting)
# ----------------------------

st.header("⚠️ Margin Call Risk — CAPITAL AFTER HEDGE")

# FIXED: hedged_remaining no longer double-counts option premium
unhedged_remaining = max_capital - total_loss_unhedged
hedged_remaining = max_capital - total_loss_hedged  # total_loss_hedged already includes option cost

col6, col7 = st.columns(2)

with col6:
    st.markdown(f"**Breakdown with No Options Hedge:**")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    st.markdown(f"- Minus Unhedged Loss: **${total_loss_unhedged:,.0f}**")
    st.markdown(f"→ Remaining Capital: **${unhedged_remaining:,.0f}**")
    
    if unhedged_remaining < 0:
        st.error(f"🚨 WITHOUT HEDGE: Margin call! You're short ${abs(unhedged_remaining):,.0f}")
    else:
        st.success(f"✅ WITHOUT HEDGE: ${unhedged_remaining:,.0f} buffer remains — SAFE from margin call")

with col7:
    st.markdown(f"**Breakdown with Options Hedge:**")
    st.markdown(f"- Initial Capital: **${max_capital:,.0f}**")
    st.markdown(f"- Total Loss (Futures + Options): **${total_loss_hedged:,.0f}**")
    st.markdown(f"→ Remaining Capital: **${hedged_remaining:,.0f}**")
    
    if hedged_remaining < 0:
        st.error(f"🚨 WITH HEDGE: Still a shortfall of ${abs(hedged_remaining):,.0f} — reduce size or adjust strike")
    else:
        st.success(f"✅ WITH HEDGE: ${hedged_remaining:,.0f} capital buffer remains — SAFE from margin call")

# ----------------------------
# Option Effectiveness Analysis
# ----------------------------

st.header("📊 Option Effectiveness")

if worst_case_price > strike_price:
    st.success(f"""
    🛡️ **Option is In-The-Money (ITM)**
    - Strike: **\\${strike_price:,.0f}** vs Market: **\\${worst_case_price:,.0f}**
    - Intrinsic Value: **\\${option_intrinsic_value:,.0f}/ton**
    - Protection Coverage: {protection_effectiveness:.1%} of potential loss
    """)
else:
    st.warning(f"""
    ⚠️ **Option is Out-The-Money (OTM)**
    - Strike: **\\${strike_price:,.0f}** vs Market: **\\${worst_case_price:,.0f}**
    - Provides no intrinsic value protection
    - Only protects against catastrophic moves above strike price
    """)

# ----------------------------
# Recommendation
# ----------------------------

st.header("🎯 Strategic Recommendation")

if total_loss_hedged < total_loss_unhedged and hedged_remaining > 0:
    st.success(f"""
    ✅ **Strong Buy: Call Options Are Worth It**
    - Caps your max loss at **\\${hedged_loss_per_ton:,.0f}/ton** instead of **\\${loss_per_ton_unhedged:,.0f}/ton**.
    - Prevents broker from forcing liquidation.
    - Cost of insurance **(\\${total_option_cost:,.0f})** is small vs loss avoided **(\\${total_loss_unhedged - total_loss_hedged:,.0f})**.
    """)
elif total_loss_hedged < total_loss_unhedged:
    st.warning(f"""
    ⚠️ **Hedge Helps But Capital Is Tight**
    - You avoid catastrophic loss, but option cost pushes you near/below zero capital.
    → Try: Higher strike price, reduce position size, or both.
    """)
else:
    st.error("❌ Current option parameters do not help — adjust strike or premium.")

# ----------------------------
# Footer Note
# ----------------------------

# Footer
st.markdown("---")
# LinkedIN
st.markdown("### Connect with Me!")

st.markdown("""
<a href="https://www.linkedin.com/in/saqif-juhaimee-17322a119/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20">
    Saqif Juhaimee
</a>
""", unsafe_allow_html=True)