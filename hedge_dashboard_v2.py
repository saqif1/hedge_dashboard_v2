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
cost_per_lot = st.sidebar.number_input("Initial Margin (USD/lot)", value=4000.0, step=1000.0)
lot_size_ton = st.sidebar.number_input("Lot Size (Tons)", value=25.0, step=1.0)
max_capital = st.sidebar.number_input("Max Capital for Futures (USD)", value=5840000.0, step=100000.0)

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

cost_per_lot = st.sidebar.number_input("Initial Margin (USD/lot)", value=4000.0, step=1000.0)

# Calculate maximum possible MT based on capital
max_mt = int((max_capital / cost_per_lot) * lot_size_ton)

exposure_mt = st.sidebar.number_input(
    "Futures Exposure (Metric Tons)",
    min_value=25,  # Minimum 1 lot
    max_value=max_mt,
    value=min(2800, max_mt),
    step=25,
    help=f"Maximum possible based on capital: {max_mt:,} ton"
)

# Calculate lots from MT exposure
actual_lots_used = exposure_mt / lot_size_ton

entry_price = st.sidebar.number_input("Futures Entry Price (USD/ton)", value=2026.0, step=10.0)
worst_case_price = st.sidebar.number_input("Scenario Analysis Price (USD/ton)", value=2310.0, step=10.0)

# ----------------------------
# OPTIONS STRATEGY CONFIGURATION
# ----------------------------
st.sidebar.header("Options Strategy Configuration")

options_config = []
for i in range(1, 3):
    st.sidebar.subheader(f"Option {i}")
    opt_type = st.sidebar.selectbox(
        f"Option {i} Type",
        ["Call", "Put"],
        key=f"opt_type_{i}"
    )
    position = st.sidebar.radio(
        f"Option {i} Position",
        ["None", "Long", "Short"],
        index=0,
        key=f"opt_pos_{i}"
    )
    if position != "None":
        strike = st.sidebar.number_input(f"Option {i} Strike Price (USD/ton)", value=10000.0, step=50.0, key=f"strike_{i}")
        premium_per_lot = st.sidebar.number_input(f"Option {i} Premium (USD/lot)", value=1000.0, step=10.0, key=f"prem_{i}")
        premium_per_ton = premium_per_lot / lot_size_ton
    else:
        strike = 0
        premium_per_lot = 0
        premium_per_ton = 0

    options_config.append({
        "type": opt_type.lower(),  # 'call' or 'put'
        "position": position.lower(),  # 'long'/'short'/'none'
        "strike": strike,
        "premium_per_lot": premium_per_lot,
        "premium_per_ton": premium_per_ton
    })

# ----------------------------
# CALCULATE BUTTON
# ----------------------------
st.sidebar.markdown("---")
calculate_pressed = st.sidebar.button("🧮 Calculate P&L", use_container_width=True)

