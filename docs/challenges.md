fab
fab.7
Online

fab
 changed the group name: hack 2 get a job. Edit Group — 1:00 PM
Maz — 1:01 PM
Lets keep everything here
fab
 changed the group icon. Edit Group — 1:01 PM
fab — 1:01 PM
project idea: https://www.notion.so/Technical-Requirements-3317c347dc7680dcb40ffb61d0ee9b53
fab’s Space on Notion
Technical Requirements | Notion
Overview
Technical Requirements | Notion
@Maz pls update if u get the chance with your added requirements that narrow it down a bit
@Beanamite condense challenges that we may be eligible for so that we can prompt GPT to add it to business requirements
@D3@dSh0t tech stack recommendation
and I'll set up the repo and figure out multi-agent architecture
Beanamite [USF],  — 1:05 PM
The best fit is Oracle Challenge: Technology in Service of Humanity. Your idea lines up almost perfectly with that prompt because it explicitly focuses on loneliness, mental health, accessibility gaps, caregivers, struggling students, people with disabilities, and older adults, and it asks for an AI solution “rooted in empathy” that genuinely helps real people. That is basically your concept in challenge form.

Your second-best fit is the Google Cloud Challenge, but only if you shape the project as a true multi-agent care coordination system, not just one AI app. That challenge wants a “Multi-Agent Ecosystem” using Google ADK and A2A, with agents that observe, analyze, and act on a large-scale issue in health, equity, or disaster response. So if you build specialist agents like a stress-monitoring agent, caregiver-burden agent, accessibility-support agent, escalation agent, and resource-matching agent, then it could be very strong there too.
These are the challenges we are eligible for. Looks like Google wants us to use the Google ADK and A2A for the multi agent architecture
fab — 1:06 PM
yes, let's look into google ADK and A2A documentation
Beanamite [USF],  — 1:07 PM
"DOCUMENTATIOn" aka ChatGPT
fab — 1:07 PM
oh yeah i forgot you guys know my workflow
yeah, brb gonna prompt everything and come back with answers that seem like my own but i don't know ANY of what im doing
oh also @Maz when you get a chance, wanna look into cursor?
is it free
https://github.com/f-petrozzi/HackUSF26.git
GitHub
f-petrozzi/HackUSF26
Contribute to f-petrozzi/HackUSF26 development by creating an account on GitHub.
Contribute to f-petrozzi/HackUSF26 development by creating an account on GitHub.
Maz — 1:12 PM
Looking at it
Beanamite [USF],  — 1:12 PM
Architecture direction

Build it as a two-layer machine:

1. Digital care operations platform
The stable business platform: data, workflows, security, integrations, notifications, audit, consent, case management.

message.txt
15 KB
Maz — 1:15 PM
Review this @everyone
https://docs.google.com/document/d/1oRKKmIV24vW1cAU8rX4HwQms2U2Bg4EGqt4TYohAD3o/edit?usp=sharing
Google Docs
NüMe
What the platform becomes NüMe A multi-agent wellness and support system. One core platform Shared data layer: user profile wearable metrics meal log recipe activity log recommendation risk flags support contacts Multiple specialist agents Each agent solves one job well. Multi-agent archite...
Image
Maz — 1:28 PM
add a Read me file to the git @fab
can not clone it
fab — 1:29 PM
ok
added
Beanamite [USF],  — 1:31 PM
Attaching the prompt to CLI for the architecture setup
You are a senior staff engineer, distributed systems architect, and Google Agent Development Kit implementation lead.

Build a production-grade hackathon MVP called NüMe.

NüMe is a multi-agent care coordination platform built on Google ADK from day one. It uses wearable signals, behavioral patterns, profile context, and accessibility preferences to detect emerging strain, coordinate specialist reasoning, validate its own recommendations, and trigger practical support actions.

prompt.txt
17 KB
Can @everyone pls review
fab — 1:32 PM
i like it
Beanamite [USF],  — 1:33 PM
Use MCP or MCP-like tools  - We can edit this to Use MCP and not MCP-like
@fab do you think we can give the prompt to claude and setup the architecture aligned folder structure for the git repo:
?*
fab — 1:34 PM
yes, I'm setting up cursor with claude now
Beanamite [USF],  — 1:34 PM
Great
Maz — 1:35 PM
Are preparing a Readme?
Beanamite [USF],  — 2:10 PM
# NüMe

**NüMe** is a multi-agent care coordination platform built on **Google Agent Development Kit (ADK)** from day one.

It uses wearable signals, behavioral patterns, profile context, and accessibility preferences to detect emerging strain, coordinate specialist reasoning, validate its own recommendations, and trigger practical support actions.

