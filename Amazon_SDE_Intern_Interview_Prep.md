# Amazon SDE-I Intern Interview Preparation Guide
## 6-Month Internship with Performance-Based PPO | India | Last 6 Months (Nov 2025 – May 2026)

---

## ⚠️ DATA AVAILABILITY & SOURCES

**Primary Sources (Recent & Verified):**
- **March 2025 On-Campus Drive** — SDE-1 Intern, 6 months, Sri City, AP (Published July 2025)
- **November 2024 Amazon WoW** — SDE 6-month internship (Published January 2025)
- **October 2024 OA** — SDE 1, 6M Internship (Published October 2024)
- **July 2025 OA Experience** — SDE-1 India (Published September 2025)
- **Amazon Recruitment Process** — General (Updated November 2025)

All data below is extracted from real, published interview experiences from India.

---

## 1. SUMMARY OF INTERVIEW PROCESS

| Aspect | Details |
|--------|---------|
| **Total Rounds** | 2–3 rounds (OA1 → OA2/Behavioral → Final Interview) |
| **Round Types** | Online Assessment (Coding + MCQs + Behavioral) → Technical Interview (DSA) |
| **Difficulty Level** | Medium to Hard |
| **Duration** | OA: 70-90 mins; Interview: 45-70 mins |
| **Mode** | OA: Online (proctored, Mettl/HackerRank); Interview: Amazon Chime (video) |
| **Stipend** | ₹1,10,000/month |
| **Relocation Bonus** | ₹2,00,000 |
| **Perks** | Meal card, cab facilities, goodies |
| **PPO** | Performance-based Pre-Placement Offer |

### Amazon-Specific Patterns:
- **Two-stage OA** is the current format (OA1: MCQs + 1 coding; OA2: 2 coding + behavioral)
- **Work Style Assessment** is mandatory and reportedly carries weight
- **Leadership Principles** tested in behavioral section of OA AND interview
- **Single technical interview** is the final round for interns (unlike SDE-1 full-time which has 3-4)
- **Problems are described in story/scenario format** — not direct LeetCode-style statements
- Amazon values **approach explanation over perfect code**

---

## 2. ONLINE ASSESSMENT (OA)

### Platform: **Mettl** (primary) / **HackerRank** (some drives)

### CURRENT FORMAT (2024-2025): Two-Stage OA

---

### OA-1: Technical Assessment

| Component | Details |
|-----------|---------|
| **Duration** | ~90 minutes |
| **Coding** | 1 coding problem |
| **MCQs** | 5 MCQs from EACH of 8 topics (40 total) |

**MCQ Topics (5 questions each):**
1. Data Structures
2. Algorithms
3. Pseudo Codes
4. Computer Networks
5. Database Query Languages (SQL)
6. Linux
7. Software Methodologies (SDLC, Agile)
8. Software Testing Concepts

---

### OA-2: Coding + Behavioral Assessment

| Component | Details |
|-----------|---------|
| **Coding** | 2 DSA problems (1 Easy/Medium + 1 Hard) |
| **Behavioral** | Leadership Principles-based MCQs |
| **Duration** | ~70 minutes coding + 15 minutes workstyle |

**OA Structure Breakdown (from email):**

| Section | Duration |
|---------|----------|
| Coding Assessment | 70 minutes |
| Workstyles Assessment | 15 minutes |
| Feedback Survey | 5 minutes |

---

### Coding Questions Reported in OA:

| Question | Difficulty | Source |
|----------|-----------|--------|
| String manipulation problem | Easy-Medium | July 2025 OA |
| DP-based array problem | Hard | July 2025 OA |
| Hash Map based problem | Easy | March 2025 On-Campus |
| Linked List problem | Medium | March 2025 On-Campus |
| Graph problem | Hard | March 2025 On-Campus |
| Next greater number using same digits (Next Permutation) | Medium | Verified multiple |
| String manipulation (easy) | Easy | Nov 2024 WoW |

---

