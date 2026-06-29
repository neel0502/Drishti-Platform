# Drishti — Design Brief
## Karnataka State Police · SCRB Intelligence Platform

---

## 1. Who Uses This Platform

Understanding the user is everything. This is NOT a developer tool.

### 🎖️ User 1 — DGP / IGP / Commissioner (Decision Maker)
- Age 50–62. Reads paper reports daily. Comfortable with phones, not dashboards.
- Opens the platform in a **review meeting** or on a **tablet**.
- Needs: "What is the state of crime in Karnataka right now?"
- Does NOT want: Sigma values, node graphs, API terminology, monospace IDs
- Asks questions like:
  - "Is Bangalore getting safer or worse?"
  - "Which districts need more deployment this month?"
  - "How many heinous crimes happened this week vs last year?"
- **Design for them:** Big numbers. Plain English. Red = bad, Green = good. One click to any answer.

### 🔍 User 2 — SCRB Intelligence Analyst (Power User)
- Age 30–45. Comfortable with computers. Does daily case analysis.
- Needs: Fast search, cross-case linking, suspect profiles, MO matching
- Asks questions like:
  - "Find all cases linked to this phone number"
  - "Show me every crime this person has been connected to"
  - "Which cases in Mysuru have the same MO as this burglary?"
- **Design for them:** Powerful search, filterable tables, network graphs, export to PDF

### 🏠 User 3 — SHO / Station Officer (Field User)
- Age 35–50. Uses it on a desktop at the station.
- Needs: What happened in MY area. My cases. My pending work.
- **Design for them:** Simple station-level view. Clean tables. No complexity.

---

## 2. Design Philosophy

### The Newspaper Test
Every screen must pass this test:
> "If a DGP looked at this for 5 seconds, could they tell if crime is going up or down in Karnataka?"

### Three Rules
1. **Words over symbols.** Write "Crime went up 34% this month" not "↑ 2.3σ". Write "3 High-Risk Districts" not "anomaly score > threshold".
2. **Colour means something specific.** Red = needs attention now. Amber = watch this. Green = normal. Blue = information. Never decorative.
3. **Every number answers a question.** Before placing any metric, write the question it answers. Can't write the question? Remove the number.

### Plain English Replacements
| Old (Too Techy) | New (Human) |
|---|---|
| "6.2σ above baseline" | "6× more than usual" |
| "Louvain community detection" | "Linked Crime Group" |
| "Node graph" | "Who knows who" map |
| "Anomaly score: 0.87" | "Unusual — needs review" |
| "CaseMasterID: 104430006" | "FIR #BLR/2024/00234" |
| "Spatiotemporal cluster" | "Crime Hotspot" |
| "MO similarity: 94.2%" | "Same method used in 14 cases" |
| "Risk score: 87/100" | "HIGH RISK OFFENDER" pill |

---

## 3. Extended Data Sources (Beyond FIR Schema)

This is what separates Drishti from a basic dashboard — full intelligence linking.

### 3.1 Identity Data
```
Aadhaar (masked — last 4 digits only)
  → Verify identity across cases with different names
  → Detect alias usage: same Aadhaar, different name registered

Voter ID / PAN
  → Cross-reference address history
  → Shell company links in economic offences

Driver's License
  → Vehicle ownership history
  → License suspension tracking
```

### 3.2 Family & Relative Network
```
Father's name, spouse name, known relatives (added by IO)

Intelligence value:
  → "Ramesh Naik's brother Suresh Naik — 3 prior NDPS cases"
  → "Accused's father owns property near crime location"
  → Family members as witnesses, co-conspirators, or shelters
```

### 3.3 Mobile Number Intelligence
```
Phone numbers from FIR records and arrest documents

Track:
  → Same number appearing in multiple FIRs across districts
  → Number registered under different names (SIM fraud indicator)
  → Number appearing in multiple accused profiles = gang link
  → Last known district from most recent arrest record

Pattern detection:
  → "This number appears in 8 FIRs across 4 districts"
  → "3 accused in the Burglary Syndicate all called the same
     number within 24 hours of each crime"
  → Phone clusters: which numbers call the same numbers = network map
```

### 3.4 Vehicle Intelligence
```
Vehicle registration numbers extracted from BriefFacts via NLP
Cross-referenced across all cases

Track:
  → Same vehicle in multiple cases
  → Vehicle ownership changes after a crime date
  → Known getaway vehicles
  → "Black Pulsar KA-05 MX 1234 linked to 6 chain snatching cases
     all in Indiranagar area between 6–9 PM"
```

