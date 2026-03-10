export const mockKPIs = [
    {
        id: "revenue",
        title: "Revenue",
        value: 845000,
        prefix: "$",
        suffix: "",
        delta: "+14.2%",
        isPositive: true,
    },
    {
        id: "users",
        title: "Active Users",
        value: 124500,
        prefix: "",
        suffix: "",
        delta: "+8.4%",
        isPositive: true,
    },
    {
        id: "growth",
        title: "Growth Rate",
        value: 24,
        prefix: "",
        suffix: "%",
        delta: "-2.1%",
        isPositive: false,
    },
    {
        id: "conversion",
        title: "Conversion",
        value: 4.8,
        prefix: "",
        suffix: "%",
        delta: "+1.2%",
        isPositive: true,
    },
];

export const mockInsights = [
    {
        id: "insight-1",
        type: "anomaly",
        title: "Mobile Sales Dropped 42%",
        narrative: "A sharp decline occurred after the April UI update.",
        chartData: [
            { name: "Jan", uv: 4000, pv: 2400 },
            { name: "Feb", uv: 3000, pv: 1398 },
            { name: "Mar", uv: 2000, pv: 9800 },
            { name: "Apr", uv: 2780, pv: 3908 },
        ],
    },
    {
        id: "insight-2",
        type: "trend",
        title: "User Signups Surged in Week 12",
        narrative: "Marketing campaign increased conversions by 18%.",
        chartData: [
            { name: "Wk10", active: 2000 },
            { name: "Wk11", active: 2200 },
            { name: "Wk12", active: 3800 },
            { name: "Wk13", active: 4000 },
        ],
    },
    {
        id: "insight-3",
        type: "segment",
        title: "High Churn in Enterprise Tier",
        narrative: "Large accounts are churning 2.4x faster than SMBs.",
        chartData: [
            { name: "Q1", churn: 2.3 },
            { name: "Q2", churn: 3.1 },
            { name: "Q3", churn: 5.8 },
            { name: "Q4", churn: 6.2 },
        ],
    }
];

export const mockChatResponse = "Based on the latest data model analysis, the revenue anomaly in April was primarily driven by a 42% drop in mobile conversions following the UI update. Suggest reverting the checkout flow for mobile users to stabilize baseline KPIs.";