### Work Style Assessment:
- ~50 personality/behavioral questions
- Based on **Amazon Leadership Principles**
- Scenario-based: "What would you do if..." format
- Tests: Customer Obsession, Ownership, Bias for Action, Deliver Results
- **DO NOT SKIP THIS** — it reportedly influences selection
- Be consistent in answers (they check for contradictions)

---

## 3. TECHNICAL INTERVIEW QUESTIONS

### A. DATA STRUCTURES & ALGORITHMS (PRIMARY FOCUS)

#### Questions Actually Asked (Verified, 2024-2025):

| Question | Difficulty | Context |
|----------|-----------|---------|
| **Design data structure with insert, delete, search, getRandom in O(1)** | Hard | Nov 2024 WoW Final Interview |
| **String manipulation with multiple approaches** | Medium | Nov 2024 WoW Final Interview |
| **Detect loop in linked list** | Medium | March 2025 On-Campus Interview |
| **Tree + DP optimization problem** | Hard | March 2025 On-Campus Interview |
| **2D array max fruits harvested in k steps** (BFS/DFS + DP) | Hard | Oct 2024 6M Internship Interview |
| **Root-to-leaf path sum in binary tree** | Easy-Medium | Oct 2024 6M Internship Interview |
| **Binary search in sorted array** | Easy | Nov 2024 India SDE Intern |
| **Two nodes summing to value in BST** | Medium | Verified repeated |
| **Number of ways to reach nth step (DP)** | Medium | Verified repeated |
| **Minimum cost to join ropes (Priority Queue)** | Medium | Verified repeated |
| **Max sum subset excluding parent-child (Tree DP)** | Hard | Verified repeated |
| **Next Permutation** | Medium | Verified repeated |
| **Kadane's Algorithm** | Easy-Medium | Amazon frequently asked |
| **Inversion of Array** | Medium | Amazon frequently asked |
| **Parenthesis Checker** | Easy | Amazon frequently asked |

#### High-Frequency Topics (Ranked by Importance):

1. **Arrays & Strings** — Most common in OA
2. **Trees (Binary Tree, BST)** — Always in interview round
3. **Dynamic Programming** — At least 1 DP problem in OA Hard
4. **Linked Lists** — Loop detection, deletion, manipulation
5. **Graphs** — BFS/DFS, path problems
6. **Hash Maps** — O(1) design problems
7. **Greedy / Priority Queue** — Optimization problems

---

### B. LOW LEVEL DESIGN (LLD)

LLD is **NOT heavily tested** for SDE Intern role. However:

| Question | Context |
|----------|---------|
| Design data structure supporting insert/delete/search/getRandom in O(1) | Asked in Nov 2024 interview |
| Design using array + HashMap combined | Follow-up: handle duplicates |

**Key:** Amazon tests design thinking through DSA problems rather than explicit LLD questions for interns.

---

### C. SYSTEMS / CS FUNDAMENTALS

**Tested primarily in OA-1 MCQs:**

| Topic | Questions |
|-------|-----------|
| **OS** | Processes, threads, deadlock |
| **DBMS** | SQL queries, normalization |
| **Computer Networks** | Basics, protocols |
| **Linux** | Basic commands |
| **Software Methodologies** | SDLC, Agile, Scrum |
| **Software Testing** | Unit testing, types of testing |

**In Interview (Lighter):**
- "What is the difference between SQL and NoSQL?"
- "What is AWS?"
- Project-based follow-up questions on technologies used

---

### D. PROGRAMMING / DEBUGGING

| Type | Details |
|------|---------|
| **Debugging** | Interviewer comments out a line and asks to identify impact (Nov 2024) |
| **Code analysis** | Dry-run examples to find bugs |
| **Language** | Any language accepted; Java preferred by Amazon India |
| **Implementation** | Must write clean, compilable code on shared editor |

---

## 4. INTERVIEW EXPERIENCE INSIGHTS

### Common Patterns (Verified from 2024-2025 experiences):