# ----------------------------
# DYNAMIC STRATEGY CALCULATIONS & DISPLAY
# ----------------------------
if calculate_pressed:

    total_tons = exposure_mt

    def calculate_option_payoff(price, strike, option_type, position_type):
        if strike == 0 or position_type == "none":
            return 0
        if option_type == "call":
            intrinsic = max(price - strike, 0)
        else:
            intrinsic = max(strike - price, 0)
        return intrinsic if position_type == "long" else -intrinsic

    def calculate_premium_flow(position_type, premium_per_ton):
        if position_type == "long":
            return -premium_per_ton
        elif position_type == "short":
            return premium_per_ton
        return 0

    # Futures P&L per ton
    if futures_position == "Short":
        futures_pnl_per_ton = entry_price - worst_case_price
    else:
        futures_pnl_per_ton = worst_case_price - entry_price

    # Options calculations
    option_payoffs_per_ton = []
    option_prem_flows_per_ton = []

    for opt in options_config:
        payoff = calculate_option_payoff(worst_case_price, opt["strike"], opt["type"], opt["position"])
        prem_flow = calculate_premium_flow(opt["position"], opt["premium_per_ton"])
        option_payoffs_per_ton.append(payoff)
        option_prem_flows_per_ton.append(prem_flow)

    total_option_payoff_per_ton = sum(option_payoffs_per_ton)
    total_premium_flow_per_ton = sum(option_prem_flows_per_ton)

    strategy_pnl_per_ton = futures_pnl_per_ton + total_option_payoff_per_ton + total_premium_flow_per_ton

    # Convert to totals
    total_futures_pnl = futures_pnl_per_ton * total_tons
    total_option_payoff = total_option_payoff_per_ton * total_tons
    total_premium_flow = total_premium_flow_per_ton * total_tons
    total_strategy_pnl = strategy_pnl_per_ton * total_tons

    # Check if both options are inactive
    both_options_none = all(opt["position"] == "none" for opt in options_config)

    # Calculate Initial Margin Used
    initial_margin_used = actual_lots_used * cost_per_lot

    # Display results
    st.header(f"📊 Strategy Analysis at ${worst_case_price:,.0f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Futures Exposure", f"{exposure_mt:,.0f} ton", f"{actual_lots_used:,.0f} lots")
    # Show position with color-coded label and entry price as help text
    if futures_position == "Long":
        col1.metric(
            "Futures Position",
            "🟢 Long",
            help=f"Entry Price: ${entry_price:,.0f}"
        )
    else:  # Short
        col1.metric(
            "Futures Position",
            "🔴 Short",
            help=f"Entry Price: ${entry_price:,.0f}"
        )

    unhedged_color = "inverse" if futures_pnl_per_ton < 0 else "normal"

    col2.metric("P&L/Ton (Futures Only)", f"${futures_pnl_per_ton:,.0f}", delta_color=unhedged_color)

    # Show "-" if no options are active
    if both_options_none:
        col3.metric("P&L/Ton (With Options)", "-")
    else:
        hedged_color = "inverse" if strategy_pnl_per_ton < 0 else "normal"
        col3.metric("P&L/Ton (With Options)", f"${strategy_pnl_per_ton:,.0f}", delta_color=hedged_color)

    st.markdown("---")

    col4, col5 = st.columns(2)
    col4.metric("Total P&L (Futures Only)", f"${total_futures_pnl:,.0f}")

    if both_options_none:
        col5.metric("Total P&L (With Options)", "-")
    else:
        col5.metric("Total P&L (With Options)", f"${total_strategy_pnl:,.0f}")

    # Premium breakdown — only show if at least one option is active
    if not both_options_none:
        premium_info = "💰 **Options Premium Cash Flow**\n"
        for idx, opt in enumerate(options_config, start=1):
            if opt["position"] != "none":
                direction = "Paid" if opt["position"] == "long" else "Received"
                premium_info += f"- Option {idx} ({opt['type'].capitalize()}): {direction} **\\${opt['premium_per_lot'] * actual_lots_used:,.0f}** (\\${opt['premium_per_ton']:,.2f}/ton)\n"

        net_direction = "Net Outflow" if total_premium_flow < 0 else "Net Inflow"
        premium_info += f"- {net_direction}: **\\${abs(total_premium_flow):,.0f}** (\\${abs(total_premium_flow_per_ton):,.2f}/ton)\n"

        st.info(premium_info)

        # Also show Option Intrinsic P&L if non-zero
        if total_option_payoff != 0:
            intrinsic_direction = "Loss" if total_option_payoff < 0 else "Gain"
            st.info(f"📌 **Option Intrinsic P&L**: {intrinsic_direction} of **\\${abs(total_option_payoff):,.0f}** (\\${total_option_payoff_per_ton:,.2f}/ton)")

    # ==============================
    # SIDE-BY-SIDE WATERFALL CHARTS — WITH INITIAL MARGIN + OPTION PAYOFF
    # ==============================
    col_chart1, col_chart2 = st.columns(2)

    # ==============================
    # CHART 1: UNHEDGED (FUTURES ONLY) — WITH MARGIN
    # ==============================
    with col_chart1:
        measure_unhedged = ["absolute", "relative", "relative", "total"]
        x_unhedged = [
            "Starting Capital",
            "Initial Margin (Blocked)",
            "Futures P&L",
            "Net Liquid Capital (Unhedged)"
        ]
        y_unhedged = [
            max_capital,
            -initial_margin_used,
            total_futures_pnl,
            max_capital - initial_margin_used + total_futures_pnl
        ]

        fig_unhedged = go.Figure(go.Waterfall(
            name="Unhedged Strategy",
            orientation="v",
            measure=measure_unhedged,
            x=x_unhedged,
            y=y_unhedged,
            textposition="outside",
            text=[f"${val:,.0f}" for val in y_unhedged],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "lightgreen"}},
            decreasing={"marker": {"color": "salmon"}},
            totals={"marker": {"color": "steelblue"}}
        ))

        fig_unhedged.update_layout(
            title="📉 Strategy 1: Unhedged (Futures Only)",
            yaxis_title="USD",
            template="plotly_white",
            height=550,
            showlegend=False
        )

        st.plotly_chart(fig_unhedged, use_container_width=True)

        # # Risk warning under chart
        # final_unhedged = max_capital - initial_margin_used + total_futures_pnl
        # if final_unhedged < 0:
        #     st.error("🚨 **Margin Call Risk (Unhedged)**: Final liquid capital is negative.")

    # ==============================
    # CHART 2: HEDGED (FUTURES + OPTIONS) — WITH MARGIN + OPTION PAYOFF
    # ==============================
    with col_chart2:
        if both_options_none:
            st.warning("⚠️ No options selected. Hedged strategy is identical to unhedged.")
            st.markdown("### -")
        else:
            measure_hedged = ["absolute", "relative", "relative", "relative", "relative", "total"]
            x_hedged = [
                "Starting Capital",
                "Initial Margin (Blocked)",
                "Futures P&L",
                "Option Intrinsic P&L",
                "Options Premium Flow",
                "Net Liquid Capital (Hedged)"
            ]
            y_hedged = [
                max_capital,
                -initial_margin_used,
                total_futures_pnl,
                total_option_payoff,
                total_premium_flow,
                max_capital - initial_margin_used + total_futures_pnl + total_option_payoff + total_premium_flow
            ]

            fig_hedged = go.Figure(go.Waterfall(
                name="Hedged Strategy",
                orientation="v",
                measure=measure_hedged,
                x=x_hedged,
                y=y_hedged,
                textposition="outside",
                text=[f"${val:,.0f}" for val in y_hedged],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "mediumseagreen"}},
                decreasing={"marker": {"color": "firebrick"}},
                totals={"marker": {"color": "navy"}}
            ))

            fig_hedged.update_layout(
                title="📈 Strategy 2: Hedged with Options",
                yaxis_title="USD",
                template="plotly_white",
                height=600,
                showlegend=False
            )

            st.plotly_chart(fig_hedged, use_container_width=True)

            # # Risk warning under chart
            # final_hedged = max_capital - initial_margin_used + total_futures_pnl + total_option_payoff + total_premium_flow
            # if final_hedged < 0:
            #     st.error("🚨 **Margin Call Risk (Hedged)**: Final liquid capital is negative.")

    # ==============================
    # NET LIQUID CASH METRICS — UNDER GRAPHS
    # ==============================
    st.markdown("---")
    st.subheader("🏦 Net Liquid Cash Remaining After Scenario")

    col_net1, col_net2 = st.columns(2)

    final_unhedged = max_capital - initial_margin_used + total_futures_pnl

    with col_net1:
        st.metric(
            "Net Liquid Cash (Unhedged)",
            f"${final_unhedged:,.0f}",
            delta=None,
            delta_color="inverse" if final_unhedged < 0 else "normal"
        )
        # Risk warning under chart
        final_unhedged = max_capital - initial_margin_used + total_futures_pnl
        if final_unhedged < 0:
            st.error("🚨 **Margin Call Risk (Unhedged)**: Final liquid capital is negative.")

    with col_net2:
        if not both_options_none:
            final_hedged = max_capital - initial_margin_used + total_futures_pnl + total_option_payoff + total_premium_flow
            st.metric(
                "Net Liquid Cash (Hedged)",
                f"${final_hedged:,.0f}",
                delta=None,
                delta_color="inverse" if final_hedged < 0 else "normal"
            )
            # Risk warning under chart
            final_hedged = max_capital - initial_margin_used + total_futures_pnl + total_option_payoff + total_premium_flow
            if final_hedged < 0:
                st.error("🚨 **Margin Call Risk (Hedged)**: Final liquid capital is negative.")
        else:
            st.metric("Net Liquid Cash (Hedged)", "-")

else:
    st.info("👈 Configure your strategy in the sidebar, then click **🧮 Calculate P&L** to see the full analysis.")

st.markdown("---")
st.markdown("### Connect with Me!")

st.markdown("""
<a href="https://www.linkedin.com/in/saqif-juhaimee-17322a119/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="20">
    Saqif Juhaimee
</a>
""", unsafe_allow_html=True)