README_NüMe_Google_ADK.md
16 KB
fab — 2:20 PM
NüMe — what it is:                                                                                                                                     
                                                                                                                                                             
  NüMe is a care coordination app that monitors your health signals and sends you a personalized support plan when you're struggling.
                                                                                                                                                             
  You open the app, log how you're doing — sleep, stress, mood, activity — or let a wearable simulator do it. Behind the scenes, a team of AI agents analyzes
   your signals in parallel: one reads the data, one assesses the risk level, one plans what you should do. Based on your persona (stressed student,         

message.txt
3 KB
this is what claude summarized for everything we've put together so far ^^^ if it's good with all of you I will have it build the architecture based off of that and split work
Beanamite [USF],  — 2:22 PM
Looks good. Do you not wanna use tjhe prompt I sent? Because it has the technical details that are needed. but if Claude is better at figuring it out on its own, then I, good. Just gotta make sure all the architectural requiremnets are being met
fab — 2:23 PM
yes, it has access to it in docs, that summary is just a super concise summary I asked it to make to make sure we're following a plan
Maz — 2:23 PM
Also please ask Claude to create a readme for the project that specifies the folders and files, for ease of nagivation
fab — 2:23 PM
yes, that's the next step
Beanamite [USF],  — 2:23 PM
sounds good
Maz — 2:24 PM
Also once we get the detailed architect from Claude, We'll need to work on DB, APIs and etc to feed to our agent
Beanamite [USF],  — 2:39 PM
- **Google Cloud Challenge: Building a Self-Healing World with Google ADK**
    
    ## **The Challenge:**
    
    Our world faces "Wicked Problems"—crises too complex, too fast, or too data-heavy for a single human (or a single chatbot) to solve. Your mission is to build a **Multi-Agent Ecosystem** using the Google ADK and A2A protocol that doesn't just "chat" about a problem, but autonomously **observes, analyzes, and acts** to create measurable social impact.
    

Challenge_Requirements.txt
9 KB
﻿
- **Google Cloud Challenge: Building a Self-Healing World with Google ADK**
    
    ## **The Challenge:**
    
    Our world faces "Wicked Problems"—crises too complex, too fast, or too data-heavy for a single human (or a single chatbot) to solve. Your mission is to build a **Multi-Agent Ecosystem** using the Google ADK and A2A protocol that doesn't just "chat" about a problem, but autonomously **observes, analyzes, and acts** to create measurable social impact.
    
    ### **The Goal:**
    
    Build a "System of Agents" that solves a global-scale issue in Climate, Equity, Health, or Disaster Response. Don't build a tool; build a **workforce for good.** We are not here to build chatbots. We are here to engineer **Autonomous Systems of Action.** Your goal is to solve a "Wicked Problem" by creating a distributed workforce of agents that can observe, reason, and act across the **A2A (Agent-to-Agent)** network.
    
    To drive the **ADK** and **Parallel/Looping** requirements, your rubric should reward the *sophistication* of the agentic logic, not just the fact that it exists.
    
    ### Judging Criteria:
    
    #### **1. Architectural Sophistication (The "Brain" Power) - 30%**
    
    - **The Workflow Requirement:** Does the solution use ParallelAgent to handle high-velocity data or LoopAgent for iterative refinement and self-correction?
    - **A2A Interoperability:** Does the agent reach out to other "Specialist" agents (the Handshake) to fill gaps in its own knowledge?
    - **Efficiency:** Does the parallel architecture actually save time or improve the "Moonshot" outcome?
    
    #### **2. Social Impact & Moonshot Vision - 30%**
    
    - **Scalability:** Could this agentic system manage a city's power grid, or coordinate a country's disaster relief?
    - **Sustainability Goal Alignment:** Does the "Vibe" of the project align with a major global challenge (UN SDGs)?
    - **Actionability:** Does the agent actually *do* something (e.g., call a tool, update a database, send an alert) rather than just summarizing text?
    
    #### **3. Technical Rigor & "Googliness" - 20%**
    
    - **ADK Mastery:** Effective use of agent.json (Agent Cards) for discovery and **MCP** for grounding in real-world data.
    - **Deployment:** Is the agent live and reachable via a public Google Cloud URL?
    - **Reliability:** How does the agent handle "Tool Space Interference" or errors in the loop?
    
    #### **4. The Pitch & The "Trace" - 20%**
    
    - **The Visualization:** Did the team use the **ADK Dev UI** to show the judges the literal "thoughts" and "parallel actions" of the agents?
    - **The Handshake:** Did they successfully demonstrate an A2A connection between disparate agents?
    
    ---
    
    ### **Improvements to "Go Big"**
    
    1. **Introduce "Agent Roles":** Tell hackers they aren't building "an app." They are building a **Specialist**. One team builds the "Satellite Analyst," another builds the "Logistics Coordinator." The real winners will be those whose agents talk to each other via A2A.
    2. **The "Live Feed" Constraint:** Force the "Moonshot" to be grounded. "Your agent must use a real-world API (Weather, News, Finance) as its trigger." This prevents "toy" projects.
    3. **The "Self-Correction" Bonus:** Offer bonus points for any LoopAgent that identifies its own hallucination or error and re-runs the task. This proves they understand **autonomy** over simple **automation**.
    
    ### **Prizes:**
    
    1st: $1000 Google Cloud Developer Credits
    
    2nd: $500 Google Cloud Developer Credits
    
    3rd: $250 Google Cloud Developer Credits
	
	
	- **Oracle Challenge: Technology in Service of Humanity**
    
    ## Problem Statement
    
    We live in an age of remarkable technological capability — and yet loneliness is rising, mental health is in crisis, accessibility gaps persist, and countless people fall through the cracks of systems that were never designed with them in mind.
    
    **Your challenge: use AI and machine learning to close the gap between human need and human connection.**
    
    The problems worth solving are all around us. A caregiver who is too exhausted to ask for help. A student who struggles silently because no one noticed. A person with a disability navigating a world not built for them. An elderly neighbor who hasn’t spoken to anyone in days. These are not edge cases — they are the everyday reality for millions of people.
    
    We're asking you to build something that genuinely helps. Not a demo for its own sake, but an AI-powered solution rooted in empathy — one that listens better, reaches further, or acts more thoughtfully than what exists today.
    
    **What does success look like?** A working prototype that addresses a real, human-centered problem. Your solution should be technically sound, but its heart should be the person it serves. Judges will evaluate your work on impact potential, technical execution, and the clarity of your vision.
    
    ### **Judging Criteria:**
    
    ![image.png](attachment:4fb03676-89af-48a2-94fa-04bf8e9bfb48:1f565bd6-5313-48b9-a614-1d9397d2f891.png)
    
    ### **Prize:**
    
    **1st Place: LEGO Super Mario Gameboy**
	
	- **NextEra Energy Challenge: Malware Analysis Challenge**
    
    AI-Driven Threat Detection & Response
    
    For this challenge, teams will be provided a non-executable malware sample and tasked with building a sandboxed virtual environment to contain it. From there, teams will design and implement an AI-driven automated pipeline that analyzes the malware, extracts key behavioral and structural identifiers, and generates a recommended mitigation or remediation plan based on its findings.
    
    The goal isn't just to detect, it's to understand and respond. Teams should aim to answer critical questions such as:
    
    - What type of malware is this, and how does it behave?
    - What systems or data could be at risk?
    - What are the recommended next steps to contain or eliminate the threat?
    
    #### Malware Sample
    
    [MalwareChallenge.zip](attachment:f617dee2-6a73-4564-8be5-d9b90c097be4:MalwareChallenge.zip)
    
    The password is "infected".
    
    **Prize:**
    
    **1st Place: Guranteed Interviews (Internships/Full-Time)**
	
	- **Climate Teach-In Sustainability Challenge: Living by the water; A Civic Challenge for Environmental Resilience.**
    
    ### **The Challenge**
    
    Design a solution that helps Tampa Bay become more resilient to water-related threats.
    
    Your project can focus on any aspect of resilience that matters to your team, including environmental, social, infrastructural, economic, civic, public health, tourism, or emergency response challenges. You may create an app, platform, tool, system, service, data product, public-facing experience, or another solution format that fits your idea.
    
    The strongest submissions will not just react to disaster. They will rethink how communities, governments, and organizations can prepare for, respond to, and thrive in a water-threatened region. Your solution should be ambitious, realistic, and rooted in the needs of the people and places most affected.
    
    ### **Goal**
    
    Build a project that answers this question:
    
    **How might we help Tampa Bay live by the water in a way that is safer, smarter, more equitable, and more resilient?**
    
    Teams are encouraged to choose a specific problem within this broader challenge. For example, you might focus on:
    
    - flood preparedness or storm response
    - infrastructure or mobility during extreme weather
    - protecting vulnerable communities
    - environmental restoration
    - resilience planning and public awareness
    - tourism and hospitality adaptation
    - civic coordination or access to resources
    
    You do not need to solve every problem. You do need to clearly define the one you are solving, explain why it matters, and show how your solution could make a meaningful difference in Tampa Bay. The challenge intentionally does not prescribe one single issue; teams are meant to identify the vulnerability that best fits their skills and values.
    
    ### Prizes
    
    **1st Place:** Zero Waste swag bags (Sponsored by Patel College of Sustainability) 
    
    The winning team gets the chance to present in front of **Tampa Bay Regional Planning Council Representatives**, the Largo Mayor and more company representatives at **Tampa Bay Resilience Design Challenge** on **Wednesday, April 1st** from 1:00 PM - 4:00 PM, as their project may be implemented in the Tampa Bay area.
    
    [CTI Challenge Judging Rubric](https://www.notion.so/CTI-Challenge-Judging-Rubric-330dd6c309db800c9c5ede19ecc14724?pvs=21)
Challenge_Requirements.txt
9 KB