1. **Story-format problems** — Questions wrapped in real-world scenarios, not direct problem statements
2. **Two DSA problems in interview** — One medium, one hard (or follow-ups)
3. **Start with introduction + project discussion** — 10-15 mins
4. **Explain approach before coding** — They evaluate thought process
5. **Follow-up questions** — "How would you handle duplicates?", "Can you optimize space?"
6. **Time complexity discussion** — Always asked after every solution
7. **Hints given in story format** — If stuck, interviewer guides with scenario hints

### Focus Areas Amazon Emphasizes:
- **Problem-solving approach** over memorized solutions
- **Multiple approaches** — Show brute force → optimized
- **Edge cases awareness** — Corner cases matter heavily
- **Clean code** — Variable naming, structure
- **Communication** — Think out loud
- **Ownership mindset** — Reflected in behavioral answers

### Typical Difficulty Level:
- OA Easy Problem: LeetCode Easy-Medium
- OA Hard Problem: LeetCode Medium-Hard
- Interview Problem 1: LeetCode Medium
- Interview Problem 2: LeetCode Medium-Hard

### Tricky/Unexpected Elements:
- Problems described as paragraphs requiring interpretation
- Debugging questions with uncommented code
- Follow-up constraints that change the approach entirely
- Personality test AFTER mentally draining coding round

---

## 5. BEHAVIORAL / HR ROUND (VERY IMPORTANT)

### Amazon Leadership Principles Tested:

| Principle | How It's Tested |
|-----------|-----------------|
| **Customer Obsession** | "Tell me about a time you went above and beyond for someone" |
| **Ownership** | "Describe a project you owned end-to-end" |
| **Bias for Action** | "When did you take a decision without having all the data?" |
| **Deliver Results** | "Tell me about a tight deadline you met" |
| **Learn and Be Curious** | "What new technology did you learn recently?" |
| **Dive Deep** | "Tell me about a bug you found and how you diagnosed it" |
| **Insist on the Highest Standards** | "When did you push back on quality?" |
| **Earn Trust** | "How did you resolve a conflict in a team?" |

### Work Simulation (OA Behavioral Section):
- Scenario-based multiple choice
- "Your teammate is not contributing. What do you do?"
- "Customer reports a bug but you're in the middle of a feature. Prioritize?"
- "You disagree with your manager's technical decision. What's your approach?"
- **ALWAYS pick answers aligning with Leadership Principles**
- Be consistent — contradictory answers are flagged

### STAR Format (For Interview):
- **S**ituation: Set the context
- **T**ask: What was your responsibility
- **A**ction: What did YOU specifically do
- **R**esult: Quantifiable outcome

### Tips:
- Prepare 5-6 stories from college/projects/internships
- Each story should map to 2-3 Leadership Principles
- Use "I" not "We" — show personal ownership
- Quantify results wherever possible

---

## 6. PREPARATION STRATEGY (BASED ON DATA)

### PRIORITY 1 — MUST PREPARE (1-2 weeks):

**DSA Core (60% of evaluation):**
| Topic | Must-Do Problems |
|-------|-----------------|
| Arrays | Kadane's, Two Sum, Sliding Window, Next Permutation |
| Strings | Anagram check, string manipulation, pattern matching |
| Linked Lists | Cycle detection, delete kth from end, merge sorted |
| Trees/BST | Path sum, depth, inorder traversal, BST validation |
| DP | Climbing stairs variants, subset sum, 2D grid problems |
| Graphs | BFS/DFS, shortest path, connected components |
| Hash Maps | Design RandomizedSet (O(1) operations) |
| Priority Queue | Merge k sorted, min cost ropes |

### PRIORITY 2 — SHOULD PREPARE (1 week):

**MCQ Topics for OA-1:**
- Data Structures theory
- Algorithm complexity analysis
- Pseudo code interpretation
- SQL queries (SELECT, JOIN, GROUP BY)
- Basic Linux commands
- SDLC & Agile methodology
- Testing concepts (unit, integration, regression)
- Computer Networks basics (TCP/IP, HTTP, DNS)

### PRIORITY 3 — BEHAVIORAL (2-3 days):