### 3.5 Address & Location Intelligence
```
Permanent address from accused records
Last known address from most recent arrest
Crime GPS coordinates (already in schema)

Intelligence:
  → Accused operating far from home = organised travel crime
  → Multiple accused sharing same address = hideout or base
  → Multiple victims in same neighbourhood = targeted area
  → Map: show accused home vs crime locations — reveals operation radius
```

### 3.6 Court & Legal Intelligence
```
Court appearances (CourtID in schema)
Bail status + bail grant date
Parole records (post-release tracking)
Prior conviction history

Intelligence:
  → "Released on bail 3 months ago — 2 new FIRs since release"
  → "Out on parole — new crime in same category = violation"
  → Recidivism pattern: average time between release and next offence
  → Court pendency: cases stuck at court for >1 year flagged
```

### 3.7 Background Cross-Case Linking Engine
```
Automatically link cases that share ANY of:
  → Same accused name (fuzzy match handles aliases)
  → Same mobile number
  → Same vehicle registration
  → Same Aadhaar last-4
  → GPS within 500m + same crime type + same time window
  → Identical or near-identical BriefFacts (NLP similarity >85%)
  → Same extracted MO pattern

Result on every case detail page:
  "6 related cases found — possibly connected" badge
  Click to see all linked cases instantly
```

---

## 4. Navigation Structure

```
Home (Command Centre)
  │
  ├── Crime Map
  │     ├── District heatmap
  │     ├── Time of day slider (hotspots)
  │     └── Prediction overlay (next 7 days)
  │
  ├── Search & Investigate    ← PRIMARY ANALYST TOOL
  │     ├── Search by: person / phone / vehicle / case / Aadhaar
  │     └── Case detail page (with auto-linked cases)
  │
  ├── Intelligence Profiles
  │     ├── Repeat offenders list
  │     └── Individual profile page
  │
  ├── Crime Networks          ← "Who knows who"
  │     ├── Group/gang view
  │     └── Network graph
  │
  ├── Situations (Alerts)     ← NOT "Anomaly Feed"
  │
  └── Reports
```

---

## 5. Screen Specifications

---

### Screen 1 — Home / Command Centre

**Purpose:** DGP opens this in morning briefing. Answers "What happened? Where do I act today?"

**Top — Morning Brief Card**
```
Full width card, plain dark bg.
Large readable sentence (auto-generated):
"Karnataka recorded 847 crimes yesterday.
 Bangalore Urban and Raichur require immediate attention today."
Subtext: "Auto-generated · Updated 6:00 AM · 29 June 2026"
```

**KPI Row — 4 cards, plain labels**
```
1. Crimes This Month
   12,847  (36px bold)
   "↑ 340 more than last month" (red)
   Tiny 6-bar sparkline

2. Cases Solved
   7,203
   "56% resolution rate"
   "Better than last year (52%)" (green)

3. Arrests Made
   4,891
   "This month · 234 heinous crime arrests"

4. Districts Needing Attention
   3  (large)
   "Bangalore · Raichur · Kolar"
   "Action Required" red pill
```

**Middle — Two columns**
```
LEFT (55%): Karnataka Map
  Districts shaded cream → deep red by crime volume
  Hover shows plain card: "Mysuru · 847 crimes · ↑12% · Top: Theft"
  3 districts with soft pulsing red glow (alert districts)
  Label: "Crime Intensity Map — Click any district"

RIGHT (45%): "What Needs Attention"
  3 alert cards, left-bordered by colour:

  🔴 "Unusual spike in Raichur"
     "3 kidnappings in 2 days — 6× higher than normal"
     [Investigate →]

  🟡 "Repeat offender active — Bangalore"
     "Kiran Kumar linked to 14 burglaries, last seen Belagavi"
     [View Profile →]

  🟡 "Same break-in method — 3 districts"
     "5 burglaries likely by same group — same drill MO"
     [See Linked Cases →]
```

**Bottom — Crime Trend**
```
Full-width area chart, 24 months, plain labels
Blue line + gradient fill
Grey band over Oct–Nov: "Festive Season — Annual Spike"
No sigma, no baseline terminology
```

---

### Screen 2 — Crime Map

**Purpose:** "Show me where crime is happening and when"

**Top floating controls**
```
Plain dropdowns:
"Show me: [All Crimes ▾]  In: [All Karnataka ▾]  During: [Last 30 Days ▾]"
Toggle: Areas / Heatmap / Incidents
"3 Situations Need Attention" red badge
```

**Map**
```
Districts coloured white→red by density
On click: bottom sheet slides up —
  "Mysuru District"
  "847 crimes this month · ↑12% vs last month"
  "Most common: Vehicle Theft"
  [See All Cases] [See Offenders] [Close-up Map]
```

