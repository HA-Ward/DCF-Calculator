import streamlit as st
import pandas as pd
import altair as alt
import yfinance as yf

defaults = {
    "revenue": 100_000_000,
    "ebitda": 30_000_000,
    "operating_income": 20_000_000,
    "capex": 5_000_000,
    "nwc1": 15_000_000,
    "nwc0": 14_000_000
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def safe_int(value, default):
    try:
        return int(value) if value is not None else default
    except:
        return default

def update_inputs(data):
    st.session_state["revenue"] = safe_int(data.get("totalRevenue"), 100_000_000)
    st.session_state["ebitda"] = safe_int(data.get("ebitda"), 30_000_000)
    st.session_state["operating_income"] = safe_int(data.get("ebit"), 20_000_000)
    st.session_state["capex"] = safe_int(data.get("capex"), 5_000_000)
    st.session_state["nwc1"] = safe_int(data.get("nwc1"), 15_000_000)
    st.session_state["nwc0"] = safe_int(data.get("nwc0"), 14_000_000)

st.title("DCF Valuation Calculator")

    
st.sidebar.header("Ticker Symbol")

with st.sidebar.form("ticker_form"):
    ticker = st.text_input("Enter Ticker Symbol", value="")
    submitted = st.form_submit_button("Fetch Data")

if submitted and ticker:
    stock = yf.Ticker(ticker)
    financials = stock.financials
    cashflow = stock.cashflow
    balancesheet = stock.balancesheet

    try:
        data = {
            "totalRevenue": financials.loc["Total Revenue"].iloc[0],
            "ebitda": financials.loc["EBITDA"].iloc[0],
            "ebit": financials.loc["EBIT"].iloc[0],
            "capex": cashflow.loc["Capital Expenditure"].iloc[0],
            "nwc1": balancesheet.loc["Working Capital"].iloc[0],
            "nwc0": balancesheet.loc["Working Capital"].iloc[1]
        }
        update_inputs(data)
        st.success(f"Loaded data for {ticker.upper()}")
    except Exception as e:
        st.error(f"Error loading data: {e}")


st.sidebar.header("Input Parameter")
revenue = st.sidebar.number_input("Revenue (TTM) ($)", key="revenue", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['revenue']:,.0f}")
if revenue == 0:
    st.error("Revenue is 0. Please enter a valid revenue manually or fetch data.")
    st.stop()
ebitda = st.sidebar.number_input("EBITDA ($)", key="ebitda", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['ebitda']:,.0f}")
operating_income = st.sidebar.number_input("Operating Income (EBIT) ($)", key="operating_income", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['operating_income']:,.0f}")
capex = st.sidebar.number_input("Capital Expenditure ($)", key="capex", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['capex']:,.0f}")
nwc1 = st.sidebar.number_input("Net Working Capital (current year) ($)", key="nwc1", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['nwc1']:,.0f}")
nwc0 = st.sidebar.number_input("Net Working Capital (previous year) ($)", key="nwc0", step=100_000)
st.sidebar.caption(f"Entered: ${st.session_state['nwc0']:,.0f}")

print(revenue)

growth_rate = st.sidebar.slider("Revenue Growth Rate (%)", 0, 50, 8)
tax_rate = st.sidebar.slider("Tax Rate (%)", 0, 100, 25)
discount_rate = st.sidebar.slider("WACC / Discount Rate (%)", 0, 20, 10)
forecast_years = st.sidebar.slider("Forecast Period (Years)", 1, 10, 5)
terminal_growth_rate = st.sidebar.slider("Terminal Growth Rate (%)", min_value=0.0, max_value=5.0, value=2.0, step= 0.5)
denominator = discount_rate/100 - terminal_growth_rate/100
if denominator == 0:
    st.error("Discount Rate must be greater than Terminal Growth Rate to calculate terminal value.")
    st.stop()

da = ebitda - operating_income
change_nwc = nwc1 - nwc0
revenues = [revenue * ((1 + growth_rate/100)**year) for year in range(1,forecast_years + 1)]
scaling_factors = [rev/revenue for rev in revenues]
ebits = [operating_income * factor for factor in scaling_factors]
das = [da * factor for factor in scaling_factors]
capexs = [capex * factor for factor in scaling_factors]
change_nwcs = [change_nwc * factor for factor in scaling_factors]

fcfs = [ebits[i]*(1-tax_rate/100) + das[i] - capexs[i] - change_nwcs[i] for i in range(0, forecast_years)]
print(fcfs)
terminal_value = fcfs[forecast_years - 1] * (1 + terminal_growth_rate/100)/(discount_rate/100 - terminal_growth_rate/100)

discounted_fcfs = [fcfs[i-1]/(1+discount_rate/100)**i for i in range(1, forecast_years + 1)]
discounted_terminal_value = terminal_value / (1 + discount_rate/100)**forecast_years
Enterprise_value = sum(discounted_fcfs) + discounted_terminal_value

years = [i for i in range(1, forecast_years + 1)]
print(years)
print(revenues)
print(ebits)
print(das)
df = pd.DataFrame({
    "Year": years,
    "Revenue Forecast ($)": revenues,
    "EBIT Forecast ($)": ebits,
    "D&A ($)": das,
    "CapEx ($)": capexs,
    "Change in NWC ($)": change_nwcs,
    "FCF ($)": fcfs,
    "Discounted FCF ($)": discounted_fcfs
})

st.subheader("Forecast and Discounted Cash Flows")
st.dataframe(df.style.format({
    "Revenue Forecast ($)": "${:,.2f}",
    "EBIT Forecast ($)": "${:,.2f}",
    "D&A ($)": "${:,.2f}",
    "CapEx ($)": "${:,.2f}",
    "Change in NWC ($)": "${:,.2f}",
    "FCF ($)": "${:,.2f}",
    "Discounted FCF ($)": "${:,.2f}"
}))

st.subheader("Revenue and Free Cash Flow Over Time")

plot_data = df[["Year", "Revenue Forecast ($)", "FCF ($)"]].melt(id_vars="Year")
chart = alt.Chart(plot_data).mark_line(point=True).encode(
    x=alt.X("Year:O", axis=alt.Axis(labelAngle=0)),
    y=alt.Y("value:Q", title="Amount($)"),
    color="variable:N",
    tooltip=["Year","variable","value"]
).interactive()

st.altair_chart(chart, use_container_width=True)

st.subheader("Terminal Value")
st.metric(label="Terminal Value ($)", value=f"{terminal_value:,.2f}")

st.subheader("Estimated Company Valuation (DCF)")
st.metric(label="Enterprise Value ($)", value=f"{Enterprise_value:,.2f}")