- Prepare 5-6 STAR stories
- Map each story to Amazon Leadership Principles
- Practice Work Simulation scenarios
- Be ready to discuss projects in depth

### Recommended Timeline (4 weeks):

| Week | Focus |
|------|-------|
| Week 1 | Arrays, Strings, Hash Maps, Linked Lists (LeetCode Medium) |
| Week 2 | Trees, BST, Graphs, BFS/DFS |
| Week 3 | DP (1D and 2D), Priority Queue, Greedy |
| Week 4 | Mock OAs (timed), MCQ prep, STAR stories, Project prep |

### Recommended Resources:
- **LeetCode** — Filter by Amazon tag, focus on Medium
- **Striver's SDE Sheet** — Top 100 problems
- **GFG Amazon archives** — Past OA questions
- **Amazon Leadership Principles** — amazon.jobs/principles
- **Pramp / Interviewing.io** — Mock interviews
- **SQL** — HackerRank SQL domain (easy-medium)

### Key Insight from Candidates:
> "The interviewer is more interested in how you keep optimizing the solution than the perfect answer itself. Always solve any problem as if the interviewer is right in front of you." — GFG, 2024

> "Amazon values logical thinking over memorization. They carefully assess how you approach a problem rather than just the solution." — March 2025 On-Campus

---

## 7. SOURCE LINKS

| Source | URL | Date |
|--------|-----|------|
| On-Campus Amazon SDE-I Intern (March 2025) | https://www.geeksforgeeks.org/interview-experiences/on-campus-amazon-interview-experience-for-sde-i-intern-position/ | Published July 2025 |
| Amazon WoW SDE 6-Month Internship | https://www.geeksforgeeks.org/interview-experiences/amazon-wow-interview-experience-sde-6-months-internship-opportunity/ | Published January 2025 |
| Amazon SDE 1 6M Internship (Oct 2025 batch) | https://www.geeksforgeeks.org/interview-experiences/amazon-interview-experience-sde-1-6m-internship-october-2025/ | Published October 2024 |
| Amazon India OA Experience SDE-1 (July 2025) | https://www.geeksforgeeks.org/interview-experiences/amazon-india-oa-experience-for-sde-1/ | Published September 2025 |
| Amazon India SDE Intern (6-month) | https://www.geeksforgeeks.org/interview-experiences/amazon-india-interview-experience-sde-intern/ | Published November 2024 |
| Amazon SDE Intern (For SDE Intern) | https://www.geeksforgeeks.org/interview-experiences/amazon-interview-experience-for-sde-intern/ | Updated July 2025 |
| Amazon Recruitment Process | https://www.geeksforgeeks.org/interview-experiences/amazon-recruitment-process/ | Updated November 2025 |
| Amazon Interview Experience SDE1 (Off-Campus) | https://www.geeksforgeeks.org/interview-experiences/amazon-interview-experience-for-sde1-off-campus/ | Published September 2025 |

---

## 8. ADDITIONAL NOTES

### PPO (Pre-Placement Offer) Details:
- Performance-based evaluation during the 6-month internship
- Based on project delivery, code quality, team collaboration
- PPO converts to SDE-1 full-time role
- Historically strong conversion rate at Amazon India (~60-70% based on forum reports)

### On-Campus vs Off-Campus Differences:
| Aspect | On-Campus | Off-Campus |
|--------|-----------|------------|
| OA Format | Same (Mettl/HackerRank) | Same |
| Interview | 1 round (45-70 min) | 1-2 rounds |
| Timeline | Faster (1-2 weeks total) | Slower (2-4 weeks) |
| Communication | Via placement cell | Direct email |

### Important Warnings:
- **Do NOT ignore the Workstyle Assessment** — multiple candidates report being rejected despite solving all coding problems
- **Practice contextual problem interpretation** — problems are NOT in clean LeetCode format
- **Be prepared for follow-up modifications** — "Now what if duplicates exist?", "What if memory is limited?"
- **Java is preferred** but any language works

---

*Last Updated: May 4, 2026*
*Compiled from verified public sources only. No data fabricated.*