**Time of Day Slider (bottom)**
```
Label: "What time do crimes happen?"
Slider: 12 AM ──────●────── 11 PM
Current: "8 PM — Evening Peak"
Info text: "Most chain snatchings happen between 6 PM and 9 PM"
▶ Play to animate through 24 hours
```

**Alert Card (top right)**
```
"⚠️ Unusual Activity — Raichur"
"Kidnappings this week are much higher than normal.
 3 cases in 48 hours — average is 1 per month."
[Investigate]  [Dismiss]
```

---

### Screen 3 — Search & Investigate

**Purpose:** Analyst types anything and gets everything linked to it.

**Search Hero**
```
Large centred search bar:
"Search by name, phone number, vehicle number, case ID, Aadhaar..."
Quick chips: [Person] [Phone] [Vehicle] [Case ID] [Location]
```

**Result — Person ("Kiran Kumar")**
```
Large card:
  "Kiran Kumar"  24px bold
  "also known as: Drill Kiran, Kiran Naik"  muted
  Pills: "HIGH RISK OFFENDER" red | "Repeat Offender" amber
  "Age 34 · Male · Last seen: Belagavi, November 2024"
  Stats: 14 FIRs · 3 Districts · AT LARGE (red)
  "Known for: House Burglary (12), Robbery (2)"
  "Connected to: Ramesh Naik · Syed Ahmed"  (blue clickable)
  [View Full Intelligence Profile →]
```

**Result — Phone Number ("9845012345")**
```
"📱 +91 9845012345"
"This number appears in 8 FIRs"
"Registered to: Ramesh Naik (as per FIR records)"
"Districts seen: Bangalore · Mysuru · Belagavi"
"⚠️ Also appears under different names — possible alias usage"
[See All 8 Cases]  [See Person Profile]
```

**Result — Vehicle ("KA-05 MX 1234")**
```
"🏍️ KA-05 MX 1234 · Black Bajaj Pulsar"
"Mentioned in 6 FIRs as suspect vehicle"
"Crime type: Chain Snatching (all 6)"
"Pattern: All incidents between 6 PM and 9 PM, Indiranagar area"
"⚠️ This vehicle has a consistent pattern"
[See All 6 Cases]  [See Location History]
```

---

### Screen 4 — Intelligence Profile Page

**Purpose:** Everything known about one person. Detective's case file, not a database view.

**Header**
```
"Kiran Kumar"  28px bold
"alias Drill Kiran, Kiran Naik"  muted italic
"HIGH RISK OFFENDER"  large red pill
"Age 34 · Male · From Dharwad · Last seen Belagavi Nov 2024"
```

**Left Column (40%)**

*Known Details card*
```
Aadhaar:  ••••••••3421  (masked)
Phones:   3 numbers — each with case count
          98450-12345 · 8 cases
          76543-21098 · 3 cases
          99887-65432 · 1 case
Addresses: 2 on record
Vehicle:   KA-05 MX 1234 · Black Pulsar
```

*Family & Connections card*
```
Father:  Kumar Naik — no criminal record
Brother: Suresh Naik — [2 NDPS cases] (clickable)
Associates:
  [Ramesh Naik] — "together in 14 cases"
  [Syed Ahmed]  — "together in 14 cases"
"These 3 people operated as a group across 3 districts"
```

*How They Operate card*
```
Plain paragraph:
"Breaks into locked houses between midnight and 4 AM
 using a hand drill on front door locks. Targets homes
 when owners are travelling. Works with 1–2 others."

"This same method appears in 14 cases —
 probably all connected to this person"
[See all 14 linked cases →]
```

*Phone Pattern card*  ← NEW — key intelligence feature
```
"Phone Number Activity"
Number: 98450-12345
  "Appears in 8 cases across 4 districts"
  "Also linked to: Ramesh Naik, Syed Ahmed"
  "⚠️ 3 different people used this number —
     likely a shared gang phone"

Movement pattern:
  Timeline showing which district the number
  appeared in, in order — reveals travel pattern
```

**Right Column (60%)**

*Case History — timeline view*
```
Filter: [All 14] [Arrested] [Pending] [Acquitted]
Vertical timeline newest first:
  Nov 2024 · House Burglary · Belagavi · ARRESTED · #BLR/24/047
  Aug 2024 · House Burglary · Mysuru   · ARRESTED · #MYS/24/089
  May 2024 · House Burglary · Bangalore· PENDING  · #BLR/24/023
  [Show 11 more ▾]
```

*Movement Across Karnataka*
```
Small Karnataka map
Dots at each case location, connected in time order
"This person has operated in 3 districts over 3 years"
```

