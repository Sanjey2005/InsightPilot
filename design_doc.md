# Frontend Design Document: InsightPilot (3D Immersive Analytics Copilot)

## 1. Project Overview

InsightPilot is an AI-powered multi-agent data analytics copilot. This frontend blends a highly interactive, 3D experiential UI (inspired by creative developer portfolios) with a functional SaaS analytics dashboard. It features a continuous WebGL background, GSAP scroll/reveal animations, glassmorphic UI elements, and interactive data visualizations.

## 2. Tech Stack & Strict Dependencies

- **Framework:** Next.js 14+ (App Router) with TypeScript
- **Styling:** Tailwind CSS (utility-first, dark mode default)
- **3D Engine:** `three`, `@react-three/fiber` (R3F), `@react-three/drei`
- **Animation Engine:** `gsap`, `@gsap/react`
- **Data Visualization:** `recharts` (or `plotly.js` via `react-plotly.js`)
- **UI Components:** `lucide-react` (icons), `clsx`, `tailwind-merge`

### Crucial Rule

All files using GSAP, Three.js, or Recharts must start with:

```typescript
"use client";
```

because they rely on browser APIs.

## 3. Global Styling & Theming

### Vibe
Cinematic, futuristic, dark-mode data lab.

### Background
`#000000` → `#0a0a0a`

### UI Overlay (Glassmorphism)
Cards and panels use:

```css
bg-white/5 backdrop-blur-lg border border-white/10
```

### Accent Colors
- **Neon Cyan:** `#06b6d4`
- **Purple:** `#a855f7`

These represent AI activity and analytics highlights.

### Typography
- **Space Grotesk** → Headings & numbers (modern, geometric)
- **Inter** → Body text and chat logs

### Layout Structure

A fixed `<canvas>` element sits at:
```css
z-index: 0
```
and fills the entire screen.

The HTML Next.js layout sits at:
```css
z-index: 10
```
with a transparent background so the 3D scene shows through.

## 4. Directory Architecture

```text
src/
├── app/
│   ├── layout.tsx            # Global setup, fonts, and fixed 3D Canvas
│   ├── page.tsx              # Main orchestrator page (Upload -> Process -> Dashboard)
│   └── globals.css           # Tailwind directives
│
├── components/
│   ├── 3d/
│   │   ├── DataScene.tsx     # R3F: Swirling particles representing data points
│   │   └── CameraRig.tsx     # R3F: Moves camera based on mouse and scroll
│   │
│   ├── ui/
│   │   ├── GlassCard.tsx     # Reusable glassmorphic container
│   │   └── AgentStepper.tsx  # Animated status of the 5 LangGraph agents
│   │
│   ├── dashboard/
│   │   ├── StoryCard.tsx     # Narrative + Recharts visualization
│   │   └── KPIBar.tsx        # Top-level metrics with GSAP counter animations
│   │
│   └── chat/
│       └── CopilotChat.tsx   # Floating natural language query interface
│
├── lib/
│   ├── utils.ts              # cn() utility
│   └── mockData.ts           # Mock payload from the backend multi-agent system
```

## 5. UI/UX Flow & Section Specifications

### Phase 1: The Immersive Dropzone (Hero / Upload)

#### Visuals
The 3D background shows idle, slowly floating particles.

#### UI
Dead center of the screen is a massive glowing glassmorphic dropzone.

**Typography:**
> Upload Dataset.  
> Awaken InsightPilot.

#### Interaction
- **Drag Over:** Particles accelerate and swarm toward the center.
- **File Drop:** GSAP fades out the upload UI and transitions to Phase 2.

### Phase 2: Agent Orchestration (The "Thinking" State)

#### Visuals
3D particles align into a structured grid / neural network lattice.

#### UI
A sleek vertical stepper appears.

**Component:** `AgentStepper.tsx`

#### Animation
GSAP highlights the 5 agents sequentially:
1. **Schema Discovery Agent:** Inferring schema & detecting KPIs...
2. **SQL Generation Agent:** Structuring queries...
3. **Insight Discovery Agent:** Hunting for anomalies and trends...
4. **Visualization Agent:** Plotting charts...
5. **Supervisor Agent:** Compiling narrative...

### Phase 3: The Insight Dashboard (Results)

#### Layout

##### Top Section
**Pinned KPIBar**
Shows high-level metrics:
- Revenue
- Users
- Growth
- Conversion

Numbers animate `0 → value` using GSAP counters.

##### Main Content (Left / Center 70%)
Scrollable column or masonry layout of:
- `StoryCard` components

##### Sidebar / Floating (Right 30%)
`CopilotChat` interface.
Used for continuous natural language analytics queries.

#### StoryCards
`components/dashboard/StoryCard.tsx`

Each card represents an anomaly or trend.

**Example:**
> Sales dropped 42% on Mobile

Each card contains:
- A Recharts / Plotly graph
- A narrative explanation
- Highlighted anomaly

**Animation**
Using GSAP ScrollTrigger:
```javascript
{
  y: 50,
  opacity: 0 // fades to 1
}
```
Cards gently float upward and fade in while scrolling.

#### CopilotChat
`components/chat/CopilotChat.tsx`

A sleek floating chat interface.
Users ask natural language questions such as:
- *Why did sales drop in Q3?*
- *Show me top products in March.*
- *Which segment has the highest churn?*

**Message Animation**
Messages appear using:
- Typewriter effect
- or smooth fade-in

## 6. Implementation Rules for AI (Crucial)

### Next.js & Browser APIs
Any component importing:
- `gsap`
- `three`
- `@react-three/fiber`
- `recharts`

must include:
```typescript
"use client";
```

### GSAP in React
Never use raw `useEffect` for GSAP animations.
Always use `@gsap/react` and the `useGSAP()` hook to avoid React Strict Mode memory leaks.

### Canvas Segregation
The 3D `<Canvas>` must remain at root level.

**Recommended location:** `layout.tsx` or a high-level wrapper.

This prevents massive WebGL re-renders when UI state changes (chat typing, dashboard updates).

State like:
- `isProcessing`
- `isDashboard`

should be shared via **Zustand** or **React Context**.

### Mock the Backend First

Before connecting the real Python / LangGraph backend, create:
`mockData.ts`

It should export sample JSON insights such as:

```typescript
export const mockInsights = [
  {
    title: "Mobile Sales Dropped 42%",
    narrative: "A sharp decline occurred after the April UI update.",
    chartData: [...] // placeholder array
  },
  {
    title: "User Signups Surged in Week 12",
    narrative: "Marketing campaign increased conversions by 18%.",
    chartData: [...] // placeholder array
  }
];
```