*Connected People*
```
Simple visual:
  [Kiran Kumar] ──── "14 cases together" ──── [Ramesh Naik]
               ──── "14 cases together" ──── [Syed Ahmed]
               ──── "Co-accused, unidentified" ──── [Unknown A3]

"These 3 people committed crimes together across
 Bangalore, Mysuru, and Belagavi"
[View full group →]
```

---

### Screen 5 — Crime Networks ("Who Knows Who")

**Purpose:** Show organised crime groups. For analysts investigating gangs.

**Left Panel — Find Connections**
```
"Find Connections For:"
Search input: "Name, phone, or case number..."

"Detected Crime Groups"
Subtext: "Groups of people found working together"

Group Card 1:
  "Drill & Enter Group"
  "3 people · 60 cases · Bangalore, Mysuru, Belagavi"
  "2 in custody · 1 AT LARGE" (AT LARGE red)
  [View Group]

Group Card 2:
  "Indiranagar Chain Snatching Group"
  "3 people · 250 cases · Bangalore"
  "All 3 identities unknown — suspects at large"
  [View Group]

Group Card 3:
  "Online Banking Fraud Ring"
  "5 people · 150 cases · Urban Karnataka"
  "3 in custody · 2 at large"
  [View Group]
```

**Graph Area — "Drill & Enter Group"**
```
Above graph (plain English explanation):
"3 people are connected through 60 crimes across 3 districts.
 They shared a phone number and a vehicle."

NETWORK GRAPH:
  Red circles = People (name visible: Kiran Kumar, Ramesh Naik,
  Syed Ahmed). Size = number of cases.
  Phone icon node = "Shared phone: 98450-12345"
  Bike icon node = "Shared vehicle: KA-05 MX 1234"
  Small blue clusters = victims per district

  Edge labels ON graph (not just hover):
  "Together in 14 cases"
  "All used this number"
  "Same vehicle"

  Syed Ahmed node: red glow + "AT LARGE" label

Bottom of graph:
"These 3 worked together in 60 break-ins across 3 districts
 between March 2022 and November 2024."
[Export Group Report]  [Flag All Members]  [Alert Stations]
```

---

### Screen 6 — Situations Needing Attention (Alerts)

**Purpose:** "What needs my attention today?" Plain language for both DGP and analyst.

**Left Feed**
```
"Situations Needing Attention"
"Updated automatically · 29 June 2026"
Tabs: [All] [Urgent] [Watch] [Information]

CARD 1 — URGENT (red left border):
  "URGENT" pill · "2 hours ago"
  "Kidnapping spike in Raichur"
  "3 kidnappings happened in 2 days. This is 6 times
   higher than the monthly average of 1 case."
  [Investigate →]  [Assign Officer]

CARD 2 — WATCH (amber):
  "Known offender may be active again"
  "Kiran Kumar was released on bail 3 months ago.
   2 new burglaries matching his method reported since."
  [View Profile →]  [Alert Local Stations]

CARD 3 — WATCH (amber):
  "Same break-in method — 5 cases, 3 districts"
  "Likely the same group operating across Karnataka"
  [See All 5 Cases →]  [Link Cases]

CARD 4 — WATCH (amber):
  "Diwali season — online fraud rising"
  "Cyber scam reports are up in October. Happens every year."
  [See Cases]

CARD 5 — INFO (blue):
  "Mysuru improving — crime down 18%"
  "Violent crime declining for 3 months straight."
  [View Mysuru Report]
```

**Right Detail Panel (selected alert)**
```
"Kidnapping Spike — Raichur District"
"URGENT · 2 hours ago"

Plain summary box:
"What happened: 3 kidnapping cases were registered in Raichur
 in the last 48 hours. Normally Raichur sees about 1 kidnapping
 per month. This week's count is 6 times higher than usual."

Three compact case cards side by side

Small Raichur map with 3 case dots

Recommended Action (amber tint box):
"Suggested response: Deploy additional patrol units to Raichur
 North and Central zones. Issue lookout notice for suspects
 described in Case #RAI/26/0034."

[Generate Briefing Report]  [Assign to IO]  [Mark Resolved]
```

---

### Screen 7 — District Drill-Down

**Purpose:** Full picture of one district. Officer asks "What's happening in my district?"

**Header**
```
"Mysuru District"
[This Week]  [This Month]  [Last 3 Months]  [Custom]
"Compared to: [State Average ▾]"
```

**Summary Card — plain language**
```
"Mysuru had 847 crimes this month.
 This is 12% more than last month, but still
 below the state average for a district this size."

Watch: Vehicle Theft is up 34% this month
Good news: Violent crime is down 18% vs last year
```

**Station Breakdown Table**
```
Station            | Cases | Resolved | Pending | Status
Mysuru Town PS     |  234  |  156 67% |    78   | Normal
Mysuru Rural PS    |  189  |   98 52% |    91   | ⚠️ Needs attention
Chamundi Hill PS   |   87  |   62 71% |    25   | Good ✓

"Mysuru Rural PS has the most unresolved cases relative
 to its size. May need additional officer deployment."
```

**Top Offenders in This District**
```
1. Kiran Kumar — 14 linked cases — Currently at large
2. Raju D.     — 8 cases — In custody
3. ...
[See All Offenders in Mysuru]
```

---

## 6. Visual Design Tokens

### Colours
```
Background:       #0D1117   — page background
Surface:          #161B22   — cards
Surface raised:   #1C2128   — hover state
Border:           #21262D   — dividers
Border active:    #30363D   — focused/hover borders

Text primary:     #E6EDF3   — headings, numbers
Text secondary:   #C9D1D9   — body copy
Text muted:       #8B949E   — labels, metadata
Text disabled:    #484F58

Accent blue:      #1E6FD9   — buttons, links, active state
Accent blue lt:   #58A6FF   — icons on dark backgrounds

Alert red:        #F85149   — urgent, high risk
Alert red tint:   #F8514912 — card background tint
Alert amber:      #D29922   — watch, warning
Alert amber tint: #D2992212
Success green:    #3FB950   — resolved, improving
Success tint:     #3FB95012
Info blue:        #388BFD   — informational only
```

### Typography
```
All UI:           Inter
KPI numbers:      Inter · 32–48px · Weight 700
Section titles:   Inter · 18–20px · Weight 600
Body:             Inter · 13–14px · Weight 400
Labels:           Inter · 11–12px · Weight 500 · uppercase for category labels
Case IDs only:    JetBrains Mono · 12px  ← the ONE exception
```

### Components
```
Cards:
  bg #161B22 · border 1px #21262D · radius 10px
  padding 20px · NO drop shadows

Buttons:
  Primary:   bg #1E6FD9 · white text · radius 7px · pad 10px 18px
  Secondary: border 1px #30363D · text #C9D1D9
  Danger:    bg #F85149 · white text
  All:       font-size 13px · font-weight 500

Status Pills:
  "HIGH RISK OFFENDER":  bg #F8514920 · text #F85149 · border #F8514940
  "WATCH":               bg #D2992220 · text #D29922 · border #D2992240
  "RESOLVED":            bg #3FB95020 · text #3FB950
  "IN CUSTODY":          bg #388BFD20 · text #388BFD
  "AT LARGE":            bg #F8514940 · text #F85149 · border 1px solid #F85149

Alert left borders:
  Urgent:  border-left 3px solid #F85149
  Watch:   border-left 3px solid #D29922
  Info:    border-left 3px solid #388BFD

Tables:
  Header: bg #0D1117 · text #8B949E · 11px uppercase
  Row:    border-bottom 1px #21262D
  Hover:  bg #1C2128
  NO zebra striping
```

---

## 7. Complete Stitch Prompts

---

### Stitch Prompt 1 — App Shell + Sidebar

```
Design a dark-mode intelligence dashboard for Karnataka State Police.
Named "Drishti". Designed for senior police officers (DGP/IGP level),
not developers. Professional, clear, authoritative — not techy or
cyberpunk. Like a premium government intelligence portal.

SHELL: Fixed left sidebar 220px. Top header 56px. Main content fills rest.

SIDEBAR (bg #0D1117, right border 1px #21262D):
  Top: Shield badge icon + "DRISHTI" bold 16px white
  Below: "Karnataka State Police" 11px in #8B949E
  Gap, then nav links with icons (icon left, label right):
    Home
    Crime Map
    Search & Investigate
    Intelligence Profiles
    Crime Networks
    Situations (bell icon with red badge "3")
    Reports
  Active state: left border 3px #1E6FD9, row bg #1E6FD910, icon #58A6FF
  Inactive: icon and text #8B949E
  Bottom: avatar circle + "DGP R. Sharma" + Logout icon

HEADER (bg #161B22, border-bottom 1px #21262D):
  Left: "Good morning, DGP Sharma" 15px white
  Centre: Search bar "Search by name, phone, vehicle, case..." 
          wide, rounded, dark bg #0D1117
  Right: Bell icon | date "Mon 29 Jun 2026" | small avatar

COLOURS: bg #0D1117, surface #161B22, border #21262D,
         accent #1E6FD9, text #E6EDF3, muted #8B949E
FONT: Inter throughout. Clean, readable. No monospace except case IDs.
FEEL: Professional government portal. Calm and authoritative.
```

---

### Stitch Prompt 2 — Home / Command Centre

```
Home page inside Drishti shell. Karnataka State Police.
For a DGP to open every morning and understand crime at a glance.
ALL text in plain English. No technical jargon anywhere.

TOP: Full-width "Morning Brief" card (#1C2128, padding 24px).
Large text: "Karnataka recorded 847 crimes yesterday.
Bangalore Urban and Raichur require immediate attention today."
Subtext muted: "Auto-generated · Updated 6:00 AM · 29 June 2026"

KPI ROW (4 equal cards, #161B22, radius 10px, border #21262D):
1. "Crimes This Month" — "12,847" 36px bold — "↑ 340 more than last month" red below — tiny sparkline
2. "Cases Solved" — "7,203" — "56% resolution rate" — "Better than last year" green
3. "Arrests Made" — "4,891" — "This month · 234 heinous crime arrests" muted
4. "Districts Needing Attention" — large "3" — "Bangalore · Raichur · Kolar" — "Action Required" red pill

MIDDLE (two columns):
LEFT 55%: Karnataka state map. Districts shaded from cream (low crime)
to deep red (high crime). Three districts with soft pulsing red glow.
Hover shows: district name, crime count, trend arrow. Clean, readable
from across a room. Label top: "Crime Intensity Map — Click any district"

RIGHT 45%: "What Needs Attention" — 3 stacked alert cards:
  Red left border card: "Unusual spike in Raichur" — "3 kidnappings
  in 2 days — 6× higher than normal" — [Investigate →] blue link
  Amber card: "Repeat offender active — Bangalore" — brief description
  — [View Profile →]
  Amber card: "Same break-in method — 3 districts — likely same group"
  — [See Linked Cases →]

BOTTOM: Full-width area chart "Crime Trend — Last 2 Years". Clean blue
line with subtle gradient fill. Month labels "Jan 2023" plain format.
One grey shaded band over Oct-Nov labelled "Festive Season".
No sigma symbols, no statistical terms.
```

---

### Stitch Prompt 3 — Crime Map

```
Crime Map page inside Drishti. Karnataka State Police.

Map fills entire content area (after sidebar). Dark map tiles.
Karnataka at state level. Designed for "where is crime happening?"

FLOATING TOP BAR (semi-transparent dark, 48px, over map):
Left: plain dropdowns "Show me: [All Crimes ▾]" "In: [All Karnataka ▾]"
"During: [Last 30 Days ▾]"
Right: toggle "Areas / Heatmap / Incidents" — "3 Situations Need
Attention" red badge button

MAP: Districts shaded cream to deep red by crime volume.
Hover tooltip card: "Mysuru District · 847 crimes · ↑12% · Top: Theft"
3 districts with soft red pulsing glow (Bangalore, Raichur, Kolar).
Click district: bottom sheet slides up with full district breakdown.

TIME SLIDER (floating bottom, full width, semi-transparent #161B22DD):
Label left: "What time do crimes happen?"
Slider 12AM to 11PM. Thumb at 8PM. Current: "8 PM — Evening Peak"
Below: "Most chain snatchings happen between 6 PM and 9 PM"
▶ Play button to animate through 24 hours.

ALERT CARD (floating top-right, 300px, red left border):
"⚠️ Unusual Activity — Raichur"
"Kidnappings this week are much higher than normal.
 3 cases in 48 hours — average is 1 per month."
[Investigate]  [Dismiss]

FEEL: Map-first. Controls float cleanly. Officers should feel like
looking at an intelligence briefing map, not a developer dashboard.
```

---

### Stitch Prompt 4 — Search Results Page

```
Search & Investigate page for Drishti. Karnataka State Police.
User searched for "Kiran Kumar". Show results clearly.

TOP: Large search bar with "Kiran Kumar" typed in.
Filter chips: [Person ✓] [Phone] [Vehicle] [Case ID] active on Person.
"Showing results for: Kiran Kumar — 1 direct match, 3 partial matches"

MAIN RESULT CARD (full width, #161B22, border #21262D, radius 10px,
padding 24px):
  Left:
    "Kiran Kumar" 24px bold white
    "also known as: Drill Kiran, Kiran Naik" muted italic
    Pills: "HIGH RISK OFFENDER" red | "Repeat Offender" amber
    "Age 34 · Male · Last seen: Belagavi, November 2024"
    
  Right stats column:
    "14 FIRs" large | "3 Districts" | "AT LARGE" red bold
  
  Below full-width line:
    "Known for: House Burglary (12 cases), Robbery (2 cases)"
    "Connected to: Ramesh Naik · Syed Ahmed" — blue clickable names
    [View Full Intelligence Profile →] prominent blue button right

SECONDARY RESULTS (smaller cards below):
"Also found in cases as co-accused:"
Two compact cards: "Kiran Kumar Naik — 2 cases, Mysuru" [View]
                   "Kiran Kumar Reddy — co-accused in 1 case" [View]

PHONE RESULT PREVIEW (separate section, grey bg card):
"📱 Phone 98450-12345 also linked to this person — appears in 8 FIRs"
[Search this number →]

FEEL: Clear, immediate, like a well-organised case file. Senior officers
understand it in seconds. Analysts can dig deeper.
```

---

### Stitch Prompt 5 — Intelligence Profile Page

```
Intelligence Profile for "Kiran Kumar alias Drill Kiran".
Drishti · Karnataka State Police.
Designed like a detective's case file, not a database view.

HEADER (full-width card #1C2128):
"Kiran Kumar" 28px bold white
"alias Drill Kiran, Kiran Naik" muted italic 14px below
"HIGH RISK OFFENDER" large red pill    "Repeat Offender" amber pill
Fact row 13px muted: "Age 34 · Male · From Dharwad · Last seen Belagavi Nov 2024"

TWO COLUMN LAYOUT:

LEFT (40%), 3 cards stacked:

Card A "Known Details":
  Aadhaar: ••••••••3421 (masked for privacy)
  Phone numbers on record:
    98450-12345  ·  appears in 8 cases
    76543-21098  ·  appears in 3 cases
    99887-65432  ·  appears in 1 case
  Addresses: 2 on record (expandable)
  Vehicle: KA-05 MX 1234 · Black Bajaj Pulsar

Card B "Family & Connections":
  Father: Kumar Naik — no criminal record
  Brother: Suresh Naik — blue link "2 NDPS cases"
  Associates: [Ramesh Naik] [Syed Ahmed] — clickable blue pills
  "These 3 operated as a group across 3 districts"

Card C "How They Typically Operate":
  Paragraph text (NOT bullet points):
  "Breaks into locked houses between midnight and 4 AM using
  a hand drill on front door locks. Targets homes when owners
  are travelling. Works with 1–2 other people."
  Below: "This same method appears in 14 cases — probably
  all connected to this person or group"
  [See all 14 linked cases →] blue link

RIGHT (60%), 3 cards stacked:

Card D "Case History — 14 FIRs":
  Filter tabs: [All 14] [Arrested] [Pending] [Acquitted]
  Vertical timeline newest first:
    ● Nov 2024  House Burglary · Belagavi  ARRESTED  #BLR/24/047
    ● Aug 2024  House Burglary · Mysuru    ARRESTED  #MYS/24/089
    ● May 2024  House Burglary · Bangalore PENDING   #BLR/24/023
    [Show 11 more ▾]

Card E "Movement Across Karnataka":
  Karnataka map placeholder, dots at case locations connected by
  line in time order showing travel pattern across 3 districts.
  Label: "Has operated in 3 districts over 3 years"

Card F "Connected People":
  Clean simple diagram:
    Central: "Kiran Kumar"
    Line to "Ramesh Naik" with label "14 cases together"
    Line to "Syed Ahmed" with label "14 cases together"
    Line to "Unknown suspect" with label "Unidentified co-accused"
  Below: "These 3 worked together across Bangalore, Mysuru, Belagavi"
  [View full group →]

FEEL: Like reading a detective's file. Every section answers one
question. Senior officers understand it immediately.
```

---

### Stitch Prompt 6 — Crime Networks Page

```
"Crime Networks" page inside Drishti. Karnataka State Police.
Shows organised crime groups. For intelligence analysts.

LAYOUT: Left panel 320px + right graph area fills rest.

LEFT PANEL (#161B22, right border 1px #21262D, padding 20px):
Header: "Find Connections" 16px bold
Search input: "Enter a name, phone number, or case..."

Section title: "Detected Crime Groups" bold 13px
Subtext: "Groups of people found to be working together" muted

3 group cards (stacked, #0D1117, border #21262D, radius 8px):

Card 1: "Drill & Enter Group" 14px bold white
  "3 people · 60 cases · Bangalore, Mysuru, Belagavi"
  "2 in custody · 1 AT LARGE" — AT LARGE in red text
  [View Group] blue button

Card 2: "Indiranagar Chain Snatching Group"
  "3 people · 250 cases · Bangalore"  
  "All 3 identities unknown"
  [View Group]

Card 3: "Online Banking Fraud Ring"
  "5 people · 150 cases · Urban Karnataka"
  "3 in custody · 2 at large"
  [View Group]

RIGHT GRAPH AREA (#0D1117, padding 24px):
Top explanation text (always visible, not in tooltip):
"Drill & Enter Group — 3 people connected through 60 crimes
 across 3 districts. Shared a phone number and a vehicle."

NETWORK GRAPH (centred, takes up most of area):
  Large red circles = people. Names visible. Sized by case count.
    "Kiran Kumar" — largest
    "Ramesh Naik" — medium
    "Syed Ahmed" — medium, with red glow + "AT LARGE" label
  Small phone icon node: "Shared phone: 98450-12345"
  Small bike icon node: "Shared vehicle: KA-05 MX 1234"
  Small blue cluster: "Victims · Bangalore"
  
  Connection labels ON the graph lines (visible, not just hover):
    "Together in 14 cases"
    "All used this number"
  
  Amber highlight box around all 3 people: "Suspected Group"

Bottom bar text:
"These 3 people worked together in 60 break-ins across 3 districts
 between March 2022 and November 2024."
[Export Group Report]  [Flag All Members]  [Alert Stations]

FEEL: The graph is explained in plain language. Labels visible on
graph itself. Not a technical force-directed graph for developers.
```

---

### Stitch Prompt 7 — Situations / Alerts Page

```
"Situations Needing Attention" page. Drishti · Karnataka State Police.
NOT labelled "Anomaly Detection Feed".

LAYOUT: Left feed 460px + right detail panel fills rest.

LEFT FEED (#161B22, right border 1px #21262D):
Header: "Situations Needing Attention" 18px bold white
Subtext: "Updated automatically · 29 June 2026" muted
Filter tabs: [All] [Urgent] [Watch] [Information]

5 alert cards scrollable (#0D1117, border #21262D, radius 8px, mb 8px):

Card 1 URGENT (border-left 3px #F85149):
  "URGENT" #F85149 pill  ·  "2 hours ago" muted right
  "Kidnapping spike in Raichur" 14px bold white
  "3 kidnappings happened in 2 days. This is 6 times higher
   than the monthly average of 1 case." 12px #C9D1D9
  [Investigate →]  [Assign Officer] buttons

Card 2 WATCH (border-left 3px #D29922):
  "Known offender may be active again"
  "Kiran Kumar released on bail 3 months ago. 2 new burglaries
   matching his method have been reported since."
  [View Profile →]  [Alert Local Stations]

Card 3 WATCH:
  "Same break-in method — 5 cases, 3 districts"
  "Likely the same group operating across Karnataka"
  [See All 5 Cases →]  [Link Cases]

Card 4 WATCH:
  "Diwali season — online fraud rising"
  "Cyber scam reports are up in October. Annual pattern."
  [See Cases]

Card 5 INFO (border-left 3px #388BFD):
  "Mysuru improving — crime down 18%"
  "Violent crime declining for 3 months."
  [View Mysuru Report]

RIGHT DETAIL PANEL (#0D1117, padding 24px):
Selected: Card 1 expanded.
"Kidnapping Spike — Raichur District" 22px bold
"URGENT  ·  Reported 2 hours ago  ·  Auto-detected"

Summary box (#1C2128, radius 8px, padding 16px):
"What happened: 3 kidnapping cases registered in Raichur in
 the last 48 hours. Normally Raichur sees about 1 kidnapping
 per month. This week's count is 6 times higher than usual."

Three compact case cards side-by-side (case number, date, location, status)

Small Raichur area map with 3 dots showing case locations

Recommended Action box (#D2992210, border 1px #D29922, radius 8px):
"Suggested response: Deploy additional patrol units to Raichur
 North and Central zones. Issue lookout notice for suspects
 described in Case #RAI/26/0034."

[Generate Briefing Report]  [Assign to IO]  [Mark Resolved]

FEEL: Calm and informative. Officers should feel informed not
overwhelmed. Plain English throughout. Red/amber used only for
genuine urgency, not decoration.
```

---

## 8. What NOT to Design

```
❌ Sigma (σ) symbols anywhere
❌ "Anomaly score", "node", "edge", "cluster" as UI labels
❌ Monospace fonts everywhere (only case IDs)
❌ More than 5 data points on one card
❌ Colour used decoratively (only for data meaning)
❌ Tooltips as the only way to understand something
❌ Raw database IDs as primary labels
❌ Animations that don't represent real data
❌ Technical ML model names visible to users
❌ Overwhelming number of charts on one screen
```

## 9. What TO Design

```
✅ Plain English before every data section
✅ One headline insight per card
✅ Red/amber/green used consistently everywhere
✅ Every number answers a stated question
✅ One primary action per screen
✅ Timeline views over raw tables
✅ Maps readable from across a room
✅ Search as the primary intelligence entry point
✅ Network graphs with plain text explanations below them
✅ "What this means" callouts on complex insights
✅ AT LARGE in red — IN CUSTODY in blue — always
```

---

*Drishti · Karnataka State Police · SCRB Intelligence Platform*
*Design Brief v2.0 · Datathon 2026*
